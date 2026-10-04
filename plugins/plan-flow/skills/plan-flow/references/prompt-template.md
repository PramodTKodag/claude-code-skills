---
layer: repo
last-reviewed: 2026-10-04
---

# Implementation prompt template

Fill every section in order. Keep the prompt lean, since the coding session carries it in context for the whole run: delete each section, bullet and `<…>` hint that does not apply to this issue, list under Verified only the facts an objective or security requirement depends on, one line each, and state each decision in one line. State each fact once, in the section that owns it; elsewhere cite its `file:line` instead of restating it. Aim for about 4.5k tokens; when over, cut repeats and wording, never a fact an objective, test or security requirement needs. Replace each `<…>`. Write imperatively: state decisions, never options. The finished text is plain Markdown that works pasted into any coding tool.

**Multi-session implementation.** This canonical prompt is the single source of truth and must stay complete for one long implementing session. For interactive coding sessions the teammate runs the execution slices from `execution-handoff-template.md` instead (`exec-obj-*`, `exec-gates`, `exec-ship`), one slice per new session; they never replace this file on disk. The Run rule below governs only a session that runs this whole prompt: objective slices never push, open PRs or run every objective, and that ship work belongs to `exec-ship.md`. When the teammate uses execution slices, objective slices never comment on the issue; they log choices only under `Decisions:` in `docs/plans/<issue>-plan-progress.md`. The start comment and every posted decision comment happen in `exec-ship.md` only. The **New decisions and side findings** section below applies to a single session that runs this whole prompt, not to slice sessions.

---

You are a senior software engineer with strong system-design, security and backend experience, fluent in this repo's stack. Be conservative with security-sensitive changes, avoid assumptions, and prefer the simplest correct production-ready design.

**This prompt is for implementation.** The design below is final: it was investigated, challenged and settled with me. Implement as soon as the quick check passes. Brainstorming alternatives, writing a plan document, and asking me to approve the design are out of scope. Research or ask me a question only when a concrete gap blocks your next step, then resume implementing. In a plan, ask or read-only mode, tell me to switch to an edit-capable mode and stop.

**Hard rule:** mention no AI tool, assistant or model anywhere: not in code, comments, commits (including co-author trailers), issues, issue comments, PRs or PR comments, and add no "generated with" footers. Expose no internal reasoning.

**Scope rule:** change files, branches and PRs only in this repo's workspace. Never edit, stage, commit or push in any other repository or checkout (sibling clone, submodule, other worktree). When an objective needs a change elsewhere, ask me, file an issue in that repo once I agree (format under Cross-service follow-up), and continue only with work that does not depend on it.

**Run rule:** carry the work through to the Definition of done in this run. Commit each objective, push, open each PR in order, and start the next objective without asking me first and without stopping to report progress. Pause only for a stop listed under Quick check, a change needed in another repo (Scope rule), a PR that outgrew a reviewable size, or side findings to decide before a PR.

# Task: <issue title>

Issue: <full GitHub issue URL; comment target for new decisions>
Problem: <two to four sentences: expected vs current behavior, why it matters>

## Workspace
<Keep the variant for the chosen mode; delete the other. Resolve every `<…>` from the repo profile.>

**Current checkout:** implement in the checkout this prompt is pasted into. Run `git fetch` and `git status`, and leave unrelated changes untouched. Create branch `<branch>` from `origin/<base branch>` and work only on it.

**Worktree:** run `git fetch`, then `git worktree add <path> -b <branch> origin/<base branch>`. Do every edit, commit, test run and PR from `<path>`; leave the main checkout untouched. Remove the worktree only when I say so.

Set up the workspace first, then start the first action.

## Quick check, then implement
1. Skim the issue and its comments for anything newer than this prompt.
2. Run `git diff <sha> origin/<base branch> -- <Read first paths and every file you will edit>` (re-read those paths if the SHA is unreachable). Trust Verified facts in unchanged paths; re-read changed paths and every security-control fact. Confirm each Assumed item when you reach it.
3. If code contradicts this prompt on a detail that leaves the objectives intact, follow the code and record it as a new decision.
4. Stop and tell me only when: a Verified fact is false in a way that makes an objective wrong; a change would weaken a security control; a required access or dependency is missing. Otherwise implement.

