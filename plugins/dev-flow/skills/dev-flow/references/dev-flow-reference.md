# Dev Flow — shared reference

Generic supporting material for the `/dev-flow` skill, loaded on demand. Repo-specific detail (guardrails,
toolchain, green-gate commands, reviewer routing, conditional triggers) lives in each repo's
`.claude/dev-flow-context.md`, NOT here.

## Contents
- Engineering charter
- Resume map
- Worktree mode
- Merge strategy
- Ledger template
- Naming & message formats
- Context-file template (how to onboard a repo)

## Engineering charter

Inject verbatim into every dispatched subagent (the `dev-flow-executor` agent has it baked in):

- Senior engineer, system-design mindset. Security invariants (per the repo's domain guardrails) are
  acceptance criteria, not guidance. Industry standards; real data only — only test cases may use fake data,
  never real code paths.
- No temporary fixes, workarounds, shims, or TODO-hacks. Sustainable root-cause solutions only; smallest
  correct diff, no speculative abstraction.
- The repo's execution convention (TDD / tests-alongside / plan-walk) and DDD / hexagonal architecture where
  it applies, strictly. Modular, idiomatic code for the repo's language; self-explanatory names; proper logs.
- Reuse-first, not reuse-forced: search for an existing fit before adding a new type/helper/port/pattern;
  build new cleanly when nothing fits rather than contorting the change.
- Follow the repo's code-structure conventions (templates/patterns named in its context file) and this
  plugin's `PRINCIPLES.md`.
- Never assume — stop and ask the teammate on any real ambiguity. Ask during the work, not after.
- No cross-service refs, `#NNN`-in-code, or Claude/Anthropic attribution in commits/PRs/issues/comments.

## Resume map

Map the ledger's `Status` to the entry point (Step 0 reads this):

| Ledger `Status`                     | Resume by                                                              |
| ----------------------------------- | ---------------------------------------------------------------------- |
| `Phase n · Task t · in-progress`    | Re-enter Step 5 at that task; run it under the ledger's `Execution` line. |
| `... · blocked`                     | Read the block reason in the ledger; resolve or ask the teammate, then continue. |
| `... · awaiting-approval`           | Present the pending recap/plan; get the gate, then proceed.            |
| `... · PR-open·awaiting-CR`         | Go to Ship & code review — handle CR on the open PR.                   |
| `all-phases-shipped`                | Final review (if not done), else teardown once the teammate confirms all merged. |

Always honor the ledger's `Next` line — it is the authoritative next action.

## Worktree mode

Invoked with `--worktree` (dashes optional). From the anchor repo, once per issue (`<issue>` = normalized number):

```
git worktree add ../<svc>-worktrees/<svc>-<issue> -b feat/<issue> origin/<base-branch>
```

Anchor there instead of the launch checkout; all edits/commits/branches/PRs/ledger live in it. `<base-branch>`
and any stack-testing caveats come from the repo's context file (some stacks false-green if run against the
main checkout — see the context file's green-gate notes). Remove the worktree only on the teammate's say-so
after merge.

## Merge strategy (the teammate merges; the manager only advises)

Stacked PRs land **bottom-up**: merge the lowest open PR first (squash), then **restack** each child onto the
updated base before merging it, repeating up the stack. Never merge top-down, never collapse a child into its
parent, never force-push a rewrite of a published branch (use a forward `git revert`). The manager advises the
order; the teammate performs the merges.

## Ledger template

Write to `docs/plans/<issue>-progress.md` in the anchor repo. `Status` and `Next` are the authoritative resume
point; keep them current.

```markdown
# <svc> #<issue> — <title>

Anchor: <repo>   Neighbors (read-only): <list>
Execution: <tdd|executing-plans|tests-alongside> · <subagent-driven|inline>
PRs: <grouping settled in Step 4 — e.g. "PR1 = phases 1-3 · PR2 = phase 4", or "one PR per phase", or "single PR">
Status: Phase <n>/<N> · Task <t> · <in-progress|blocked|awaiting-approval|PR-open·awaiting-CR|all-phases-shipped>
PR stack: #<x> (phases 1-3, open) · #<y> (phase 4, merged) · …

## Goal
<one paragraph>

## Decisions & open questions
- <decision> — <why>
- OPEN: <question awaiting teammate>

## Plan
### Phase 1 — <name>  (PR #<x>)
- [x] Task 1 — <desc> — files: <declared paths> — commit <sha>
- [ ] Task 2 — <desc> — files: <declared paths>
### Phase 2 — <name>
- [ ] …

## Follow-ups filed
- <repo>#<n> — <desc>

## Next
<exact next action so a cold session resumes here>
```

## Naming & message formats

One house format for branches, commits, and PRs so the stack reads cleanly and auto-links to the issue. The
`<type>` is the Conventional-Commit vocabulary everywhere — pick the one matching the change's primary intent:

| `<type>`   | Use when the change…                                                              |
| ---------- | --------------------------------------------------------------------------------- |
| `feat`     | adds or extends user-facing behaviour / a new capability                          |
| `fix`      | corrects a bug in existing behaviour                                              |
| `refactor` | restructures code with **no** behaviour change (rename, move, extract, DDD slice) |
| `perf`     | improves performance without changing behaviour                                   |
| `chore`    | build, deps, tooling, pointer bumps — no `src` behaviour                           |
| `docs`     | documentation / skills / comments only                                            |
| `test`     | adds or fixes tests only                                                           |

- **Branch** — `<type>/<issue>-<kebab-slug>` (slug = 2–4 word summary). Per-PR branches add a phase segment:
  `<type>/<issue>-p<n>-<slug>`. Worktree mode uses the same base name. Never work on the base branch directly.
- **Commit** — `<type>(<scope>): <summary>`, imperative and lowercase after the colon, summary ≤ ~72 chars
  naming the **concrete** change (not "update code"). Body (wrapped ~72 cols) states **what changed and why**;
  skip the "how". One task = one commit. Footer: `Refs #<issue>` (intra-repo only). **Never**: cross-service
  `svc#NNN` refs, any `#NNN` inside code/comments, Claude/Anthropic attribution.
- **PR** — title = the headline Conventional-Commit line. Body describes the **actual** change:
  - **What** — the concrete changes (bullet the real edits).
  - **Why** — the problem / issue goal it serves.
  - **How tested** — commands run and their result (tie to the green gate + any E2E evidence).
  - **Risk & rollback** — blast radius and how to revert.
  - **Stack** — `Stacked on #<parent>` when it builds on an earlier PR.
  - **Issue** — `Closes #<issue>` only on the PR completing the issue; `Refs #<issue>` on earlier ones.
  No cross-service refs, no Claude/Anthropic attribution.

## Context-file template (how to onboard a repo)

To use `/dev-flow` in a repo, add `.claude/dev-flow-context.md` following this shape. Keep it LEAN — it loads
fully into the driver at Step 1. Push heavy howtos/tables into a sibling `.claude/dev-flow-context/` reference
if they grow. **Security/domain guardrails are acceptance criteria — write them precisely; they are applied
verbatim and injected into every subagent.**

```markdown
# dev-flow context — <svc>

## Identity
- What this repo is (one paragraph), its role, and its base branch (`dev` | `main` | `testnet`).
- Neighbors (read-only deps) and how to list them (imports / `go list -m all` / package manifest).
- Worktree naming: `../<svc>-worktrees/<svc>-<issue>`.
- Execution convention: TDD | tests-alongside | plan-walk (only if it differs from the default TDD).

## Domain guardrails (SECURITY — acceptance criteria, applied verbatim)
- <the repo's hard rules — key-material / self-custody / on-chain / protocol invariants, as applicable>.
- A change that would weaken any of these is a HARD STOP.
- (If the repo has no security-sensitive surface, state that explicitly so nothing is copy-pasted in.)

## Toolchain & green-gate commands
- Build / lint / test / security-scan commands for this stack, and the ONE full-checkpoint sequence.
- Any safety notes (e.g. shared dev stack already running; worktree false-green caveats).

## Reviewer routing (only reviewers that exist for THIS repo)
| Change surface | Reviewer agent |
| -------------- | -------------- |
| <surface>      | <agent>        |

## Conditional triggers (fire only when the diff matches)
| Diff touches… | Fire | Where |
| ------------- | ---- | ----- |

## Downstream-contract drift
- Which downstream repo's tests this repo's contracts feed (or "none").
```
