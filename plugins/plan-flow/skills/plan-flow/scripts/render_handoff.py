"""Render execution handoff files from one JSON spec, validate them in memory, then write them.

The planner supplies each fact once; this script routes facts to the files that need them and adds
the fixed executor rules, so shared text is exact and costs the planner no output tokens.
Usage: render_handoff.py --out <planning dir> [--spec <file>|-] [--replace-existing]   (spec defaults to stdin)
"""

import argparse
import datetime
import json
import re
import shlex
import sys
from pathlib import Path

from handoff_common import (
    BASE_VALUE, DATE_VALUE, EXEC_SENTENCE, ISSUE_URL, PR_ROW_FORMAT, artifact_pattern,
)
from validate_handoff import load_directory, report, validate

RULES = """\
- Start: read the repo guidance (AGENTS.md, CLAUDE.md), the issue and its new comments, the progress file if present, and `git status`. Run the Freshness command and re-read every path it lists; always re-read security-control facts. Follow the code over this file on non-invalidating details and record the deviation.
- Scope: edit, stage and commit only in the Workspace, within this phase. Stage explicit paths; never stage plan or progress files. Never bypass hooks, push to the base branch, or merge (no `--auto`/`--admin`). Write no persistent memory. Never repeat an unchanged tool call.
- Output: run checks as `set -o pipefail; <cmd> 2>&1 | tail -n 60`; if the cause is not visible, rerun only the failing test verbosely. Report outcomes, not logs.
- Public text (code, commits, PRs, issues, comments): no assistant or tool attribution (including default `Co-Authored-By` or "generated with" trailers), hidden reasoning, secrets, key material or exploit detail; use the repo's own domain terms and glossary; `#N` refs only in commit or PR bodies, stating issue or PR; a cross-repo reference names only what the work needs.
- Decisions: when a choice the issue (body and comments) does not state is settled this session (user answer, deviation from this file), post it at once as one issue comment, `Execution decision: <choice>; why; rejected alternative`, under the Public text rules; routine mechanical choices do not. Log the comment ID under Decisions in the progress file; never repost. If `gh` fails, log the text there and tell the user.
- Tests: pass only if the output shows the expected tests ran and passed; `no tests to run`, a zero count or an unmatched filter is a failure. Never delete, skip or weaken a test or assertion to get green; change one only if the required behavior changes, and record why.
- Stop, record: objective invalidated, security control weakened, missing access or dependency, or scope growth. Out-of-scope findings: record, never fix or file. Vulnerabilities: tell the user privately now. Unresolved choices or any stop: ask (Questions) with the ways forward; never wait silently; continue only on an answer that clears it.
- Completion comment: once this phase's work is fully done (never partial, never before its checks pass), post one issue comment `Execution complete: <phase>` saying what was done, under the Public text rules. Log its ID under `comments` in the progress file; never repost. A stop or failure posts nothing. If `gh` fails, log the text there and tell the user.
- Questions: ask only via the host's interactive question tool (numbered text if none), never in reply text. Plain short English; 2-4 options, recommended first as `(Recommended)` with a short reason. A runner contract that forbids asking overrides."""

PHASE_RULE = {
    "compact": "Phase: implement and commit, then validate (Gates), then publish (Ship) only when authorized and gates are fresh. If interrupted or resuming, create the progress file first so decisions and posted IDs are not lost. Post a completion comment per stage (objective, gates, ship), each only when that stage is done.",
    "objective": "Phase: implement and commit this objective only. No push, PR or full gate suite.",
    "gates": "Phase: validate only; fix in-scope failures. No push or PR.",
    "ship": "Phase: publish only with authority and current-commit gate evidence; implement nothing new.",
}