## Verified (read in code)
Verified at: `<repo>@<sha>` (one line per repo read)
- <fact> — `<file:line>`

## Assumed (confirm before relying on it)
- <claim> — why it is unverified

## Root cause
<what the code does today and exactly why the issue exists>

## Target design
<where responsibility belongs, which component stays generic, what the end state looks like>

## Decided — do not reopen
- <decision> — <why>. Rejected: <option> because <reason>.

## Objectives (in this order)
1. <exact change> — files/APIs: `<confirmed paths>` <— waits on: `<owner issue or release>`; check: `<command that shows it is met>`. Only when the objective depends on an unreleased library, an open issue or another external gate; execution slices turn this into their STOP line.>

**First action:** <the concrete first step, e.g. write the failing test `<name>` in `<path>`, or change `<function>` in `<file>`>

## PR plan
<Include only when the split chose more than one PR; otherwise delete this section. One row per PR in merge order; every objective sits in exactly one row; name each branch like `<branch>`. The last row closes the issue; every earlier row refs it.>

Open one PR per row, in order, each against the base its row names. Cut each later branch from the previous PR's branch tip in the same workspace. With more than one row, tell me in your final message to merge in row order and to check, before merging each later PR, that it now targets `<base branch>`: GitHub retargets it only when the branch below is deleted on merge, and `Closes` fires only on a merge into the default branch.
1. `<branch>` → `<base branch>` — objectives <1–2> — `Refs #<issue>`
2. `<branch-2>` → `<branch>` — objective <3> — `Closes #<issue>`

## Progress file
<Include only with two or more objectives; otherwise delete this section. Fill the checklist from the Objectives.>

Create `docs/plans/<issue>-plan-progress.md` in your workspace with the content below. It is working state: never stage or commit it. Update it only after each objective's commit, each PR you open, and whenever you stop. After a context reset I will re-paste this prompt; read the progress file first and continue from `Next` without re-planning.

    # <issue> progress
    - [ ] 1. <objective 1 title>
    - [ ] 2. <objective 2 title>
    Next: objective 1 — <first action>
    Decisions: none
    Findings: none
    PRs: none opened

## Security requirements
<authn/authz, ownership, key and custody boundaries, replay, input validation, logging of sensitive data — only the issue-specific behaviors this change touches (auth path, storage, events and the like). State which existing controls must stay intact. Do not paste the repo's invariant tables; cite them in the Binding line below.>
Binding: obey <the `AGENTS.md` or `CLAUDE.md` section that holds the invariants>; <ADR ids already under Decided>. <Delete this line when the repo has neither.>

## Constraints
- **Compatibility.** <Keep the variant for the chosen mode; delete the other.>
  - Greenfield: there are no live users, consumers or stored data to preserve. Add no compatibility shims, legacy paths, dual support or old-data migrations in product code. Change contracts cleanly.
  - Existing consumers: keep public contracts and stored data working. Ship every breaking change with the migration or rollout path named under Decided.
- Smallest correct diff. No speculative abstraction, dead code, temporary fixes, hardcoded workarounds, debug-only logic or special-case headers.
- Follow the repo's own conventions, layout and domain terms; use DDD terms only where the repo already uses them.
- Clear names, small focused modules, idiomatic code, proper error handling, useful structured logs. Production code uses real flows and data; fake data only in tests.

## Read first
- `<path>` — <why>

## Behavior, API, data, errors, logging
<only the requirements this change adds or alters>

## Tests
<the repo's test convention; the behavior, security, integration and regression tests to add, by name; existing coverage to leave alone>

## Validation
<exact format, lint, test, build commands from the repo profile for the chosen workspace mode, one line each; where one Make target runs the same checks, name that target instead of its parts. In worktree mode, state that main-checkout targets exercise the wrong tree and use the profile's worktree commands. Run the full set once before pushing; never skip git hooks.>

