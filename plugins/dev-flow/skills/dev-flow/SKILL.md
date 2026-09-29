---
name: dev-flow
description: "Use when the teammate runs /dev-flow or asks to drive a large, multi-phase or multi-PR change on a repo through the full flow end to end — plan, execute task-by-task with a live ledger, ship per PR, and resume cleanly across sessions. Works in any repo that has a .claude/dev-flow-context.md."
when_to_use: >-
  Use when the teammate says "/dev-flow", "start the flow on <issue>", "drive <issue> end to end",
  "work on <issue> with the full flow", or "resume <issue>". One sustained driver for a change that
  spans multiple tasks/PRs, needs deep understanding, and must survive being paused and resumed later
  without losing work or decisions. Requires a per-repo .claude/dev-flow-context.md.
user-invocable: true
disable-model-invocation: true
argument-hint: "<issue-number-or-url> [--worktree]"
arguments:
  - name: issue
    description: "GitHub issue number or URL for the anchor repo. Omitted = infer from the current branch, or from an in-progress ledger."
    required: false
  - name: worktree
    description: "Pass `--worktree` (or bare `worktree`) to run this issue in its own git worktree instead of the current checkout. Omitted = current checkout."
    required: false
allowed-tools:
  - Read
  - Grep
  - Glob
  - Write
  - Edit
  - Agent
  - Skill
  - AskUserQuestion
  - TaskCreate
  - TaskUpdate
  - TaskList
  - WebSearch
  - WebFetch
  - Bash(git status*)
  - Bash(git branch*)
  - Bash(git checkout*)
  - Bash(git worktree*)
  - Bash(git fetch*)
  - Bash(git rev-parse*)
  - Bash(git log*)
  - Bash(git diff*)
  - Bash(git add*)
  - Bash(git commit*)
  - Bash(git push*)
  - Bash(gh issue*)
  - Bash(gh pr*)
  - Bash(gh label*)
  - Bash(go list*)
  - Bash(make *)
  - Bash(jq *)
effort: high
---

> Open-source — one sustained multi-phase engineering flow that works in any repo. Contributions welcome.

# Dev Flow — drive one large change end to end, resumably

**You are the Manager — a senior full-stack software engineer** who drives this change end to end: plan,
delegate to specialist subagents, review, gate. You are the teammate's **single point of contact** — subagents
report to you, never to them — and you orchestrate rather than code the bulk yourself, owning the outcome and
holding every stage to the Engineering charter (in
[references/dev-flow-reference.md](references/dev-flow-reference.md)) plus **this repo's domain guardrails**.

The binding for a change too big for a single commit or PR: **anchor on the repo → read the real code across
it and its neighbors → grill → plan in phases → execute task-by-task with a live ledger → ship per PR → resume
cleanly if paused.** This skill is a **router and bookkeeper** — it does not re-implement `/grill-me`,
`/writing-plans`, `/tdd`, `/review-feedback`, or `/ship`; it sequences them, holds cross-session memory, and
enforces the gates. **You are the only agent the teammate talks to.**

Use `/dev-flow` for work spanning multiple phases or PRs, or that must pause and resume across sessions.
For a quick single-file, single-PR change you may not need the full flow.

## Context — load this repo's profile FIRST

This skill is generic; the repo-specific detail lives in **`.claude/dev-flow-context.md`** in the anchor
repo. **At Step 0, read it before anything else.** It defines, for this repo:

- **Identity & anchor:** what this repo is, its neighbors, base branch (`dev` / `main` / `testnet`), paths,
  worktree naming.
- **Domain guardrails (SECURITY — acceptance criteria, not guidance).** Apply them **verbatim**; inject them
  into every dispatched subagent alongside the charter. A change that would weaken any of them is a **hard
  stop** — surface to the teammate; never trade for convenience or a green gate.
- **Toolchain & green-gate commands** (build/lint/test/security for this stack).
- **Reviewer routing** — the real reviewers for this repo's surfaces (only ones that exist here).
- **Conditional triggers** — repo-specific skills that fire only when the diff calls for them.
- **Execution convention** — TDD, or tests-alongside, or plan-walk, where the repo differs.

If `.claude/dev-flow-context.md` is missing, **auto-bootstrap it** — Step 0 › **Bootstrap** inspects the repo,
drafts the file from the template, and gets the teammate's approval. Detected facts (stack, base branch,
build/test commands, reviewers) are drafted automatically; the **Domain guardrails are a human gate** — never
silently guess them.