PROGRESS_FORMAT = (
    "Progress file `{planning}/{issue}-plan-progress.json`, created on first use: "
    '{{"next":"","done":{{"<objective>":"<sha>"}},"decisions":["<comment id>"],"findings":[],"gates":{{"tip":"","result":""}},"prs":[],"comments":{{"<phase>":"<comment id>"}},'
    '"criteria":{{"<AC id>":{{"status":"pending","evidence":""}}}}}}. '
    "Edit values only, never remove or rename keys; `passing` only with evidence (test or command, result, tip SHA)."
)

OBJECTIVE_COMPLETION = "Completion comment (Rules) after the commit and passing validation: objective title, commit SHA, what changed and why, tests run and passed, deviations."

GATES_COMPLETION = "Completion comment (Rules) after every criteria entry is set: branch-tip SHAs, commands and results, review outcome, criteria passing, failing or unvalidated."

GATES_FIXED = "Run at each branch tip, in the checkout that contains the change; confirm mounts and build contexts exercise that checkout. Fix in-scope failures and rerun affected checks; if code changes, rerun review and checks on the new commit. Report any requirement not validated."

FRESH_EVIDENCE = "Gate evidence is fresh only if each PR branch tip equals its recorded SHA, `git status --porcelain` is empty and tool versions are unchanged. Otherwise rerun the affected commands below or stop with the exact blocker. Never accept a recollection of a green run. Every criteria entry in the progress file must be `passing` with evidence, else report it unvalidated."

SHIP_STEPS = """\
1. Ask (Questions) about each recorded side finding before any PR: include with authority, or a separately authorized issue. No automatic scope growth.
2. Check authority for each external action; a planning request alone authorizes no issue edit, push, PR or follow-up issue; decision and completion comments (Rules) are standing. Not granted: ask `Push and open PRs (Recommended)` / `Hold`.
3. Issue record: when authorized, reconcile accepted decisions, non-goals and acceptance into the issue body (the body is the execution contract); otherwise report the body as unreconciled. Never repost a decision already commented.
4. Inspect the final diff; if too big to review, ask about splitting. Push task branches and open the PR rows below in order against their bases. `Closes #N` only on the row with keyword=Closes; `Refs #N` rows list the open criteria. Never merge.
5. Report gaps first (criteria not passing, unvalidated items, follow-ups), then PR URLs, CI links, exact validation and review outcomes, deviations, remaining waits (URL, holder). State publication as local-only, pushed, PR open or merged.
6. Completion comment (Rules), once every PR row is open: PR URLs, CI status, publication state, gaps. Hold or a stop posts none."""

STACK_STEPS = (
    "Stack: rows are one chain, bottom first; its branches exist locally, so publish together here. "
    "With the official `github/gh-stack` extension: `gh stack init -b {trunk} <row branches in order>`, then `gh stack submit --auto` (linked draft PRs; the user marks them ready before `gh stack merge`). "
    "Otherwise push in row order and `gh pr create --draft --base <row base>`, each body listing the stack. "
    "The user merges bottom-up. Manual stack: retarget each later PR to {trunk} before its merge "
    "(squash-merge repo: `git rebase --onto origin/{trunk} <merged branch> <next branch>`; ask before the force push)."
)

FOLLOW_UP_FIXED = "After implementation, inspect the changed contract and each candidate's consumed version, and search for more consumers. For truly affected repos create only separately authorized issues (generic behavior, acceptance, rollout order); edit no other repo. If issue creation is unavailable, save a labelled draft and report it."

MAX_CRITERIA_PER_OBJECTIVE = 4

STOP_RULE = "Any stop in Rules: record it, then ask the way forward (Questions)."


class SpecError(ValueError):
    """The spec cannot be rendered."""


def wrap(command):
    return f"set -o pipefail; {command} 2>&1 | tail -n 60"


def applies(item, number):
    scope = item.get("objectives")
    return number is None or scope is None or number in scope


def single_line(value):
    return isinstance(value, str) and bool(value.strip()) and "\n" not in value


