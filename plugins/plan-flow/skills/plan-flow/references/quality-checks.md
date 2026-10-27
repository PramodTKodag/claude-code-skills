# Quality checks

Contents: Before saying ready · Maintaining this skill

The renderer and validator already enforce: layout completeness, placeholders, header fields, issue URL, Base format, matching Compatibility, AC and S coverage and verbatim S text, `pipefail` on piped commands, absolute Workspace paths, leading STOP for waits, one PR row per objective with one `Closes`, and soft size budgets. Do not re-check those by hand. Judge only what a script cannot.

## Before saying ready

- Planning stayed planning: nothing executed from a template, no product edit, branch, commit, PR, issue edit or memory write; the status diff against preflight shows only the written files. The only external write is the approved decision comment: posted once, after the save answer, matching what the plan check listed, with nothing sensitive.
- The plan check was answered explicitly before the files were written.
- Sizing fits the work: compact has a concrete small-session reason; phased objectives are real behavior boundaries, not fragments; related flows were not collapsed into one giant objective.
- Evidence is real: each claim was read at the recorded SHA, `file:line` exists, assumptions are labelled, dependency versions are resolved. No open design options remain in the spec.
- Every issue acceptance criterion maps to a verifiable outcome; named tests exist or name a new file in a verified parent.
- Security: all touched controls are covered, S text states the actual requirement, sensitive plans have a completed fresh-context review with P0/P1 resolved.
- Conditional gates match the repo's path-triggered checks.
- Governing decisions were followed, earlier register before later, from a lookup run in this session; coverage limits are stated, not "none found".
- Compatibility matches the chosen mode, and greenfield overrides no accepted decision, control or immutable state.
- PR grouping, base branches and branch names match repo policy. Rollback is real for this change.
- Each file stands alone: an executor with only that file and the repo can start, stop and report correctly.

## Maintaining this skill

- Change behavior only with a test: `cd scripts && python3 -B -m unittest discover -p 'test_*.py'` (renderer, validator, preflight, decision lookup, portability; throwaway local repos only, no network, no product code).
- Token budgets in `handoff_common.py` stay about twice the rendered sample sizes; re-tune from `evals/specs` renders after any rule-text change. Sizes are chars/4 proxies; real usage needs measured runs.
- `evals/behavior.md` lists live planning scenarios to run by hand after a change to SKILL.md or planning.md. Compare outcomes (layout, questions asked, boundary held, files valid), not wording.
- Keep SKILL.md under about 100 lines and every reference one level deep; new rules go to the file loaded at the step that needs them.
