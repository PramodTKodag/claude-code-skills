---
name: plan-flow
description: Investigates a GitHub issue against the real code and writes a self-contained canonical implementation prompt plus execution slices derived from it for multi-session implementation, without implementing anything. Use when the teammate runs /plan-flow or wants an issue investigated, grilled, security-audited and cross-service-checked before a different AI session or tool implements it.
argument-hint: "<issue-number-or-url> [--worktree] [--light] [--greenfield] [--no-prompt] [--exec-print <n|gates|ship|all>]"
disable-model-invocation: true
---

# Plan Flow

Investigate one GitHub issue, then write the implementation prompt another session will execute. This session reads, researches, asks, and writes the prompt file and its execution slices. It edits no product code, opens no branch or PR, and saves no memory.

Input: issue link or number, optional `--worktree` (dashes optional), optional `--light`, optional `--greenfield`, optional `--no-prompt`, optional `--exec-print <n|gates|ship|all>`, plus any notes the teammate pasted. Missing issue → ask.

**Checkout mode.** `--worktree` → the prompt directs implementation into a new git worktree. Omitted → the current checkout. Fix the mode now and state it in the preflight message. This session creates no worktree or branch; the coding session does.

**Compatibility mode.** `--greenfield` → the product has no live users, consumers or stored data to preserve, so the plan carries no compatibility or migration work. Omitted → existing consumers and data are assumed, and a breaking change needs a migration or rollout path. Fix the mode now and state it in the preflight message.

**Output mode.** Always save the canonical prompt and its execution slices. Default: print the teammate workflow, objective 1's slice in one fenced block, and the file paths. `--exec-print` picks the slice to print: an objective number, `gates`, `ship`, or `all`. `all` is for archiving; the handoff still tells the teammate to paste one slice per new session. `--no-prompt` → print the workflow and paths only.

## Tiers

| Tier | Work |
|------|------|
| Scout | delta skims, research reading |
| Standard | security-path reads, cross-service trace, prompt self-check; the whole session under Light |
| Deep | this session under Full: grilling, audit, design, writing the prompt |

Concrete model names, mode switches and subagent mechanics per tool: `references/runtime-notes.md`. Never hardcode a model name anywhere else.

## Presets

- **Full** (default): this session runs on Deep.
- **Light**: a small single-repo issue with no security-sensitive path. This session runs on Standard, with no subagents and no second-model plan review.

Chosen once at preflight, never re-asked per phase: a model switch re-bills the whole context.

**Escalate.** A session below Deep (Light, or Full with a missing model) stops when steps 3–5 show a security-sensitive path per the profile, a change to an API, type or behavior another repo consumes, or a decision that alters architecture or security. Name the trigger, then ask: switch to Deep (or plan in a tool that has it) and continue, or stay on this tier.

## 0. Preflight — one message, then proceed

1. **Access.** The repo checkout and `gh` must be reachable. If not, stop and say so; never plan from docs or issue text alone.
2. **Mode.** Switch to the tool's plan / read-only mode. Without one, stay read-only by discipline.
3. **Preset and subagents.** `--light` given → Light, no question. Otherwise ask once, recommended first: Full with subagents, Full without, or Light. Subagents take reads and research off this session's context (fewer tokens here); a tool without them drops that option. Recommend subagents when the issue spans more than one repo or many paths. State checkout mode, compatibility mode, preset and subagent choice in this message.
4. **Model.** This session runs on its preset's tier. On a different tier, print the exact switch for this tool and wait. If the tier's model is missing from the picker, use the strongest available at or below it, never the largest tier, and say so.

## Asking

Use the tool's structured-question UI; else numbered plain text. 2–4 options, recommended first. Ask at the moment a decision appears. Look facts up instead of asking.

## 1. Context

Root `AGENTS.md` or `CLAUDE.md`, if present: reuse it when the tool already loaded it, else read it. Follow only the routing this issue needs, and skip references marked on-demand. Read the anchor repo's profile if present: `.agents/dev-flow-context.md` or `.claude/dev-flow-context.md` (guardrails, neighbors, downstream consumers, test convention, base branch). Neither exists → infer the base branch, validation commands and security-sensitive paths from the repo's build files and CI config, and confirm them once.