def check_spec(spec):
    errors = []

    def need(where, mapping, key, test, expectation):
        if not isinstance(mapping, dict) or not test(mapping.get(key)):
            errors.append(f"{where}{key}: {expectation}")
            return None
        return mapping[key]

    def text(value):
        return isinstance(value, str) and bool(value.strip())

    def lines(value):
        return isinstance(value, list) and bool(value) and all(single_line(v) for v in value)

    def numbers(value):
        return isinstance(value, list) and bool(value) and all(isinstance(v, int) and v >= 1 for v in value)

    if not isinstance(spec, dict):
        return ["spec must be a JSON object"]
    need("", spec, "issue", lambda v: isinstance(v, str) and ISSUE_URL.fullmatch(v), "full https://github.com/<org>/<repo>/issues/<n> URL")
    need("", spec, "base", lambda v: isinstance(v, str) and BASE_VALUE.fullmatch(v), "<branch>@<sha> (7-40 hex)")
    need("", spec, "compatibility", lambda v: v in ("existing", "greenfield"), "existing or greenfield")
    need("", spec, "layout", lambda v: v in ("compact", "phased"), "compact or phased")
    need("", spec, "execution_root", lambda v: isinstance(v, str) and v.startswith("/"), "absolute path")
    for key in ("title", "layout_reason", "setup", "root_cause", "target_behavior", "follow_up", "rollback"):
        need("", spec, key, single_line, "non-empty single line")
    if "planned" in spec and not (isinstance(spec["planned"], str) and DATE_VALUE.fullmatch(spec["planned"])):
        errors.append("planned: YYYY-MM-DD")

    objectives = need("", spec, "objectives", lambda v: isinstance(v, list) and v, "non-empty list")
    count = len(objectives) if isinstance(objectives, list) else 0
    if spec.get("layout") == "compact" and count != 1:
        errors.append("objectives: compact layout takes exactly one objective")
    for index, objective in enumerate(objectives if isinstance(objectives, list) else [], start=1):
        where = f"objectives[{index}]."
        need(where, objective, "title", single_line, "non-empty single line")
        need(where, objective, "action", single_line, "non-empty single line")
        need(where, objective, "validate", single_line, "single-line command")
        need(where, objective, "files", lines, "list of paths")
        need(where, objective, "tests", lines, "list of named tests")
        if isinstance(objective, dict):
            if "prerequisites" in objective and not numbers(objective["prerequisites"]):
                errors.append(f"{where}prerequisites: list of earlier objective numbers")
            wait = objective.get("wait")
            if wait is not None and not (isinstance(wait, dict) and all(single_line(wait.get(k)) for k in ("on", "check", "resume"))):
                errors.append(f"{where}wait: needs single-line on, check and resume")

    ids = set()
    acceptance = need("", spec, "acceptance", lambda v: isinstance(v, list) and v, "non-empty list")
    for item in acceptance if isinstance(acceptance, list) else []:
        identifier = item.get("id") if isinstance(item, dict) else None
        if not (isinstance(identifier, str) and re.fullmatch(r"AC[1-9][0-9]*", identifier)) or identifier in ids:
            errors.append(f"acceptance: unique AC<n> id required (got {identifier!r})")
            continue
        ids.add(identifier)
        need(f"acceptance {identifier}.", item, "text", single_line, "single line")
        need(f"acceptance {identifier}.", item, "objectives", lambda v: numbers(v) and all(n <= count for n in v), "objective numbers within range")

    security = need("", spec, "security", lambda v: isinstance(v, dict) and isinstance(v.get("sensitive"), bool), "object with boolean sensitive")
    if isinstance(security, dict):
        controls = security.get("controls", [])
        if security["sensitive"]:
            need("security.", security, "review", single_line, "reviewer, scope and resolved findings (required when sensitive)")
            if not controls:
                errors.append("security.controls: sensitive work needs S<n> controls")
        for control in controls if isinstance(controls, list) else []:
            identifier = control.get("id") if isinstance(control, dict) else None
            if not (isinstance(identifier, str) and re.fullmatch(r"S[1-9][0-9]*", identifier)) or identifier in ids:
                errors.append(f"security.controls: unique S<n> id required (got {identifier!r})")
                continue
            ids.add(identifier)
            need(f"control {identifier}.", control, "text", single_line, "single line")
            if "objectives" in control and not (numbers(control["objectives"]) and all(n <= count for n in control["objectives"])):
                errors.append(f"control {identifier}.objectives: objective numbers within range")

    for key, fields in (("evidence", ("at", "claim")), ("decisions", ("text", "why", "rejected"))):
        items = need("", spec, key, lambda v: isinstance(v, list) and v, "non-empty list")
        for item in items if isinstance(items, list) else []:
            for name in fields:
                need(f"{key}.", item, name, single_line, "single line")
    for key in ("rules", "assumptions"):
        if key in spec and not lines(spec[key]):
            errors.append(f"{key}: list of single lines")
    if "dirty" in spec and not single_line(spec["dirty"]):
        errors.append("dirty: single line")
    if isinstance(spec.get("security"), dict) and "binding" in spec["security"] and not single_line(spec["security"]["binding"]):
        errors.append("security.binding: single line")
    for number in range(1, count + 1):
        if isinstance(acceptance, list) and not any(isinstance(a, dict) and number in (a.get("objectives") or []) for a in acceptance):
            errors.append(f"acceptance: objective {number} has no acceptance criterion")
    gates = need("", spec, "gates", lambda v: isinstance(v, dict) and lines(v.get("commands")), "object with commands list")
    for conditional in (gates or {}).get("conditional", []) if isinstance(gates, dict) else []:
        need("gates.conditional.", conditional, "when", single_line, "single line")
        need("gates.conditional.", conditional, "command", single_line, "single line")

    rows = need("", spec, "pr_rows", lambda v: isinstance(v, list) and v, "non-empty list")
    covered = []
    for row in rows if isinstance(rows, list) else []:
        need("pr_rows.", row, "branch", lambda v: isinstance(v, str) and re.fullmatch(r"[^\s;]+", v), "no spaces or semicolons")
        need("pr_rows.", row, "base", lambda v: isinstance(v, str) and re.fullmatch(r"[^\s;]+", v), "no spaces or semicolons")
        need("pr_rows.", row, "keyword", lambda v: v in ("Closes", "Refs"), "Closes or Refs")
        if need("pr_rows.", row, "objectives", numbers, "objective numbers"):
            covered += row["objectives"]
    for number in range(1, count + 1):
        if covered.count(number) != 1:
            errors.append(f"pr_rows: objective {number} must be in exactly one row (found {covered.count(number)})")
    return errors or stack_errors(spec)


