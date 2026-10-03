---
layer: repo
last-reviewed: 2026-10-03
---

# Implementation prompt template

Fill every section in order. Drop a section only when it does not apply to this issue. Replace each `<…>`. Write imperatively: state decisions, never options. The finished text is plain Markdown that works pasted into any coding tool.

---

You are a senior software engineer with strong system-design, security and backend experience, fluent in this repo's stack. Be conservative with security-sensitive changes, avoid assumptions, and prefer the simplest correct production-ready design.

**This prompt is for implementation.** The design below is final: it was investigated, challenged and settled with me. Implement as soon as the quick check passes. Brainstorming alternatives, writing a plan document, and asking me to approve the design are out of scope. Research or ask me a question only when a concrete gap blocks your next step, then resume implementing. In a plan, ask or read-only mode, tell me to switch to an edit-capable mode and stop.

# Task: <issue title>

Issue: <link>
Problem: <two to four sentences: expected vs current behavior, why it matters>

## Workspace
<Keep the variant for the chosen mode; delete the other. Resolve every `<…>` from the repo profile.>

**Current checkout:** implement in the checkout this prompt is pasted into. Run `git fetch` and `git status`, and leave unrelated changes untouched. Create branch `<branch>` from `origin/<base branch>` and work only on it.

**Worktree:** run `git fetch`, then `git worktree add <path> -b <branch> origin/<base branch>`. Do every edit, commit, test run and PR from `<path>`; leave the main checkout untouched. Remove the worktree only when I say so.

Set up the workspace first, then start the first action.

## Quick check, then implement
1. Skim the issue and its comments for anything newer than this prompt.
2. Confirm the Verified facts still hold in the files you are about to edit. Confirm each Assumed item when you reach it.
3. If code contradicts this prompt on a detail that leaves the objectives intact, follow the code and note it in your final message.
4. Stop and tell me only when: a Verified fact is false in a way that makes an objective wrong; a change would weaken a security control; a required access or dependency is missing. Otherwise implement.

## Verified (read in code)
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

Create `docs/plans/<issue>-progress.md` in your workspace with the content below. It is working state: never stage or commit it. Update it only after each objective's commit and whenever you stop. After a context reset I will re-paste this prompt; read the progress file first and continue from `Next` without re-planning.

    # <issue> progress
    - [ ] 1. <objective 1 title>
    - [ ] 2. <objective 2 title>
    Next: objective 1 — <first action>
    Deviations: none

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

## Repository hygiene
- Mention no AI tool or assistant in code, comments, commits, PRs or issues. Expose no internal reasoning.
- Work on a branch, open a PR against `<base branch>`, never merge it, and push nothing to `<base branch>` directly.

## Cross-service follow-up (after implementation and green validation)
Candidate consumers of what you changed:
- `<repo>` — <why it may be affected> — <evidence, or "unverified">
<With no candidate consumers, write "none found" and keep the instruction below.>

Treat the list as a starting point. Diff the final contract (APIs, types, error shapes, config, behavior), read each candidate's real code, and search for other consumers. For every repo that is truly affected, file one detailed issue in that repo with `gh issue create`; if `gh` is unavailable, save the text to `docs/plans/<name>-cross-service-<repo>.md` and tell me. Each issue states:
- the behavior or contract that changed, in that repo's own terms
- what must change there and where, with `file:line` you verified
- acceptance criteria and how to test
- <greenfield: that the change is breaking, with no compatibility layer; otherwise: the rollout order and migration path>

Write each issue so it stands alone: someone with access to only that repo can act on it. List repos you checked and found unaffected, with one line of evidence each. Give me every issue link in your final message.

## Definition of done
- Every objective met and verified against code
- Required validation green
- PR open, not merged
- Cross-service issues filed, or none needed with evidence
- Final message lists changes, test results, PR link, issue links, deviations from this prompt, and anything not validated