Resolve for the chosen checkout mode: base branch, branch pattern, worktree path naming, and the validation commands that exercise the right tree (some stacks false-green when a worktree is tested with main-checkout targets). Mode-specific values missing → ask.

## 2. Issue

`gh issue view <n> --comments`, plus linked issues and PRs. The issue is a hypothesis. Extract the ask, acceptance criteria, constraints, prior decisions.

If the body has `Verified at: <repo>@<sha>` and a `Read first` list: `git fetch`, diff those paths against base, and trust unchanged paths. Re-verify every security-invariant fact regardless.

## 3. Real code, delta only

Read the paths the issue changes and each neighbor it relies on, in line ranges. Source is truth, not docs, comments, or prior summaries. With subagents on, run one reader per repo covering all of its targets, parallel across repos: every spawn loads a fresh base context, so a reader per file multiplies that cost. A repo's security-sensitive paths go to their own reader at Standard. Readers return one summary per target with `file:line`.

Tag every fact **verified** (read, with `file:line`) or **assumed**. Record the commit each repo was read at (`git rev-parse HEAD`, noting uncommitted changes to the paths read); the prompt pins it.

## 4. Cross-service

Trace the flow across repos end to end. Place the fix in the generic component that owns the behavior, never as a downstream workaround. List candidate consumers from the profile's downstream list, if any, and from what the code shows, each with evidence or marked unverified. The prompt carries this list. The coding session edits the anchor repo only: when the component that owns the fix sits in another repo, write no objective or workspace for it. Ask the teammate whether to file an issue there for separate planning, and carry it in this list.

## 5. Security, challenge, research