def spec_warnings(spec):
    """Soft size signals; the plan is still valid."""
    warnings = []
    criteria, objectives = len(spec["acceptance"]), len(spec["objectives"])
    if criteria > MAX_CRITERIA_PER_OBJECTIVE * objectives:
        warnings.append(f"acceptance: {criteria} criteria for {objectives} objective(s); merge overlapping ones or re-check sizing, never drop a security control")
    return warnings


def stack_errors(spec):
    """How PR rows chain: each base is the trunk or an earlier row, each row has one child, and work builds upward."""
    trunk, rows = trunk_of(spec), spec["pr_rows"]
    errors, seen, children = [], {}, {}
    for n, row in enumerate(rows, start=1):
        if row["branch"] in seen:
            errors.append(f"pr_rows: PR{n} repeats branch {row['branch']}")
        seen[row["branch"]] = n
        if row["base"] == trunk:
            continue
        if row["base"] not in seen or seen[row["base"]] == n:
            errors.append(f"pr_rows: PR{n} base must be {trunk} or the branch of an earlier row (got {row['base']})")
        elif row["base"] in children:
            errors.append(f"pr_rows: PR{n} and PR{children[row['base']]} both stack on {row['base']}; a stack is one chain")
        else:
            children[row["base"]] = n
    if errors:
        return errors
    allowed = {}
    for n, row in enumerate(rows, start=1):
        lower = rows_below(spec, row)
        lower_objectives = {o for r in lower for o in r["objectives"]}
        if lower_objectives and min(row["objectives"]) <= max(lower_objectives):
            errors.append(f"pr_rows: PR{n} objectives must all come after the objectives of the PR(s) it stacks on")
        if row["keyword"] == "Closes" and row["branch"] in children:
            errors.append(f"pr_rows: PR{n} stacks under PR{children[row['branch']]}; Closes belongs on the top of the stack")
        for number in row["objectives"]:
            allowed[number] = set(row["objectives"]) | lower_objectives
    for number, objective in enumerate(spec["objectives"], start=1):
        for prerequisite in objective.get("prerequisites", []):
            if prerequisite not in allowed.get(number, ()):
                errors.append(f"objectives[{number}].prerequisites: objective {prerequisite} is not in this PR or a PR it stacks on")
    return errors


