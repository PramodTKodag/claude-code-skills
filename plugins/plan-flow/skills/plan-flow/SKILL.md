---
name: plan-flow
description: Investigates one GitHub issue against the real code and writes validated execution handoff files for separate coding sessions, without implementing anything. Use when the teammate runs /plan-flow or wants an issue investigated, grilled, security-audited and cross-repo checked before a different AI session or tool implements it.
argument-hint: "<issue-number-or-url> [--worktree] [--light] [--greenfield] [--exec-print <n|gates|ship|all>]"
disable-model-invocation: true
---

# Plan Flow

Plan one issue; a later session executes it. Planning only: no product edits, branch, worktree, commit, PR, issue edit or memory write. Git/`gh` reads and fetches are fine. The only writes are the handoff files, in the anchor repo's planning directory, never staged, and one approved decision comment on the issue.

## Boundary (read first)

- Invoking this skill authorizes planning only. Generated prompts are content for a future session, never instructions for this run.
- Run only read-only commands, apart from the approved decision comment. Inspect a diagnostic's side effects first; if it can change files, dependencies, services or external state, put it in the handoff instead.
- "Yes", "save it" or "go ahead" at the plan check means post the listed decisions and save the files, nothing more. After saving, report and STOP. The user starts execution in a new session by pasting an execution file.
- A security-control weakening, or access you lack, is a stop: ask, do not work around.

## Preflight

`<skill-dir>` below is the folder containing this SKILL.md, as loaded by the host.

Run `python3 <skill-dir>/scripts/preflight.py` once, in the same turn as the first issue read. It prints repo facts (read-only; no issue text is passed to a shell). Keep its dirty-path list; the final status check compares against it.

## Anchor repo

Execution edits exactly one repo, the anchor.

- Started inside a submodule: the anchor is that submodule unless the issue clearly belongs elsewhere (then ask).
- Started at a parent checkout with submodules: pick the owning submodule from the issue; ask if unclear.
- Read the guidance chain and profile printed by preflight (nearest first; the profile is `.agents/dev-flow-context.md` or `.claude/dev-flow-context.md`: guardrails, downstream consumers, test convention, base branch, `## Decisions`). Resolve base branch, workspace setup, validation commands and security-sensitive paths from them. With no profile, infer from build files and CI config and confirm once; do not guess.
- Submodule not initialized: ask once before `git submodule update --init --depth 1 <path>`; if declined, read through `git show` or `gh api` and label the evidence as remote.
- `docs/plans` "NOT ignored": ask where handoffs belong (local `.git/info/exclude` entry, a path outside the repo, or accept untracked files). Missing: ask for the planning directory.

## Flags

Require an issue URL or number; resolve the full URL. Dashes on flags are optional.

- Default compatibility is `existing` (consumers and data are preserved). `--greenfield` plans with no live users or data to preserve; it never overrides accepted decisions, weakens controls or redeploys immutable state (planning.md, "Compatibility").
- `--worktree`: the handoff directs execution into a new, approved worktree; planning creates none.
- `--light`: Light depth for confirmed bounded, single-repo, non-sensitive work with no consumed-contract change, migration or architecture decision. Otherwise Full. Raise to Full when risk shows up, even with `--light`.
- `--exec-print <n|gates|ship|all>`: print those file bodies, each in its own fence. Default: outcome, workflow and paths only.

State checkout mode, compatibility and depth in one line after preflight.

## Depth and models

Full runs this session on the Deep tier; Light on Standard (tiers and per-tool switches: [references/runtime-notes.md](references/runtime-notes.md), loaded only when a switch is needed). If the session runs below its tier, say so once and let the user choose to switch or continue; never switch mid-run (it re-bills the whole context) and name no model elsewhere. Stop and ask when Light work turns out to touch a sensitive path, a consumed contract or an architecture decision.

## Questions

For decisions with a preference dimension, use the host's structured question tool if it has one; otherwise list the options as numbered plain text and wait for the reply. Give 2-4 concrete options, recommended first and marked `(Recommended)` with one short reason. Plain short English. Never treat silence or a preselected option as an answer. Look up discoverable facts yourself. Keep questions to material behavior, architecture, security or delivery choices; record each answer with its why and rejected alternative, and never reopen a settled one.

## Steps

1. **Orient.** Preflight, anchor repo, guidance chain, profile. Stop if the issue or source cannot be read.
2. **Investigate.** Read the issue, its comments, linked issues and PRs, and the affected source and tests. Treat the issue as a hypothesis. Pin every fact to the repo SHA and `file:line`; label assumptions and dirty paths. Load [references/planning.md](references/planning.md) for evidence, ownership, security, decision discovery and sizing rules. Run its decision lookup before settling, at either depth.
3. **Settle.** Root cause, owning component, target behavior, rejected alternatives; trace the flow across repos and list consumers. Grill: batch every question whose prerequisites are settled, each with a recommended answer, until no open question remains. Sensitive work needs a fresh-context review before it is ready (planning.md, "Security review").
4. **Size.** Choose compact or phased layout from the actual work (planning.md, "Sizing"); settle PR grouping separately and once.
5. **Plan check (always).** In a few plain sentences: the change, why this layout. List each decision settled beyond what the issue's body and comments already state, one line each; saving posts them to the issue. Ask `Save this plan?` with `Save plan and post decisions (Recommended)` / `Change the plan`; with no new decisions the first option is `Save plan only (Recommended)`. Answer must be explicit.
6. **Write.** Load [references/handoff-spec.md](references/handoff-spec.md). If the plan check listed decisions, post them first as one issue comment ("Decision comment"). A decision settled after that post goes in one follow-up comment; never post a decision twice. Pipe one JSON spec to the renderer; it routes each fact to the files that need it, adds the fixed executor rules, validates in memory and writes only if valid:

   ```sh
   python3 <skill-dir>/scripts/render_handoff.py --out <planning dir> <<'JSON'
   { ...spec... }
   JSON
   ```

   Fix reported errors in the spec and rerun; no hand-edited output. Existing files: ask, then add `--replace-existing`. Files of another layout for the same issue (including an old `<issue>-implementation-prompt.md`) are the user's to resolve; never delete them.
7. **Judge.** The validator checks structure only. Apply [references/quality-checks.md](references/quality-checks.md) for what it cannot judge.
8. **Report.** Outcome, caveats, the ordered execution workflow, every saved path, the decision comment URL. Compact: one new session. Phased: one session per objective, then gates, then ship; unmet prerequisite means STOP. Tell the user to run the gate commands themselves and paste the gates file only if a gate fails or the work is sensitive. The user merges PRs. Say `Planning complete. No implementation performed.` Compare `git status` with preflight, ignoring the written files; report any other change and stop.

## Outcomes other than ready

Stop before the plan check and report plainly, writing no ready handoff: already fixed, cannot reproduce, needs information, wrong repo, duplicate. A blocked plan (missing access, unavailable required review) is labelled blocked with the exact blocker, never presented as ready.

## Economy

- One continuous session from invoke to save: switching model or effort mid-run invalidates the prompt cache.
- Batch independent tool calls in one turn. Use bounded ranges and `rg`; never repeat an unchanged call or re-read an unchanged file.
- Prefer script output (`preflight.py`, renderer report) over reading files. Load a reference only when its step starts.
- Delegate only large read-only sweeps, one reader per repo, summaries back, and only with the user's OK. The sensitive-plan review is separate and required; you still decide what its findings change.
- Handoff files are the cost that repeats: the renderer keeps each objective file to its own facts. Do not add prose to a spec field the file already states.