- **Security.** Audit from code: authn/authz, ownership, signing, keys, replay, input, trust boundaries, logging. A change that weakens a control is a hard stop → ask.
- **Challenge.** Does the proposed fix hit the root cause? Is there a simpler design, a better boundary, existing infrastructure, an unlisted edge case?
- **Compatibility.** With `--greenfield`, plan no compatibility shims, legacy paths, dual support or old-data migrations in product code, and change earlier decisions (the issue's premise, an ADR, an existing API) when a better design is warranted, after asking the teammate. Without it, give every breaking change to an API, type, schema or behavior a migration or rollout path and an entry under "Decided". In both modes keep the smallest correct diff, never relax a security check, and flag already-deployed immutable state (on-chain contracts, shared dev/testnet data) as a cost.
- **Research.** Search online only for time-sensitive or uncertain facts; primary sources; cite. One background reader when subagents are on.

## 6. Grill

Batch every question whose prerequisites are settled, each with a recommended answer. Ask only what materially changes architecture or security: product behavior, ownership, client- vs server-control, security assumptions. Repeat until no open question remains, so the coding session inherits decisions, not choices. Record each decision with its rejected alternatives for the prompt's "Decided" section. Confirm shared understanding before step 7.

## 7. Decide

Settle current behavior, root cause, target design, and concrete changes (files and APIs confirmed in code). Compare alternatives on security, correctness, maintainability, complexity; recommend one. Tests follow the repo's own convention; TDD only where the repo uses it. Make each objective testable on its own: each becomes one coding session, so changes that cannot be tested apart form one objective, and a change too small to justify its own session (a few lines) folds into the objective it supports.

**PR split.** One objective → one PR, no ask. Two or more → ask once, recommended first by coupling and size: one PR (objectives tightly coupled or small together), one PR per objective (each stands alone), or a custom split. Record the answer under "Decided"; with more than one PR, the prompt carries it as the PR plan.

Security-sensitive per the profile (auth, keys or crypto, payments, permissions, or paths it lists): run an independent plan review on Deep before writing. Use a different-vendor model when the tool offers one; else a fresh-context subagent labelled "not independent". Act on P0/P1; on disagreement, ask.

## 8. Write the prompt and its slices

Read `references/prompt-template.md` now, not earlier, and fill it. With two or more objectives, fill its Progress block with the objective titles; the coding session creates that file, never this one. With more than one PR, fill its PR plan from the split. Save it as the canonical prompt, `docs/plans/<issue>-implementation-prompt.md` in the anchor repo.

Then read `references/execution-handoff-template.md` and derive from the canonical prompt one `<issue>-exec-obj-<n>.md` per objective, `<issue>-exec-gates.md` and `<issue>-exec-ship.md`, saved beside it. Never stage any file under `docs/plans/`; say so if the path is not git-ignored.

Self-check before handing over, by one Standard subagent or inline when subagents are off:
- every acceptance criterion maps to an objective
- every verified fact carries `file:line`; assumptions are flagged; the Verified block pins each repo's commit
- no open option or unanswered question remains; each decision sits under "Decided" with its rejected alternatives
- a cold session can start objective 1 with no further research: objectives name confirmed paths, tests are named, validation commands are exact, the first action is concrete
- every objective blocked on an unreleased library, an open issue or another external gate ends with a `waits on:` mark and its check command
- the prompt opens with the implement-now directive and the run rule, and lists only the three mandatory stops
- the Workspace section matches the chosen mode with a resolved path, branch and base, and Validation uses that mode's commands
- the Workspace names one checkout, the anchor repo; every objective edits only it, and a needed change in another repo appears under Cross-service follow-up, never as an objective
- a Progress block exists exactly when there are two or more objectives, and its titles match the Objectives
- a PR plan exists exactly when the split chose more than one PR; every objective sits in exactly one row, and each row names its branch, base and issue keyword (`Closes` on the last row, `Refs` on the others)
- the prompt is lean: no not-applicable section or leftover `<…>` hint, Verified lists only facts an objective or security requirement depends on, and no fact is restated across sections
- the Issue line holds the full issue URL; the hard rule, hygiene, new-decisions-and-findings, after-merge (with the prompt file's absolute path), compatibility and cross-service blocks are present, and the compatibility block matches the chosen mode
- a security-sensitive issue per the profile carries the pre-PR diff review line
- no secrets, key material, or AI-tool names

And for the slices:
- one objective slice per canonical objective, plus the gates and ship slices
- each objective slice meets the template's carry and leave-out lists: one objective, one focused test command, no full gate suite, and no Run rule, push, PR or issue step: ship work sits only in the ship slice, full validation only in the gates slice
- each objective slice stays near 1,800 tokens (about 1,350 words); when over, cut repeats and wording, never a fact
- every canonical Security requirements line appears in the slice of each objective it touches and in the gates slice; standing invariants appear as the template's pointer, not a pasted table
- a slice whose objective waits on an unmet external release or issue opens with a STOP line
- the ship slice's start comment matches Decided, and its PR rows and issue keywords match the canonical PR plan
- objective slices forbid issue comments; the ship slice owns the start comment and every `Decisions:` post from the progress file
- the canonical prompt still passes every check above on its own

Fix gaps. Then reply with a report of at most 25 lines: issue summary, root cause, design, security findings, edge cases, alternatives, open questions. Follow it with the handoff: the template's teammate workflow block, filled; the slice `--exec-print` names (default objective 1; `all` prints each slice) in its own fenced block; and one line listing the canonical prompt and every slice path. With `--no-prompt`, give the workflow block and the paths only. End by suggesting `/clear`.

## Rules

- Tokens: summaries over dumps, line ranges over whole files, no re-reads, scope to the delta.
- Use the repo's own domain terms.
- The prompt names no tool-specific commands or skills.
- Print the teammate workflow block on every handoff, and the chosen slice in a fenced block unless `--no-prompt`; saved files alone are not a handoff.
- Interactive implementation runs from the slices, one new session each, never from a pasted canonical prompt.
- The prompt edits one repo, the anchor repo. Changes elsewhere go to issues, never to objectives.
- No memory writes. No product edits. Git is read-only; write only the prompt and slice files under `docs/plans/`.