def freshness(spec, evidence):
    branch, sha = BASE_VALUE.fullmatch(spec["base"]).groups()
    paths = []
    for item in evidence:
        path = re.sub(r":\d+(?:-\d+)?$", "", item["at"])
        if path not in paths:
            paths.append(path)
    target = "origin/" + branch
    scope = " -- " + " ".join(shlex.quote(p) for p in paths) if paths else ""
    return f"Freshness: `git fetch origin && git diff --stat {sha} {target}{scope}`; re-read every listed path."


def workspace(spec, out_dir, evidence, extra=()):
    lines = [f"Execution root: {spec['execution_root']}", f"Planning files: {out_dir}", f"Setup: {spec['setup']}", freshness(spec, evidence), *extra]
    return "\n".join(lines)


def acceptance_lines(spec, number=None):
    return "\n".join(f"- {a['id']}: {a['text']}" for a in spec["acceptance"] if applies(a, number))


def acceptance_map(spec):
    return "\n".join(
        f"- {a['id']} -> objective {','.join(map(str, a['objectives']))}: {a['text']}" for a in spec["acceptance"])


def evidence_lines(spec, number=None):
    lines = [f"Root cause: {spec['root_cause']}", f"Target: {spec['target_behavior']}"]
    lines += [f"- {e['at']}: {e['claim']}" for e in spec.get("evidence", []) if applies(e, number)]
    lines += [f"Assumption: {a}" for a in spec.get("assumptions", [])]
    lines.append(f"Dirty paths: {spec.get('dirty', 'none')}")
    return "\n".join(lines)


def decision_lines(spec, number=None, *, layout=False):
    lines = [f"- {d['text']} (why: {d['why']}; rejected: {d['rejected']})" for d in spec["decisions"] if applies(d, number)]
    lines += [f"- Rule: {r}" for r in spec.get("rules", [])]
    if layout:
        lines.append(f"- Layout: {spec['layout']}, because {spec['layout_reason']}")
    return "\n".join(lines)


def file_controls(spec, number=None):
    return [c for c in spec["security"].get("controls", []) if applies(c, number)]


def security_lines(spec, number=None):
    security = spec["security"]
    controls = file_controls(spec, number)
    binding = security.get("binding") or "the repo's security guidance (AGENTS.md, CLAUDE.md)"
    if not controls:
        return f"No issue-specific controls apply here. Binding: {binding}."
    lines = [f"- {c['id']}: {c['text']}" for c in controls] + [f"Binding: {binding}"]
    if security["sensitive"]:
        lines.append(f"Review: {security['review']}")
    return "\n".join(lines)


def is_sensitive(spec, number=None):
    return bool(spec["security"]["sensitive"]) if number is None else bool(file_controls(spec, number)) and bool(spec["security"]["sensitive"])


