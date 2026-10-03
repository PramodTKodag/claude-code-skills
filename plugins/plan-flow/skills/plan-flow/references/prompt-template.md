---
layer: repo
last-reviewed: 2026-10-03
---

# Implementation prompt template

Fill every section in order. Keep the prompt lean, since the coding session carries it in context for the whole run: delete each section, bullet and `<…>` hint that does not apply to this issue, list under Verified only the facts an objective or security requirement depends on, and state each decision in one line. Replace each `<…>`. Write imperatively: state decisions, never options. The finished text is plain Markdown that works pasted into any coding tool.

---

You are a senior software engineer with strong system-design, security and backend experience, fluent in this repo's stack. Be conservative with security-sensitive changes, avoid assumptions, and prefer the simplest correct production-ready design.

**This prompt is for implementation.** The design below is final: it was investigated, challenged and settled with me. Implement as soon as the quick check passes. Brainstorming alternatives, writing a plan document, and asking me to approve the design are out of scope. Research or ask me a question only when a concrete gap blocks your next step, then resume implementing. In a plan, ask or read-only mode, tell me to switch to an edit-capable mode and stop.

**Hard rule:** mention no AI tool, assistant or model anywhere: not in code, comments, commits (including co-author trailers), issues, issue comments, PRs or PR comments, and add no "generated with" footers. Expose no internal reasoning.

**Scope rule:** change files, branches and PRs only in this repo's workspace. Never edit, stage, commit or push in any other repository or checkout: not a sibling clone, a submodule, or another worktree. When an objective needs a change elsewhere, make no edit there: ask me how to proceed, file an issue in that repo once I agree (format under Cross-service follow-up), and continue only with work that does not depend on it.

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
1. <exact change> — files/APIs: `<confirmed paths>`

**First action:** <the concrete first step, e.g. write the failing test `<name>` in `<path>`, or change `<function>` in `<file>`>

## Progress file
<Include only with two or more objectives; otherwise delete this section. Fill the checklist from the Objectives.>

Create `docs/plans/<issue>-plan-progress.md` in your workspace with the content below. It is working state: never stage or commit it. Update it only after each objective's commit and whenever you stop. After a context reset I will re-paste this prompt; read the progress file first and continue from `Next` without re-planning.

    # <issue> progress
    - [ ] 1. <objective 1 title>
    - [ ] 2. <objective 2 title>
    Next: objective 1 — <first action>
    Decisions: none
    Findings: none

## Security requirements
<authn/authz, ownership, key and custody boundaries, replay, input validation, logging of sensitive data — only those this change touches. State which existing controls must stay intact.>

## Constraints
- **Compatibility.** <Keep the variant for the chosen mode; delete the other.>
  - Greenfield: there are no live users, consumers or stored data to preserve. Add no compatibility shims, legacy paths, dual support or old-data migrations in product code. Change contracts cleanly.
  - Existing consumers: keep public contracts and stored data working. Ship every breaking change with the migration or rollout path named under Decided.
- Smallest correct diff. No speculative abstraction, dead code, temporary fixes, hardcoded workarounds, debug-only logic or special-case headers.
- Follow the repo's own conventions and layout. Use DDD terms only where the repo already uses them.
- Clear names, small focused modules, idiomatic code, proper error handling, useful structured logs. Production code uses real flows and data; fake data only in tests.
- Use the repo's own domain terms.

## Read first
- `<path>` — <why>

## Behavior, API, data, errors, logging
<only the requirements this change adds or alters>

## Tests
<the repo's test convention; the behavior, security, integration and regression tests to add, by name; existing coverage to leave alone>

## Validation
<exact format, lint, test, build commands from the repo profile for the chosen workspace mode. In worktree mode, state that main-checkout targets exercise the wrong tree and use the profile's worktree commands. Run the full set once before pushing; never skip git hooks.>

<Security-sensitive issues only; delete this paragraph otherwise.> Before opening the PR, re-read your full diff as a security reviewer against the Security requirements above, fix what you find, and report what you checked in your final message.

## Repository hygiene
- Work on a branch, open a PR against `<base branch>`, never merge it, and push nothing to `<base branch>` directly.

## New decisions and side findings
**Decisions.** Before objective 1, post one comment on the issue (`gh issue comment`): the root cause and target design in one line each, every item under Decided (decision, why, rejected alternative), and the compatibility mode with its migration or rollout path. Then post a comment for every later decision this prompt does not already settle: a deviation from it, an answer I gave you, how a side finding was resolved. State the decision, why, and the alternative you rejected. Post later comments at the points where you update the progress file, or before opening the PR when there is none, and mark each posted decision, the start comment included, under `Decisions`. Write plain prose: no progress chatter, code, secrets, key material or exploit detail.

**Side findings.** You may find a defect or gap outside the objectives, in this repo or another. Do not fix or file it on your own. Note it in one line (repo, `file:line`, what is wrong) under `Findings` when the progress file exists, else in your notes; keep implementing; and show me the list once before opening the PR. For each item, ask me: another repo → file an issue there, yes or no; this repo → file an issue, or fold it into this PR. Report a security vulnerability immediately instead of waiting. Write approved issues in the format under Cross-service follow-up. Everything you post follows the hard rule above.

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

## Definition of done
- Every objective met and verified against code
- Required validation green
- <Security-sensitive only: full-diff security review done and reported>
- PR open, not merged
- Every change is inside this repo's workspace
- Cross-service issues filed, or none needed with evidence
- Start comment and every new decision commented on the issue; side findings resolved as I decided
- Final message lists changes, test results, PR link, issue links, deviations from this prompt, and anything not validated
