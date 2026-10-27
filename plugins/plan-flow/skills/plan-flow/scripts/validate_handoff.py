"""Read-only structural checks for handoff files; not a design, evidence or security review."""

import argparse
import json
import re
from pathlib import Path

from handoff_common import (
    ABSOLUTE_PATH, AC_ID, BASE_VALUE, CONTROL_LINE, DATE_VALUE, EXEC_MARKER, ISSUE_URL, PR_ROW,
    SECTIONS, TOKEN_BUDGET, artifact_pattern, est_tokens, field, header, phase_pattern, sections,
)

PLACEHOLDER = re.compile(r"\{\{\s*[A-Za-z_]\w*\s*\}\}|<…>|<\.\.\.>|\bTBD\b|\?\?\?")


def load_directory(directory, issue):
    """Read every artifact of the issue; unreadable files become errors."""
    pattern = artifact_pattern(issue)
    files, errors = {}, []
    for path in sorted(directory.iterdir()):
        if pattern.fullmatch(path.name):
            try:
                files[path.name] = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                errors.append(f"{path.name}: cannot read artifact: {exc}")
    return files, errors


def expected_layout(files, issue, objectives):
    """Infer the chosen layout from filenames; the planner owns sizing, the checker owns completeness."""
    objective_file = re.compile(re.escape(issue) + r"-exec-obj-([1-9][0-9]*)\.md")
    phase = phase_pattern(issue)
    phased = (objectives or 0) > 1 or any(phase.fullmatch(name) for name in files)
    if not phased:
        return {f"{issue}-exec.md": "compact"}, 1
    found = sorted(int(m.group(1)) for m in map(objective_file.fullmatch, files) if m)
    count = objectives or (found[-1] if found else 1)
    expected = {f"{issue}-exec-obj-{n}.md": "objective" for n in range(1, count + 1)}
    expected[f"{issue}-exec-gates.md"] = "gates"
    expected[f"{issue}-exec-ship.md"] = "ship"
    return expected, count


def check_document(name, text, kind, issue, errors, warnings):
    body, head = sections(text), header(text)
    if PLACEHOLDER.search(text):
        errors.append(f"{name}: unresolved template placeholder")
    if EXEC_MARKER not in text:
        errors.append(f"{name}: missing the execution-prompt statement")
    match = ISSUE_URL.fullmatch(field(text, "Issue"))
    if not match or match.group(1) != issue:
        errors.append(f"{name}: missing or mismatched full issue URL")
    if field(text, "Status") != "ready":
        errors.append(f"{name}: handoff is not marked ready")
    if not BASE_VALUE.fullmatch(field(text, "Base")):
        errors.append(f"{name}: Base must be <branch>@<sha>")
    if not DATE_VALUE.fullmatch(field(text, "Planned")):
        errors.append(f"{name}: Planned must be YYYY-MM-DD")
    if field(text, "Compatibility") not in ("existing", "greenfield"):
        errors.append(f"{name}: compatibility mode is missing")
    if field(text, "Security-sensitive") not in ("yes", "no"):
        errors.append(f"{name}: security classification is missing")
    if field(text, "Plan review") not in ("complete", "not-required"):
        errors.append(f"{name}: plan review status is missing or incomplete")
    if re.search(r"waits on:", text[len(head):], re.IGNORECASE):
        errors.append(f"{name}: an external wait must open the file, before the first heading")
    if re.search(r"waits on:", head, re.IGNORECASE) and not all(
        (re.search(r"\bSTOP\b", head), re.search(r"check:", head, re.IGNORECASE), re.search(r"resume:", head, re.IGNORECASE))
    ):
        errors.append(f"{name}: external wait requires a leading STOP with check: and resume:")
    for heading in SECTIONS[kind]:
        if not body.get(heading):
            errors.append(f"{name}: missing or empty {heading} section")
    if body.get("Workspace") and not ABSOLUTE_PATH.search(body["Workspace"]):
        errors.append(f"{name}: Workspace needs absolute paths")
    validate_section = body.get("Validate", "")
    if "|" in validate_section and "pipefail" not in validate_section:
        errors.append(f"{name}: Validate pipes must keep failures visible (set -o pipefail)")
    if est_tokens(text) > TOKEN_BUDGET[kind]:
        warnings.append(f"{name}: about {est_tokens(text)} tokens, over the {TOKEN_BUDGET[kind]} budget; trim prose, keep every fact and control")


