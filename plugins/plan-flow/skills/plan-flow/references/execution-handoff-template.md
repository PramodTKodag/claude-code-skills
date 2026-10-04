---
layer: repo
last-reviewed: 2026-10-04
---

# Execution slices template

Derive these files from the saved canonical prompt after it passes its self-check. The canonical prompt stays the single source of truth and the full handoff for a session that runs the whole issue. The slices let the teammate run one objective per new coding session, so no session carries the whole issue or a long thread. Copy from the canonical prompt; add no scope, fact or decision it lacks. Replace each `<…>` and delete hints that do not apply. Write tool-neutral text: no product, editor or vendor names.

## Files

Save beside the canonical prompt in the anchor repo's `docs/plans/`:
- `<issue>-exec-obj-<n>.md`: one per canonical objective, numbered the same
- `<issue>-exec-gates.md`: validation only
- `<issue>-exec-ship.md`: decision record, side findings, push, PRs, cross-service issues

Aim for 1,200–1,800 tokens per objective slice (about 1,350 words at most); when over, cut repeats and wording, never a fact. The gates and ship slices may run larger, but never restate the whole canonical prompt.

## Objective slice

Carry only what objective `<n>` needs:
- **Workspace setup.** Objective 1, and the first objective of each later PR plan row, creates its branch (from `origin/<base branch>`, or from the previous row's branch tip); every other slice switches to its row's branch.
- **STOP line.** Only when the canonical objective carries a `waits on` mark: name the release or issue and the command that shows whether it is met.
- **Verified.** The facts this objective needs, with the `Verified at` line of each repo they come from.
- **Decided.** The lines this objective relies on, binding ADR or canon lines included.
- **Security.** Copy verbatim the canonical Security requirements lines this objective touches: they are issue-specific and short, and a pointer loses them. For the repo's standing invariants, prefer the binding Decided lines plus one pointer, `Binding: <AGENTS.md or CLAUDE.md section that holds them>; <ADR ids>`, over pasting their tables. None touched → one line saying so. The slice still keeps to the size target. A slice touching a security-sensitive path per the profile marks its title `security-sensitive`.
- **Validate.** One focused command for this objective's tests, from the canonical Validation or the repo profile.

Leave out: other objectives, the Progress template, the PR plan, Cross-service follow-up, the new-decisions and side-findings procedure, After merge, the Definition of done, Verified blocks of repos this objective does not touch, and the full gate suite.

    # <issue> · objective <n> of <N>: <title> <· security-sensitive>

    **STOP: blocked until <dependency>. Check `<command>`; not met → tell me and stop.** <only with a `waits on` mark; else delete this line>

    Implement objective <n> of <full issue URL> now, and only this objective; stop after its commit. The design is final: do not brainstorm, write a plan, or ask me to approve it. Research or ask only when a concrete gap blocks your next step. In a plan, ask or read-only mode, tell me to switch to an edit-capable mode and stop.

    **Hard rule:** mention no AI tool, assistant or model in code, comments or commits (including co-author trailers), and add no "generated with" footers.
    **Scope:** edit only this workspace. Never edit another repository, checkout or objective; when this objective needs a change elsewhere, tell me and stop.

    ## Workspace
    Path `<path>` · branch `<branch>` · base `<base branch>`
    1. `git fetch`, then `<create or switch command>`. Leave unrelated changes untouched.
    2. `git diff <sha> origin/<base branch> -- <paths this objective reads or edits>`. Trust Verified facts in unchanged paths; re-read changed paths and every security-control fact.
    3. Read `docs/plans/<issue>-plan-progress.md` if it exists and run `git log --oneline origin/<base branch>..HEAD`. Follow every decision logged there; if one conflicts with this slice, stop and tell me.
    <Worktree mode: do every edit, commit and test run in `<path>`; leave the main checkout untouched.>

    ## Objective
    <exact change> — files/APIs: `<confirmed paths>`
    Tests: <named tests, in the repo's convention>
    First action: <the concrete first step>

    ## Verified
    Verified at: `<repo>@<sha>`
    - <fact> — `<file:line>`

    ## Decided — do not reopen
    - <decision> — <why>

    ## Security
    - <requirement, verbatim from the canonical prompt>
    Binding: <`AGENTS.md` or `CLAUDE.md` section that holds the invariants>; <ADR ids>.

    ## Validate
    `<focused test command>` must pass before you commit. Never skip git hooks.

    ## Stops
    Stop and tell me only when: a Verified fact is false in a way that makes this objective wrong; a change would weaken a security control; a required access or dependency is missing. Report a security vulnerability as soon as you find it; stop at once only when it sits in code this objective changes.

    ## Commit, log, stop
    Stage by explicit path only (never `git add -A`, `git add .` or anything under `docs/plans/`), then commit. Update `docs/plans/<issue>-plan-progress.md` in the workspace (create it with the lines `# <issue> progress`, `Decisions:` and `Findings:` if missing; never stage it): add `- [x] <n>. <title> — <commit sha>`; under `Decisions:`, each choice this slice did not settle (decision, why, rejected option); under `Findings:`, each defect outside this objective (repo, `file:line`, what is wrong), unfixed.
    Do not push, open a PR, comment on or file any issue, or start another objective.
    Final message: commit SHA, test result, decisions and findings logged.

    Full spec, read only if blocked: `<absolute path of the canonical prompt>`.

## Gates slice

Carry the exact gate commands from the repo profile (`.agents/dev-flow-context.md` or `.claude/dev-flow-context.md`) when present, else from the canonical Validation, for the chosen workspace mode. Write heavy checks that only some changes need as `If <condition>:` lines.

    # <issue> · gates

    Validate <full issue URL> now. Add no feature work: change code only to make a failing check pass, within this issue's objectives. In a plan, ask or read-only mode, tell me to switch to an edit-capable mode and stop.

    **Hard rule:** mention no AI tool, assistant or model in code, comments or commits (including co-author trailers), and add no "generated with" footers.
    **Scope:** edit only this workspace; never another repository or checkout.

    ## Workspace
    Path `<path>` · base `<base branch>` · branches in merge order: `<branch>`<, `<branch-2>`>
    `git fetch`, then read `docs/plans/<issue>-plan-progress.md`. Gate only branches whose objectives are all checked there.
    Stop and tell me only when: a fix would weaken a security control or change the design; a required access or dependency is missing.

    ## Gates
    Run on each branch in merge order. Fix a failure on the branch that introduced it, stage by explicit path, commit, then `git merge` that branch into each later branch. Never skip git hooks.
    - `<format command>`
    - `<lint command>`
    - `<build command>`
    - `<full test command>`
    - `<security scan command>`
    - If <condition, e.g. the dependency lock file changed>: `<command>`
    <Worktree mode: main-checkout targets exercise the wrong tree; these are the worktree commands.>

    ## Security re-read
    Re-read `git diff origin/<base branch>...<last branch>` as a security reviewer against:
    - <every canonical Security requirements line, verbatim; none → "no change to a security control">
    Fix what falls within the objectives; log anything else under `Findings:` in the progress file.

    ## Report, then stop
    Add `Gates: green at <branch>@<sha>` per branch, or `Gates: failed — <check>`, to the progress file. Final message: each command with pass or fail, fixes with commit SHAs, what the security re-read checked, anything not run and why. Do not push, open a PR or comment on any issue.

## Ship slice

Write the start comment ready to post, from the canonical Decided section. Copy the PR plan rows (one row when there is one PR) and the Cross-service follow-up and After merge sections verbatim.

    # <issue> · ship

    Ship <full issue URL> now: post the decision record, resolve side findings, push, open the PRs and file cross-service issues. Implement no objective. In a plan, ask or read-only mode, tell me to switch to an edit-capable mode and stop.

    **Hard rule:** mention no AI tool, assistant or model anywhere: not in code, comments, commits (including co-author trailers), issues, issue comments, PRs or PR comments, and add no "generated with" footers. Expose no internal reasoning.
    **Scope:** change branches and PRs only in this workspace; in other repos file issues only, and edit nothing there.

    ## Check
    Path `<path>`. Read `docs/plans/<issue>-plan-progress.md`. Ship only PR rows whose objectives are all checked. Each shipped branch needs a `Gates: green` line at its current tip; when one is missing or stale, ask me whether gates passed.
    Stop and tell me only when: a change would weaken a security control; a required access or dependency is missing.

    ## Decision record
    Post this start comment on the issue once (`gh issue comment`):
    <root cause and target design, one line each; every Decided item with why and the rejected alternative; the compatibility mode with its migration or rollout path>
    Then post one comment per entry under `Decisions:`: decision, why, rejected alternative. Plain prose only: no progress chatter, code, secrets, key material or exploit detail.

    ## Side findings
    When `Findings:` has items, show the list once and ask per item: another repo → file an issue there, yes or no; this repo → file an issue, or fold the fix into this PR (then run its focused test and the gates, stage by explicit path and commit). Write approved issues in the Cross-service follow-up format. Comment each resolution on the issue.

    ## Push and open PRs
    Per row, in merge order: check `git diff --stat origin/<row base>...<branch>`; if it outgrew a reviewably small PR (many files, several hundred lines, mixed concerns), ask me whether to split it. Then `git push -u origin <branch>` and open the PR against the row's base, with the row's keyword in the body:
    1. `<branch>` → `<base branch>` — objectives <1–2> — `Refs #<issue>`
    2. `<branch-2>` → `<branch>` — objective <3> — `Closes #<issue>`
    With more than one row, tell me in your final message to merge in row order and to check, before merging each later PR, that it now targets `<base branch>`: GitHub retargets it only when the branch below is deleted on merge, and `Closes` fires only on a merge into the default branch.
    Write `owner/repo#<issue>` when the issue lives in another repo. A PR that leaves an acceptance criterion open uses `Refs` and names that criterion. Never merge a PR, and push nothing to `<base branch>` directly.

    ## Cross-service follow-up
    <the canonical section, verbatim>

    ## After merge
    <the canonical section, verbatim>

    Final message: PR links, issue links, comments posted, how each finding was resolved, deviations from the plan, anything not validated.

## Teammate workflow

Print this block, filled, on every handoff.

    ## How to run this issue in a coding agent

    1. Open **only** the anchor checkout named in Workspace: `<path>` (not a parent monorepo unless that is the anchor).
    2. **New session** → paste **only** the contents of `docs/plans/<issue>-exec-obj-1.md`. It implements and commits once this objective's tests pass.
    3. **Clear context** (new session). Do not continue the old thread.
    4. For each remaining objective (none when there is only one): **new session** → paste **only** `<issue>-exec-obj-<n>.md` in order.
    5. If a slice starts with **STOP** (dependency not ready), skip it until unblocked. Gates and ship handle only PR rows whose objectives are all done.
    6. **Clear context** → paste **only** `<issue>-exec-gates.md`, **or** run its commands yourself.
    7. **Clear context** → paste **only** `<issue>-exec-ship.md`. It posts the decision record, asks about side findings, pushes and opens the PRs linked to the issue. You merge, in PR plan order. Opening the PRs yourself instead? Skip pasting it and copy the start comment, each row's `Closes`/`Refs` keyword and the cross-service issues from it.
    8. **Never** paste `<issue>-implementation-prompt.md` into a coding session, and do not attach it unless you are debugging a single blocker.
    9. Every slice printed at once (`--exec-print all`) is for copying or archiving only. Still run one slice per new session; never paste several slice files into one thread.

    Pin a fast default model for routine slices and a stronger one for slices marked security-sensitive; avoid automatic routing to expensive models.