def gates_lines(spec):
    gates = spec["gates"]
    lines = ["Commands:"] + [f"- `{wrap(c)}`" for c in gates["commands"]]
    lines += [f"- If {c['when']}: `{wrap(c['command'])}`" for c in gates.get("conditional", [])]
    lines.append(GATES_FIXED)
    if spec["security"]["sensitive"]:
        lines.append("Sensitive: review the full scoped diff of every branch tip against the S controls; fix, rerun, and report the disposition.")
    return "\n".join(lines)


def trunk_of(spec):
    return BASE_VALUE.fullmatch(spec["base"]).group(1)


def rows_below(spec, row):
    """PR rows `row` is stacked on, nearest first; empty when it targets the trunk."""
    by_branch = {r["branch"]: r for r in spec["pr_rows"]}
    below = []
    while row["base"] in by_branch:
        row = by_branch[row["base"]]
        below.append(row)
    return below


def scope_check_lines(spec):
    """One git command per PR row that prints changed paths no objective planned; empty output means in scope."""
    trunk, lines = trunk_of(spec), []
    for n, row in enumerate(spec["pr_rows"], start=1):
        base = f"origin/{row['base']}" if row["base"] == trunk else row["base"]
        planned = dict.fromkeys(path for number in row["objectives"] for path in spec["objectives"][number - 1]["files"])
        excludes = " ".join(shlex.quote(f":!{path}") for path in planned)
        lines.append(f"- PR{n} scope: `git diff --name-only {base}...{row['branch']} -- . {excludes}`")
    return ("Scope check: each command prints changed paths outside the plan; justify every printed path under findings in the progress file, or revert it.\n"
            + "\n".join(lines))


def pr_rows(spec):
    return "\n".join(
        PR_ROW_FORMAT.format(n=i, branch=r["branch"], base=r["base"], objectives=",".join(map(str, r["objectives"])), keyword=r["keyword"])
        for i, r in enumerate(spec["pr_rows"], start=1))


def ship_lines(spec):
    stack = "\n" + STACK_STEPS.format(trunk=trunk_of(spec)) if any(r["base"] != trunk_of(spec) for r in spec["pr_rows"]) else ""
    return f"{SHIP_STEPS}\n\nPR rows:\n{pr_rows(spec)}{stack}\nRollback: {spec['rollback']}"


def cleanup_lines(spec, paths, out_dir):
    listing = "\n".join(f"- {p}" for p in paths)
    progress = f"{out_dir}/{ISSUE_URL.fullmatch(spec['issue']).group(1)}-plan-progress.json"
    return (f"Generated files, absolute:\n{listing}\n- {progress} (only if created)\n"
            "Keep them until every PR is independently verified MERGED, then list these files and get the user's deletion confirmation. "
            "Never glob or delete another checkout's planning files; never remove a worktree without authority.")


def follow_up_lines(spec):
    return f"{spec['follow_up']}\n{FOLLOW_UP_FIXED}"


def assemble(spec, title, kind, sensitive, sections, wait=None):
    planned = spec.get("planned") or datetime.date.today().isoformat()
    review = "complete" if spec["security"]["sensitive"] else "not-required"
    head = [
        f"# {title}", "",
        f"Issue: {spec['issue']}", "Status: ready", f"Base: {spec['base']}", f"Planned: {planned}",
        f"Compatibility: {spec['compatibility']}", f"Security-sensitive: {'yes' if sensitive else 'no'}", f"Plan review: {review}",
    ]
    if wait:
        head += ["", f"STOP: waits on: {wait['on']}; check: {wait['check']}; resume: {wait['resume']}"]
    head += ["", EXEC_SENTENCE, "", "## Rules", "", f"- {PHASE_RULE[kind]}", RULES]
    body = "".join(f"\n\n## {name}\n\n{content}" for name, content in sections)
    return "\n".join(head) + body + "\n"


def objective_section(number, objective):
    return "\n".join([
        f"Objective {number}: {objective['title']}",
        f"Files: {', '.join(objective['files'])}",
        f"Tests: {', '.join(objective['tests'])}",
        f"First action: {objective['action']}",
    ])