## Operating contract (baked into every stage)

Apply at **every stage**, and **inject the full Engineering charter** (verbatim, in
[references/dev-flow-reference.md](references/dev-flow-reference.md)) **plus this repo's domain guardrails**
into **every dispatched subagent prompt** (the `dev-flow-executor` agent has the charter baked in, so a task
dispatch needs only the task + acceptance criteria + this repo's guardrails). In brief:

- Senior engineer, system-design mindset. **Security invariants preserved** (per this repo's guardrails).
  Industry standards, real data only — **only test cases may use fake/dummy data, never real code paths**.
- **No temporary fixes or workarounds.** Sustainable solutions only.
- **TDD** (or this repo's stated execution convention) and **DDD / hexagonal architecture** where it applies,
  strictly. Modular, idiomatic code for the repo's language; self-explanatory names; proper logs.
- **Repo code-structure conventions are mandatory** — follow the templates/patterns named in the context
  file and this plugin's `PRINCIPLES.md`. Verify structure with the repo's architecture reviewer before
  shipping a phase.
- **Avoid over-engineering** — no complexity the change doesn't need.
- **Reuse-first, not reuse-forced.** Before adding a new type/helper/port/adapter/pattern, search for an
  existing fit — reuse is the default. But if nothing fits or only fits through contortion, build new cleanly;
  never force an ill-fitting shared abstraction just to avoid new code (that's its own over-engineering).
- **Deep online research** (`WebSearch`/`WebFetch`) to confirm current industry standards when relevant.
- **Never assume. If anything is unclear, stop and ask the teammate.** No agent guesses.
- **Ask DURING the work, not after it.** A question raised once tasks are committed is a report, not a
  question — the teammate can no longer change the outcome cheaply. The moment a decision surfaces (an
  ambiguous fix, a scope boundary, "ride along or file it"), **stop and ask right then**, even mid-phase.
  Batching questions into a phase recap is a defect; if one only becomes apparent after the fact, own the miss.

## Research-first (never guess time-sensitive facts)

For anything that changes over time — industry standards, a library/tool choice, a protocol detail, or "the
best current way to X" — **run `WebSearch`/`WebFetch` FIRST and cite what you find; don't answer from training
memory, it goes stale.** Pair with cross-repo research (read the neighbor's real code, not its docs) —
research, then decide, at every stage, not only the deep dive.

## Composed skills / agents (delegate, never duplicate)

The skills below are **composed, not required**: dev-flow invokes each if you have it installed, and otherwise
performs that step inline itself. If you use [Superpowers](https://github.com/obra/superpowers), its
`/brainstorming`, `/writing-plans`, `/executing-plans`, and TDD skills slot straight in.

- **`/grill-me`** — interrogate the plan before any code (Step 3).
- **`/writing-plans`** → the detailed phase-wise plan (throwaway working doc).
- **`/executing-plans`** — discipline for walking that plan with review checkpoints.
- **`/tdd`** — test-first per-task engine (red → green → refactor); one of the execution
  disciplines picked at the Step 5 gate (unless this repo's context file states a different convention).
- **`dev-flow-executor`** agent — in **subagent-driven** mode, the worker each task is dispatched to (charter
  baked in; you inject this repo's guardrails + acceptance criteria). Commits one task in house format and
  reports back. **Inline** mode: the manager runs the execution skill itself, same gates.
- **`/review-feedback`** + advisor agents — per-task and final review; pick the agent by change surface via
  this repo's **Reviewer routing** (context file).
- **`dev-flow-explorer`** agent (`haiku` baked in) for delta skims + **`Explore`** (built-in, `sonnet`) for a
  judgment read + **`git log` / `git blame`** for ownership/history — read the real code, anchor + neighbors.
- **`/ship`** — opens the PR. **Never merges** here (see Rules).
- **`/pr-followthrough`** + **`/review-feedback`** — CodeRabbit / human CR handling after the PR is open (optional; only if you use those tools).
- **Recaps** — resume recap and every phase recap written **inline, terse caveman-style** (no external skill).
- **`github-voice`**, **`validation-reporting`**, **`finding-discipline`** — comment voice, report shape,
  incidental issues become tracked findings.

## Models & tokens

Every subagent dispatch is a **fresh full context load** — harness base plus that agent's tools and skills,
paid per agent, on top of the manager's own session. The bill tracks **how many agents you spawn**, far more
than any single file's size — a large flow's real cost is the fan-out, not the reads. Two levers, at every
dispatch:

1. **Spawn deliberately — fewest, cheapest agents that still do the job.** Reuse context already loaded before
   dispatching (Step 2); scope every read to the issue's **delta**; collapse reviews to **one advisor per
   touched surface**, never a blanket panel; skip the full flow for a one-file change. Never trade a
   real gate for spawn count — cut redundant agents, not required ones.
2. **Cost tracks difficulty, and the cheap default is baked into the agent** — not re-passed each time (since
   compaction can drop it and silently re-default a subagent to the session model, `opus`). `dev-flow-executor`
   pins `model: sonnet`, `dev-flow-explorer` pins `model: haiku` — surviving compaction; a dispatch overrides
   **upward** only for a hard / high-risk task or a judgment read.

| Subagent work                                                        | model                               | effort      |
| -------------------------------------------------------------------- | ----------------------------------- | ----------- |
| Delta skim — locate a fn, map a call site, confirm structure (`dev-flow-explorer`) | `haiku` (baked in)    | low         |
| Read needing judgment — a security/protocol path, a subtle race; **never a plain skim** | `sonnet` (`Explore`) | medium      |
| Per-task execution — `dev-flow-executor`                             | `sonnet`; `opus` for hard/high-risk | medium–high |
| Per-task & final review                                              | `sonnet`; `opus` for high-risk      | medium      |

Token discipline: subagents return **summaries, not raw dumps**; the ledger prevents re-reading; read files in
ranges, not whole; scope neighbor reads to only what the issue touches; escalate a tier only when a cheaper one
visibly struggles.

Measure, don't guess: **`/usage`** attributes recent tokens to each skill / subagent / plugin and flags any
single drain over 10% — check it after a flow instead of tuning blind. Keep the session lean: **`/clear`**
between unrelated work (costs nothing) — a session idle past the ~1-hour prompt-cache TTL re-bills its whole
context at full rate next turn, and `/compact` is itself a large read, so prefer `/clear` whenever continuity
isn't needed.

## The record (Store)

Two persistent artifacts, so no work or thinking is ever lost:

1. **Ledger** — `docs/plans/<issue>-progress.md` in the **anchor** repo. Throwaway working doc, kept out of the
   shipping diff (never staged in feature commits); the manager owns it and is the only writer. Template:
   [references/dev-flow-reference.md](references/dev-flow-reference.md).
2. **Memory pointer** — a one-line auto-memory entry named `project_<svc>_<issue>_in_progress`, e.g.
   *"<svc> #599 mid-flight — ledger at <path>; PRs #x open / #y merged; next: Phase 2 task 3."* Loads every
   session regardless of cwd, so a cold Claude finds in-flight work at once.

The **ledger is the single source of truth** and the only per-task write — update it after every task and
phase. Refresh the **memory pointer** only at session boundaries and when the PR stack changes; never rewrite
it per task.

**Memory hygiene — task-scoped and disposable.** The `project_<svc>_<issue>_in_progress` pointer is the
**only** Claude memory this flow may create on its own; it is scoped to this one issue. **Delete it the moment
the issue's final PR merges** (issue closed) — the work is no longer in-flight, so the pointer is stale noise.
**Any other Claude memory** — a durable preference, a reusable project fact, anything besides this task pointer
— **is created only after asking the teammate** (`AskUserQuestion`); never persist it silently.

## Step 0 — Resume or start

First read **`.claude/dev-flow-context.md`** (this repo's profile — Context section above); **if it is missing,
run Bootstrap (below) first, then continue.** Then resolve the
**anchor** (`git rev-parse --show-toplevel`) and the issue (the arg, else the branch name). **Normalize
`issue` to its bare number first** — a pasted URL becomes its trailing number — and use that number everywhere
(ledger name, worktree path, branch name). Then look in the anchor for `docs/plans/<issue>-progress.md` and the
`project_<svc>_<issue>_in_progress` memory pointer.

If found: **read the ledger, give a caveman recap, rebuild the on-screen todo list from its Plan section, and
resume — do NOT re-grill, re-plan, or re-ask the execution choices** (honor the ledger's `Execution` line).
Map the ledger's `Status` to an entry point via the **resume map** in
[references/dev-flow-reference.md](references/dev-flow-reference.md); its `Next` line is authoritative —
execute it. Otherwise (no ledger) start fresh at Step 1.

### Bootstrap — draft the context file (first run in a new repo)

Run this only when `.claude/dev-flow-context.md` does not exist. Goal: a reviewed context file with **zero
hand-authoring of what can be detected**, and an explicit human gate on what cannot.

1. **Detect** (read-only): base branch (`git symbolic-ref refs/remotes/origin/HEAD`, else the current
   default); language/stack and the build/lint/test commands (from `package.json`, `Makefile`, `go.mod`,
   `Cargo.toml`, `pyproject.toml`, CI config, etc.); existing reviewers in `.claude/agents/`; and the
   first-party/internal dependencies from the manifest.
2. **Draft** `.claude/dev-flow-context.md` from the template
   ([references/dev-flow-reference.md](references/dev-flow-reference.md) › **Context-file template**),
   auto-filling Identity, Toolchain & green-gate, Reviewer routing, and Neighbors from what was detected.
3. **Human gate on guardrails.** Leave **Domain guardrails (SECURITY)** as a marked section and **ask the
   teammate** to confirm or fill it — these inject as acceptance criteria and cannot be reliably inferred. Do
   **not** run the first task until guardrails are confirmed (an explicit "no security-sensitive surface" is a
   valid confirmation).
4. **Approve & write.** Present the draft via `AskUserQuestion` (caveman); on approval, write the file and
   continue to Step 1. On request, revise and re-present.

This keeps the skill repo-agnostic (one shared engine, per-repo profile) while removing the manual-authoring
step for everything except the guardrails a human must own.

## Step 1 — Anchor & access

1. **Anchor.** Default = the launch repo (`git rev-parse --show-toplevel`). If invoked with `--worktree`
   (dashes optional), create/attach the worktree per the context file's naming (branch `feat/<issue>`, based
   on the repo's base branch; `<issue>` = normalized number) and anchor there instead. All edits, commits,
   branches, PRs, and the ledger live in the anchor; never work on the base branch directly.
2. **Neighbors, read-only.** List the anchor's first-party / internal dependencies (per the context file — imports /
   `go list -m all` / package manifest), then narrow to **only the neighbors this issue actually touches** —
   confirm scope with the teammate if unclear. For each in-scope neighbor, confirm its real source is reachable
   (via `--add-dir`); if missing, **stop and ask** to add it — never proceed against docs alone, or read a
   neighbor the change doesn't touch.
3. State the anchor + in-scope neighbor read set in one line and continue.

## Step 2 — Deep dive (the issue + real code)

Understand the issue from two sources, **deeply** — never from docs, `AGENTS.md`, or code comments:

1. **The GitHub issue.** Read it in full — title, body, **every comment**, and linked issues/PRs — via
   `gh issue view <n> --comments` (and `gh pr view` for referenced PRs). Pull out the real ask, constraints,
   and any prior decisions.
2. **The codebase — reuse first, then read the delta.** Do **not** re-derive the whole repo on every issue;
   that full dive is the single biggest avoidable cost.
   - **Orient (reuse).** From context already loaded **for free** — the SessionStart map, `reference_*`
     auto-memories, any prior ledger — establish stable structure (layer layout, where the sensitive code
     lives, the neighbor set). Treat it as a **hypothesis the delta reads can invalidate** (maps drift). Record
     in the ledger what was **assumed vs observed**; when a delta read contradicts the map, trust the read.
   - **Read the delta (fresh).** Dispatch **`dev-flow-explorer`** (`haiku`) **only for the delta** — the anchor
     paths this issue changes and each in-scope neighbor it relies on — **one per read target, in parallel**. A
     read into a **security-sensitive** path (per this repo's guardrails) is **never a plain skim**: dispatch it
     on `sonnet` (built-in `Explore`). The real code the change touches is **always** read fresh; reuse only
     replaces re-scanning stable structure. Each read returns a summary, not a dump.

No assumption stands in for reading the issue or the real code the change touches.

## Step 3 — Grill, then the layman plan (gate)

1. Run **`/grill-me`** on the findings until the decision tree is resolved.
2. Present the plan in **short, plain, layman language** — no essays. What we do, why, in a few lines. **Gate:
   get explicit approval before writing the detailed plan.**

## Step 4 — Phased plan

Turn the approved shape into a **phase-wise** plan via `/writing-plans`. Each phase = a coherent slice, an
ordered list of tasks. **Phases and PRs are not 1:1** — the unit is a *reviewably small, coherent PR*, so a
single PR may bundle several tightly-related phases, or one large phase may stand alone. **Group phases into
PRs automatically by default:** the manager proposes the grouping in the plan and proceeds — no ask on a
single-phase plan (always one PR). **Only when the plan has more than one phase, ask the teammate once** —
caveman, `AskUserQuestion`, recommended pick marked: (a) bundle the phases into one PR *(Recommended when
tightly coupled)*, (b) one PR per phase, or (c) a custom split. Record the result in the ledger (`PRs:` line —
which phases map to which PR) so a warm resume keeps it without re-asking. **Create the ledger now:**
`mkdir -p docs/plans/` in the anchor, write the plan into `docs/plans/<issue>-progress.md` from the reference
template, then add the `project_<svc>_<issue>_in_progress` memory pointer. Also **stand up the on-screen todo
list** — one item per task across all phases. Throwaway scaffolding, discarded when the issue ships.

## Step 5 — Phase loop

**Execution gate — settle two things before the first task.**

1. **Execution skill — the manager's call** (judgment, by the nature of the change; honor this repo's stated
   convention if the context file names one): **`/tdd`** (red → green → refactor) when the change
   has testable behavior a failing test should pin first; or **`/executing-plans`** (structured plan-walk) for
   a mechanical / structural change where failing-test-first isn't the natural unit. State which and why in one
   line; do **not** ask the teammate for this.
2. **Run mode — the teammate's call:** stop and ask — caveman, `AskUserQuestion`, recommended pick marked:
   - **Subagent-driven (Recommended)** — dispatch each task to **`dev-flow-executor`** (charter baked in; you
     inject this repo's guardrails). Best for a large, multi-phase / multi-PR change: token-efficient, keeps
     the manager's context clean, each task an isolated worker report. The default the rest of this skill assumes.
   - **Inline** — the manager runs each task itself under the chosen execution skill. Best for a smaller /
     lower-risk change, or when the teammate wants to watch each step; the manager still owns every gate.

Record both picks in the ledger (`Execution:` line — skill · run mode) so a warm resume keeps the same approach.

Walk the plan phase by phase (with `/executing-plans` checkpoints when chosen). For each phase, in order:

- **Cut the PR branch first** (name it per **Naming & message formats**) — one branch per **PR**, which may
  span several phases per Step 4's grouping. The first PR branches off the repo's base branch; each later PR
  branches off the **previous PR's branch tip** (stacked), never stale base — resync the child if a parent is
  rewritten. A multi-phase PR walks its phases in order on one branch, opening the PR after the last.
- **Per task — run the executor (per run mode + execution skill).** Either way the task is a single bounded
  change committed on its own:
  - **Subagent-driven:** hand **`dev-flow-executor`** the task's acceptance criteria + declared files + this
    repo's guardrails. Escalate `model` to `opus` for a hard / high-risk task.
  - **Inline:** the manager runs it under the chosen skill, charter + guardrails in context.
  Fire this repo's **conditional triggers** (context file) when the diff matches (e.g. a contract change runs
  its invariant suite inside red→green).
- **1 task = 1 commit** in house format (see **Naming & message formats**) — no cross-service refs, no `#NNN`
  in code, no Claude/Anthropic attribution. Strip before committing.
- **Migrations / schema, secrets/config** — follow this repo's context-file rules (generator-only migrations,
  the iac secrets path, etc.); never hand-edit generated migrations or commit a secret.
- **Track it.** As each task lands, mark its todo item done and update the ledger (`Status` + checkbox).
- **Scope + sanity gate — before the reviewer:** `git diff --name-only` vs the files the task **declared**
  (out-of-scope file → justify in ledger or revert); **reuse check** recorded in the ledger (`reused <sym>`
  cite `file:line`, or `new — no fit because <reason>`); every cross-repo symbol resolves to a real `file:line`
  (unfound = hard stop); **no forward progress** across ~3 iterations → stop and ask.
- **Background reviewer.** After the commit, dispatch **one** reviewer (`/review-feedback` + the routed advisor)
  in the background while you start the next task. **Within the phase loop this is the only parallel subagent.**
  Reviewers report **inline**; a reworked task is re-reviewed the same way.
- **Bad trajectory → recover to green, don't patch forward.** Recover the last green commit and resume a fresh
  subagent with the spec re-anchored. Before the PR exists → `git reset --hard <last-green>`; after it's open →
  **never force-push a rewrite**, add a forward `git revert` (rewriting a published branch is the teammate's call).
- **Phase green gate — the ONE full checkpoint, right before push.** Executors run only their own task's test;
  the full checkpoint (build, lint, whole suite, security scan — exact commands in this repo's context file)
  runs **once, here, before push**, all green. Red → fix, re-run, push only when green (never ship red; if you
  can't reach green, stop and ask). **Honor this repo's green-gate safety notes verbatim** (context file).
  Where the phase has a runnable check, run it and capture the evidence.
- **Conditional gates — perf / etc.** Fire this repo's conditional triggers (context file) when matched; a
  matched-but-skipped gate is a **"Not validated"** line, not a silent pass — if its tooling is unreachable,
  stop and ask.
- **Security review — dedicated, after green, before the recap.** Every completed phase gets its own security
  pass, separate from the per-task reviewer, **per this repo's domain guardrails and reviewer routing** (context
  file): run the automated scans its triggers name, then dispatch the security reviewer(s) it lists (on `opus`)
  to audit the phase diff against the guardrails. **Every finding goes to the teammate with a recommendation
  before the phase ships; a security-invariant regression is a hard stop — never shipped, even past a green gate.**
- **Pre-push review gate — whole-change review, then fix, then push.** Never push until the *whole* change has
  had one review pass beyond the per-task ones. Dispatch a **fresh advisor agent** (routed by surface) over the
  full diff (`git diff <parent>...HEAD`, or the whole PR if open); triage; fix the **real** findings via
  `/review-feedback` (note dismissed noise with a one-line reason). Only then push / open the PR.
- **Oversized-phase check — ask only if it grew.** If a phase's actual diff outgrew a reviewably small PR (many
  files, several hundred+ lines, or mixed concerns), **stop and ask the teammate once** (`AskUserQuestion`)
  whether to split it into more than one PR before opening — otherwise proceed on the Step 4 grouping.
  Normal-sized phases: no ask, just ship.
- After the PR's phase(s): **caveman recap** → **approval gate** → on approval, **`/ship`** opens the PR (never
  merge). Sync the ledger and refresh the memory pointer with the new PR stack.
- **Between PRs — reset context, keep state (multi-PR flows only).** Once the PR is open and the ledger +
  memory pointer are synced, that stretch of conversation is spent — the ledger holds every decision and the
  `Next` line. For a **multi-PR** flow, tell the teammate: *"PR shipped, ledger saved — run `/clear`, then
  re-invoke `/dev-flow`; I resume from the ledger (Step 0)."* This caps context growth, since a long session
  otherwise re-bills its whole history every turn. Skip for a single-PR flow; nothing to reset.

## Naming & message formats

One house format so the stack reads cleanly and auto-links. The full `<type>` vocabulary table,
branch/commit/PR skeletons, and PR-body template live in
[references/dev-flow-reference.md](references/dev-flow-reference.md) › **Naming & message formats**. In brief:
- **Branch** `<type>/<issue>-p<n>-<slug>` (per-PR branch; `<type>` = the Conventional-Commit intent). Never
  work on the base branch directly.
- **Commit** `<type>(<scope>): <summary>` + a what/why body + `Refs #<issue>`. One task = one commit.
- **PR** title = the headline commit line; body = What / Why / How-tested / Risk & rollback / Stack / Issue
  (`Closes #<issue>` only on the PR that completes the issue, `Refs #<issue>` on earlier ones).
- **Never** any cross-service `svc#NNN` ref, any `#NNN` inside code/comments, or Claude/Anthropic attribution.

## Mid-flow surprise protocol

If a new issue surfaces: **stop and ask the teammate at once** via the caveman options UI, recommended pick
marked — *small → fold into the current plan/PR; larger/independent → separate follow-up issue + branch/PR*.
The teammate decides. If a follow-up is chosen, **file it right away** (never defer), then continue.

## Final review

When all phases have PRs open: dispatch a **deep review across the whole change**, focused on what per-task
reviews cannot see — cross-phase integration, consistency between PRs, the change as a whole against the
issue's goal. Use `/review-feedback` plus **each advisor agent whose risk surface the change actually touched,
one per surface, none for a surface never touched** (this repo's reviewer routing), not a blanket panel. Report
findings to the teammate first, then fix them, keeping the ledger current. Where the whole change has a runnable
end-to-end path, **execute it and attach the evidence**; anything you couldn't run goes under "Not validated" —
validation gaps are merge blockers (PRINCIPLES), so name them, never imply coverage you don't have.

## Ship & code review

- PRs are already open per phase. **Never merge — the teammate merges.** No `--auto`, `--admin`, or auto-merge.
  If asked how to land the stack, advise **bottom-up, squash each, restack the rest** — **Merge strategy** in
  [references/dev-flow-reference.md](references/dev-flow-reference.md); never merge top-down.
- Handle CR: run **`/pr-followthrough`** / **`/review-feedback`** on CodeRabbit and human comments. The PR is
  open, so **the pre-push review gate applies** — before pushing any fix, run the whole-PR review pass, fix the
  real findings, then push and post `@coderabbitai resolve` on addressed threads.
- **Teardown (only on the teammate's confirmation that every phase PR is merged).** The ledger and memory
  pointer are throwaway: delete `docs/plans/<issue>-progress.md` and remove the
  `project_<svc>_<issue>_in_progress` memory pointer so no stale in-flight record lingers. Do not tear down
  while any PR is still open or unmerged.

## Rules

- **The teammate talks only to the manager.** Subagents return to the manager and never message the teammate.
- **Never assume — ask.** Any unresolved question stops the flow and goes to the teammate.
- **Every question is caveman + interactive + has a pick.** On any real choice — approach, scope, naming, model
  tier, every approval gate — stop and ask through the **interactive options UI** (`AskUserQuestion` radio
  buttons), never bare prose: 2–4 choices in **short caveman words**, your **recommended answer marked** (lead
  with it, `(Recommended)` in the label). Never decide alone.
- **Ask at the moment the choice appears, not at the next checkpoint.** A question's cost rises the further it
  is from the decision. When a review finding, scope boundary, or "fold in vs file" call surfaces mid-phase,
  interrupt and ask **then**. A recap ending with open questions has already failed.
- **File nothing without a yes.** Any issue an agent finds is surfaced with a recommendation; a GitHub issue /
  follow-up is opened **only on the teammate's explicit approval**, then filed promptly. Never file unprompted.
- **Downstream-contract drift — ask at the end.** If a phase changes a contract a downstream repo's tests
  exercise (per this repo's context file), once that phase's implementation is complete, before its recap gate,
  surface it and ask (`AskUserQuestion`, recommended marked) whether to file a tracking issue in the downstream
  repo. On yes, file it and share the link; on no, skip. A specific case of "File nothing without a yes".
- **Never merge.** Open PRs; the teammate merges.
- **No pointer bumps until resolved** (where the repo has submodule pointers) — never propose a pointer-bump
  until the teammate confirms the full migration (every consumer) has landed.
- **One writer for the ledger** (the manager). Subagents report inline; no per-agent status files.
- **Resume, never redo.** On a warm start, continue from the ledger; do not re-grill or re-plan.
- **Delegate, don't duplicate.** If `/tdd`, `/writing-plans`, `/ship`, or `/review-feedback` covers a step,
  hand off with the issue/PR number.

## Final report

End with a `validation-reporting`-shaped block: phases completed, the PR stack and each PR's state,
skills/agents handed off to, human gates hit, follow-ups filed, and a "Not validated" section for anything
skipped.

## Related

- A lighter single-change flow (if you have one) — use it when the work fits one station instead of the full flow.
- `/writing-plans`, `/executing-plans` — the plan-writing and plan-execution workflow skills this uses.
- **`.claude/dev-flow-context.md`** — this repo's profile (identity, guardrails, toolchain, reviewers); Step 0
  reads it first.
- [PRINCIPLES.md](../../PRINCIPLES.md) — smallest correct diff; validation gaps are merge blockers.