def check_pull_requests(documents, objective_count, errors):
    holder = next((body for _, body, kind in documents.values() if kind in ("compact", "ship")), None)
    if holder is None:
        return
    rows = PR_ROW.findall(holder.get("Ship", ""))
    if not rows:
        errors.append("Ship section has no PR rows (- PR<n>: branch=..; base=..; objectives=..; keyword=..)")
        return
    covered = [int(n) for _, _, _, objectives, _ in rows for n in objectives.split(",")]
    for number in range(1, objective_count + 1):
        if covered.count(number) != 1:
            errors.append(f"objective {number} must appear in exactly one PR row (found {covered.count(number)})")
    if sum(1 for row in rows if row[4] == "Closes") != 1:
        errors.append("exactly one PR row must use keyword=Closes")


def validate(files, issue, objectives=None, *, sensitive=False, read_errors=()):
    errors, warnings, documents = list(read_errors), [], {}
    expected, objective_count = expected_layout(files, issue, objectives)
    for name in sorted(files):
        if name not in expected:
            errors.append(f"{name}: conflicting or unrequested artifact; resolve without automatic deletion")
    for name, kind in expected.items():
        if name not in files:
            errors.append(f"{name}: missing required artifact")
            continue
        documents[name] = (files[name], sections(files[name]), kind)
        check_document(name, files[name], kind, issue, errors, warnings)

    detected_sensitive = sensitive or any(field(text, "Security-sensitive") == "yes" for text, _, _ in documents.values())
    for name, (text, body, kind) in documents.items():
        if field(text, "Security-sensitive") == "yes" or (detected_sensitive and kind != "objective"):
            if field(text, "Security-sensitive") != "yes" or field(text, "Plan review") != "complete":
                errors.append(f"{name}: sensitive work needs an explicit completed plan review")
            if not CONTROL_LINE.search(body.get("Security", "")):
                errors.append(f"{name}: missing issue-specific security requirement IDs")
            if not re.search(r"^Review:[ \t]*\S", body.get("Security", ""), re.MULTILINE):
                errors.append(f"{name}: Security needs a Review: line naming reviewer, scope and resolved findings")
    for label in ("Compatibility", "Base", "Issue"):
        if len({field(text, label) for text, _, _ in documents.values()}) > 1:
            errors.append(f"{label} differs across artifacts")

    acceptance, controls, all_controls = {}, {}, {}
    for name, (_, body, _) in documents.items():
        acceptance[name] = set(AC_ID.findall(body.get("Acceptance", body.get("Acceptance map", ""))))
        if not acceptance[name]:
            errors.append(f"{name}: missing acceptance IDs")
        controls[name] = {}
        for identifier, requirement in CONTROL_LINE.findall(body.get("Security", "")):
            requirement = requirement.strip()
            if identifier in all_controls and all_controls[identifier] != requirement:
                errors.append(f"{name}: {identifier} differs across artifacts")
            controls[name][identifier] = requirement
            all_controls[identifier] = requirement
    covered = set().union(*(acceptance[name] for name, (_, _, kind) in documents.items() if kind in ("compact", "objective")))
    for name, (_, _, kind) in documents.items():
        if kind in ("gates", "ship"):
            if acceptance[name] != covered:
                errors.append(f"{name}: acceptance IDs differ from objective coverage")
            if set(controls[name]) != set(all_controls):
                errors.append(f"{name}: missing issue-wide security requirements")
    check_pull_requests(documents, objective_count, errors)
    return errors, warnings, documents


def report(errors, warnings, documents):
    sizes = {name: est_tokens(text) for name, (text, _, _) in documents.items()}
    return {
        "ok": not errors,
        "files": sizes,
        "total_est_tokens": sum(sizes.values()),
        "token_estimate": "characters / 4; a proxy, not a measured count",
        "errors": errors,
        "warnings": warnings,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--issue", required=True)
    parser.add_argument("--objectives", type=int, help="optional; inferred from the files when omitted")
    parser.add_argument("--security-sensitive", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[1-9][0-9]*", args.issue) or (args.objectives is not None and args.objectives < 1):
        parser.error("issue must be a positive issue number and objectives must be positive")
    files, read_errors = load_directory(args.directory, args.issue)
    errors, warnings, documents = validate(files, args.issue, args.objectives,
                                           sensitive=args.security_sensitive, read_errors=read_errors)
    print(json.dumps(report(errors, warnings, documents), indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