def render(spec, issue, out_dir):
    """Return {filename: text} for every file the layout needs."""
    evidence = spec.get("evidence", [])
    files = {}
    names = [f"{issue}-exec.md"] if spec["layout"] == "compact" else (
        [f"{issue}-exec-obj-{n}.md" for n in range(1, len(spec["objectives"]) + 1)] + [f"{issue}-exec-gates.md", f"{issue}-exec-ship.md"])
    paths = [f"{out_dir}/{name}" for name in names]

    if spec["layout"] == "compact":
        objective = spec["objectives"][0]
        row = spec["pr_rows"][0]
        files[names[0]] = assemble(spec, spec["title"], "compact", is_sensitive(spec), [
            ("Workspace", workspace(spec, out_dir, evidence, [f"Branch: {row['branch']} from origin/{row['base']}"])),
            ("Acceptance", acceptance_lines(spec)),
            ("Evidence", evidence_lines(spec)),
            ("Decisions", decision_lines(spec, layout=True)),
            ("Objective", objective_section(1, objective) + f"\nFocused check: `{wrap(objective['validate'])}`\n{OBJECTIVE_COMPLETION}"),
            ("Security", security_lines(spec)),
            ("Gates", f"{gates_lines(spec)}\n{scope_check_lines(spec)}\n{GATES_COMPLETION}\nRecord results if interrupted: {PROGRESS_FORMAT.format(planning=out_dir, issue=issue)}"),
            ("Ship", ship_lines(spec)),
            ("Follow-up", follow_up_lines(spec)),
            ("Cleanup", cleanup_lines(spec, paths, out_dir)),
            ("Stops", STOP_RULE),
        ], wait=objective.get("wait"))
        return files

    for number, objective in enumerate(spec["objectives"], start=1):
        row = next(r for r in spec["pr_rows"] if number in r["objectives"])
        first = min(row["objectives"]) == number
        lower = rows_below(spec, row)
        if not first:
            branch = f"Branch: {row['branch']} (PR base {row['base']}); reuse the existing branch."
        elif lower:
            branch = (f"Branch: {row['branch']} (PR base {row['base']}); first objective of this PR: create it from the local tip of {row['base']} "
                      f"(`git switch -c {row['branch']} {row['base']}`). That branch is unpushed by design: never wait for its PR, push or merge; "
                      "STOP only if it is missing locally or lacks the prerequisite commits.")
        else:
            branch = f"Branch: {row['branch']} (PR base {row['base']}); first objective of this PR: create it from origin/{row['base']}."
        earlier = objective.get("prerequisites") or [n for n in row["objectives"] if n < number]
        if first:
            earlier = sorted(set(earlier) | {o for r in lower for o in r["objectives"]})
        prerequisites = (f"Prerequisites: objective(s) {','.join(map(str, earlier))} committed and tested per the progress file, else STOP."
                         if earlier else "Prerequisites: none.")
        files[names[number - 1]] = assemble(spec, f"{spec['title']} - objective {number}: {objective['title']}", "objective",
            is_sensitive(spec, number), [
                ("Workspace", workspace(spec, out_dir, [e for e in evidence if applies(e, number)], [branch, prerequisites])),
                ("Acceptance", acceptance_lines(spec, number)),
                ("Evidence", evidence_lines(spec, number)),
                ("Decisions", decision_lines(spec, number)),
                ("Objective", objective_section(number, objective)),
                ("Security", security_lines(spec, number)),
                ("Validate", f"`{wrap(objective['validate'])}`"),
                ("Record", f"Commit this objective with explicit paths, update the progress file. {OBJECTIVE_COMPLETION} Report the result and stop. {PROGRESS_FORMAT.format(planning=out_dir, issue=issue)}"),
                ("Stops", STOP_RULE + " Unmet prerequisites: STOP."),
            ], wait=objective.get("wait"))

    files[names[-2]] = assemble(spec, f"{spec['title']} - gates", "gates", is_sensitive(spec), [
        ("Workspace", workspace(spec, out_dir, evidence)),
        ("Scope", "Review only these branches and their commit ranges:\n" + pr_rows(spec)
         + "\nInspect implemented behavior against the Acceptance map and the full scoped diff."),
        ("Acceptance map", acceptance_map(spec)),
        ("Security", security_lines(spec)),
        ("Gates", f"{gates_lines(spec)}\n{scope_check_lines(spec)}"),
        ("Record", "Record exact branch-tip SHAs, commands, results, environment, review scope and limits in the progress file; set every criteria entry to passing or failing with its evidence, and report any without evidence as unvalidated. " + GATES_COMPLETION + " Then stop. "
                   + PROGRESS_FORMAT.format(planning=out_dir, issue=issue)),
        ("Stops", STOP_RULE + " Any objective not committed and tested: STOP."),
    ])
    files[names[-1]] = assemble(spec, f"{spec['title']} - ship", "ship", is_sensitive(spec), [
        ("Workspace", workspace(spec, out_dir, evidence)),
        ("Acceptance map", acceptance_map(spec)),
        ("Evidence", f"Root cause: {spec['root_cause']}\nTarget: {spec['target_behavior']}"),
        ("Decisions", decision_lines(spec, layout=True)),
        ("Security", security_lines(spec)),
        ("Gates", f"{FRESH_EVIDENCE}\n" + "\n".join(f"- `{wrap(c)}`" for c in spec["gates"]["commands"])
         + ("\nSensitive: every published tip needs full-diff security review evidence." if spec["security"]["sensitive"] else "")),
        ("Ship", ship_lines(spec)),
        ("Follow-up", follow_up_lines(spec)),
        ("Cleanup", cleanup_lines(spec, paths, out_dir)),
        ("Stops", STOP_RULE + " Stale or missing gate evidence: rerun or STOP with the exact blocker."),
    ])
    return files


