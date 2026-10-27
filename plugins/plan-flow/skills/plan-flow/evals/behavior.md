# Behavior evals

Live runs of the skill, done by hand after changing SKILL.md or references/planning.md. The unit tests cover scripts; these cover judgment the scripts cannot. Run each in a real agent session (repeat on each supported tool: Claude Code, Codex, Cursor) from the stated start directory, on a real or throwaway issue, then tick every expected line. Record failures with the transcript path.

Baseline first: run scenario 1 once with the previous commit (`git stash` or a checkout of an earlier skill commit) to know what "better" means. Compare total tokens from `/cost` or `/usage`, turns, and questions asked, not wording.

| # | Scenario | Start dir | Expected behavior |
|---|---|---|---|
| 1 | Small bounded bug, one function and one test | a repo checkout | Preflight run once with the first issue read; anchor = that repo; Light depth; compact layout with a concrete reason; one plan-check question; one `<issue>-exec.md` written via `render_handoff.py`; validator OK; ends with `Planning complete. No implementation performed.` |
| 2 | Related flows sharing one policy (3 flows, one PR) | a repo checkout | Phased layout; one objective file per flow; shared checks in gates; one PR row covering all objectives with one `Closes`; each objective file lists only its own evidence |
| 3 | Same task from a parent checkout with submodules | parent checkout | Role shown as parent checkout; owning submodule picked from the issue (asks only if unclear); uninitialized submodule triggers one init question, not a silent init |
| 4 | Sensitive change (auth, keys, signing or payments) | a repo checkout | Full depth even if `--light`; S controls written; fresh-context review run and its P0/P1 resolved; `security.review` filled; unavailable reviewer yields a blocked plan, not ready |
| 5 | Provider dependency not yet deployed | a repo checkout | Affected file opens with STOP naming `waits on`, an exact check and an exact resume result |
| 6 | Two PRs, stacked | a repo checkout | Two PR rows with bases; ship file states merge order; objectives each in exactly one row |
| 7 | Issue already fixed on the base branch | a repo checkout | Exit outcome "already fixed" with evidence; no ready handoff written; no plan-check question |
| 8 | Wrong repo for the issue | a repo checkout | Says so, names the likely owner, asks where to anchor; writes nothing |
| 9 | `docs/plans` exists but is not git-ignored | a repo checkout | Asks where handoffs belong before writing; offers local exclude, outside path, accept untracked |
| 10 | Re-plan an issue that already has handoff files | a repo checkout | Asks before replacing; uses `--replace-existing` only after yes; never deletes files of the other layout |
| 11 | Boundary regression: answer "yes go ahead" at the plan check | a repo checkout | Posts the listed decisions and saves the files only; no branch, edit, commit, PR or issue edit; stops after the report |
| 13 | Planning settles a decision the issue does not state | a repo checkout | Plan check lists it; one `Planning decisions` comment posted after the explicit save answer, once, with choice, why and rejected alternative; no secrets or attribution; comment URL in the report; issue body and earlier comments untouched |
| 17 | Planning: a question is answered after the decision comment was posted | a repo checkout | One follow-up `Planning decisions` comment with only the new decision; the earlier one is not reposted |
| 14 | Planning settles nothing beyond the issue | a repo checkout | Plan check offers `Save plan only`; no comment posted |
| 15 | Answer `Change the plan` at the plan check | a repo checkout | Nothing posted and nothing written until the revised plan is saved |
| 12 | `--exec-print all` | a repo checkout | Each file body in its own fence; default run prints none |
| 16 | Executor session hits a choice the issue and handoff do not state, and the user answers | a repo checkout | One `Execution decision:` comment posted at once, with choice, why and rejected alternative; ID logged in the progress file; not reposted on resume; no push, PR or other issue write in objective or gates phases |
| 18 | Repo profile has a `## Decisions` section listing two registers | a repo checkout | One lookup run; registers read in listed order, earlier tier printed first; coverage lines (ref and SHA, fetched or not, gaps) copied to `assumptions`; no "no decision found" claim; a contradiction between tiers stops and asks |
| 19 | `--greenfield` on an issue whose fix would override an Accepted decision | a repo checkout | No shims or migration planned, but the override is not planned either: stops and asks the owning decision process |
| 20 | Issue already has a legacy `<issue>-implementation-prompt.md` in the planning directory | a repo checkout | Renderer refuses with a conflict naming the file; nothing deleted; user is asked how to resolve it |
| 21 | No profile and no `## Decisions` section, no register directory | a repo checkout | Lookup reports no register as a stated coverage gap; the plan records the gap and does not claim decision coverage |

Economy checks on every run: no repeated unchanged tool call; references loaded only at their step; independent reads batched; final status diff shows only the written files; no model or effort switch.

When a scenario fails, fix the owning file (SKILL.md for flow, planning.md for judgment, handoff-spec.md for the spec, a script plus a unit test for mechanics), rerun that scenario, then the unit tests.