<Security-sensitive issues only; delete this paragraph otherwise.> Before opening the PR, re-read your full diff as a security reviewer against the Security requirements above, fix what you find, and report what you checked in your final message.

## Repository hygiene
- Work on a branch and open a PR against `<base branch>` (with a PR plan: each PR against the base its row names). Never merge a PR, and push nothing to `<base branch>` directly.
- Link the issue in every PR body: `Closes #<issue>` on the PR that completes it (the only PR, or the last PR plan row), `Refs #<issue>` on every other PR; write `owner/repo#<issue>` when the issue lives in another repo. A PR that leaves an acceptance criterion open uses `Refs` and names that criterion.
- Before opening any PR, check its diff. If it outgrew a reviewably small PR (many files, several hundred lines, or mixed concerns), stop and ask me whether to split it further.

## New decisions and side findings
**Decisions.** Before objective 1, post one issue comment (`gh issue comment`): root cause and target design in one line each, every Decided item (decision, why, rejected alternative), and the compatibility mode with its migration or rollout path. Then comment every later decision this prompt does not settle (a deviation from it, an answer I gave you, how a side finding was resolved): decision, why, rejected alternative. Post them when you update the progress file, or before opening the PR when there is none, and mark each posted decision, the start comment included, under `Decisions`. Plain prose only: no progress chatter, code, secrets, key material or exploit detail.

**Side findings.** A defect or gap outside the objectives, in this repo or another: do not fix or file it on your own. Note it in one line (repo, `file:line`, what is wrong) under `Findings`, or in your notes when there is no progress file, and keep implementing. Before opening the PR, when the list has items, show it once and ask per item: another repo → file an issue there, yes or no; this repo → file an issue, or fold it into this PR. Report a security vulnerability in a message as soon as you find it, then keep implementing; it joins that list. Stop and ask at once only when it sits in code your objectives change or makes an objective unsafe to ship. Write approved issues in the Cross-service follow-up format. Everything you post follows the hard rule.

## Cross-service follow-up (after implementation and green validation)
Candidate consumers of what you changed:
- `<repo>` — <why it may be affected> — <evidence, or "unverified">
<With no candidate consumers, write "none found" and keep the instruction below.>

Treat the list as a starting point. Diff the final contract (APIs, types, error shapes, config, behavior), read each candidate's real code, and search for other consumers. For every repo that is truly affected, file one detailed issue in that repo with `gh issue create` (an issue only; edit nothing there); if `gh` is unavailable, save the text to `docs/plans/<name>-cross-service-<repo>.md` and tell me. Each issue states:
- the behavior or contract that changed, in that repo's own terms
- what must change there and where, with `file:line` you verified
- acceptance criteria and how to test
- <greenfield: that the change is breaking, with no compatibility layer; otherwise: the rollout order and migration path>

Write each issue so it stands alone: someone with access to only that repo can act on it. List repos you checked and found unaffected, with one line of evidence each. Give me every issue link in your final message.

## After merge
Delete the planning files only after every PR you opened for this issue is merged. When I say they are, confirm each with `gh pr view <number> --json state` reporting `MERGED`; if any is not merged, keep all planning files (canonical prompt, every exec slice, and the progress file if it exists) and tell me which PRs are still open. Then list the files below and ask me to confirm; on yes, delete them:
- `<absolute path of this prompt file>` and every `<issue>-exec-*.md` beside it, in the main checkout
- the progress file in your workspace, if one exists

## Definition of done
- Every objective met and verified against code
- Required validation green
- <Security-sensitive only: full-diff security review done and reported>
- Every PR open (one per PR plan row when there is a plan), linked to the issue with `Closes` or `Refs`, none merged
- Every change is inside this repo's workspace
- Cross-service issues filed, or none needed with evidence
- Start comment and every new decision commented on the issue; side findings resolved as I decided
- Final message lists changes, test results, PR links, issue links, deviations from this prompt, and anything not validated