def run(spec, out, *, replace_existing=False):
    """Validate the spec, render, validate the rendered files in memory, and write only if all pass."""
    problems = check_spec(spec)
    if problems:
        return {"ok": False, "errors": problems, "written": []}
    issue = ISSUE_URL.fullmatch(spec["issue"]).group(1)
    out = Path(out).resolve()
    if not out.is_dir():
        return {"ok": False, "errors": [f"{out}: planning directory does not exist; ask where handoffs belong"], "written": []}
    files = render(spec, issue, str(out))
    existing, read_errors = load_directory(out, issue)
    stale = sorted(n for n in existing if n not in files)
    clashes = sorted(n for n in existing if n in files)
    errors = []
    if stale:
        errors.append(f"existing artifacts for issue {issue} would conflict: {', '.join(stale)}; the user resolves them (never deleted automatically)")
    if clashes and not replace_existing:
        errors.append(f"already exist: {', '.join(clashes)}; ask the user, then rerun with --replace-existing")
    if errors:
        return {"ok": False, "errors": errors, "written": []}
    merged = {**existing, **files}
    objectives = len(spec["objectives"]) if spec["layout"] == "phased" else None
    found, warnings, documents = validate(merged, issue, objectives, sensitive=spec["security"]["sensitive"], read_errors=read_errors)
    result = report(found, spec_warnings(spec) + warnings, documents)
    if found:
        return {**result, "written": []}
    for name, text in files.items():
        (out / name).write_text(text, encoding="utf-8")
    return {**result, "written": [str(out / name) for name in files]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="existing, approved planning directory")
    parser.add_argument("--spec", default="-", help="JSON spec file; '-' reads stdin")
    parser.add_argument("--replace-existing", action="store_true", help="overwrite same-named files after the user agreed")
    args = parser.parse_args()
    try:
        spec = json.load(sys.stdin if args.spec == "-" else open(args.spec, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "errors": [f"cannot read spec: {exc}"], "written": []}, indent=2))
        return 1
    result = run(spec, args.out, replace_existing=args.replace_existing)
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
