# Changelog

All notable changes to this repo are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); this repo is pre-1.0, so
minor/patch semantics are loose while it's greenfield.

## [Unreleased]

### Added
- **plan-flow 0.3.0 — PR split.** With two or more objectives the planner asks once: one PR, one PR per
  objective, or a custom split, and records it under Decided. More than one PR adds a PR plan to the
  prompt: one row per PR in merge order, each stacked on the previous PR's branch. The coding session
  checks each diff before opening its PR and asks before splitting further.
- **plan-flow 0.3.0 — after-merge cleanup.** The prompt tells the coding session to delete the prompt file
  and the progress file once every PR it opened for the issue is merged and you confirm. If any PR is
  still open it keeps both files and says which.
- **plan-flow 0.3.0 — execution slices.** Besides the canonical prompt, the skill writes one
  `<issue>-exec-obj-<n>.md` per objective, `<issue>-exec-gates.md` (validation only) and
  `<issue>-exec-ship.md` (decision record, side findings, push, PRs linked to the issue, cross-service
  issues). The teammate pastes each into a new coding session in order, so no session carries the whole
  issue or a long thread. Each objective slice keeps the facts, decisions and security requirements its
  objective touches, one focused test command and the three mandatory stops, then commits and stops.
  A canonical objective blocked on an external release or issue carries `waits on:` with a check
  command, and its slice opens with a STOP line. Each objective slice reads the progress file and the
  branch log first and follows earlier decisions; each objective must be testable on its own. With
  stacked PRs, the final message says to merge in order and retarget each later PR to the base branch
  before merging, since `Closes` fires only on a merge into the default branch. Slices read only the
  cited line ranges and run tests and gates without verbose output. The workflow has you run the gate
  commands yourself and paste the gates slice only on a failure or for a security-sensitive issue, and
  a change too small for its own session folds into the objective it supports.
  The canonical prompt stays complete for tools that run the whole issue in one session, and its Run rule
  governs only such a run. Slices copy the issue's own security requirements verbatim and cite standing
  invariants by pointer instead of pasting their tables.
- **plan-flow 0.3.0 — handoff output.** Every handoff prints a how-to-run block, objective 1's slice in a
  fenced block and the file paths. `--exec-print <n|gates|ship|all>` picks the slice to print;
  `--no-prompt` prints the how-to-run block and paths only.
- **plan-flow 0.3.0 — single-repo scope rule.** The planner writes objectives and a workspace for the
  anchor repo only, and the prompt tells the coding session to change nothing in any other repository or
  checkout: when an objective needs a change elsewhere it asks, files an issue once agreed, and edits
  nothing there.
- **plan-flow 0.3.0 — new decisions and side findings.** The generated prompt tells the coding session
  to comment on the issue for every decision the prompt did not settle, and to hold side findings
  (defects found outside the objectives) until one batched question before the PR: file an issue for
  another repo or this one, or fold a same-repo finding into the PR. Security vulnerabilities are
  reported immediately. Both land in the slim progress file.
- **plan-flow 0.3.0 — start comment.** Before objective 1 the coding session posts one comment on the
  issue with the root cause, target design, every settled decision (with why and the rejected option) and
  the compatibility mode, so the issue holds the decision record even if the local prompt file is lost.
- **plan-flow 0.3.0 — lean prompt.** The template and self-check now require deleting every
  not-applicable section and leftover hint and listing under Verified only the facts an objective or
  security requirement depends on, since the coding session carries the prompt in context for the
  whole run.
- **plan-flow 0.3.0 — hard rule.** The prompt opens with an explicit rule against any AI tool,
  assistant or model mention in code, commits (including co-author trailers), issues, PRs and their
  comments.

### Changed
- **dev-flow 0.3.0 — plan gate.** The plan is explained once, as a caveman summary printed in chat right
  before `ExitPlanMode`: what we fix, how it helps users and the team, what pain stays if skipped, what
  changes, phases to PRs, tier, out of scope, hard stops. No plan narration after earlier steps. The
  run-mode question moves ahead of the gate, so approving the plan starts execution with no further ask.
  Security and Tier 3 risks stay in full prose.
- **plan-flow 0.3.0 — issue-linked PRs.** Every PR the coding session opens links the issue: `Closes`
  on the PR that completes it (the only PR, or the last PR plan row), `Refs` on every other PR, and
  `Refs` plus the open criterion when a PR leaves an acceptance criterion unmet. PR plan rows carry the
  keyword, and the self-check and Definition of done confirm it.
- **plan-flow 0.3.0 — run rule.** The prompt tells the coding session to carry the work through to the
  Definition of done in one run: commit each objective, push, open each PR in order and start the next
  objective without asking or stopping to report progress. It pauses only for a Quick check stop, a
  change needed in another repo, an oversized PR, or side findings to decide before a PR, and that
  question is asked only when the list has items. A security vulnerability is reported as soon as it is
  found and work continues; it stops the run only when it sits in code the objectives change or makes an
  objective unsafe to ship.
- **plan-flow 0.3.0 — token cuts.** Code readers run one per repo, covering all of its targets, instead
  of one per file, since every spawn loads a fresh base context; security-sensitive paths keep their own
  Standard reader and every target is still read. Step 1 reuses root instructions the tool already
  loaded, follows only the routing the issue needs, and skips on-demand references. The prompt states
  each fact once and cites `file:line` elsewhere, aims for about 4.5k tokens without cutting any fact an
  objective, test or security requirement needs, and its fixed rule blocks keep every rule in fewer
  words. Security requirements, the security plan review and the separate self-check are unchanged.
- **plan-flow 0.3.0 — progress file name.** The coding session's progress file is now
  `docs/plans/<issue>-plan-progress.md`, so it no longer shares a path with the `dev-flow` ledger
  (`docs/plans/<issue>-progress.md`).

## [0.4.0] - 2026-10-03

### Changed
- **plan-flow 0.2.0 — pinned facts.** The generated prompt now pins the commit each repo was read at
  (`Verified at: <repo>@<sha>`). The coding session diffs the paths it will touch against that commit,
  trusts unchanged facts, and re-reads only what changed plus every security-control fact.
- **plan-flow 0.2.0 — pre-PR security review.** For security-sensitive issues the prompt tells the
  coding session to re-read its full diff as a security reviewer before opening the PR, and to report
  what it checked.

## [0.3.0] - 2026-10-03

### Added
- **plan-flow 0.1.0** plugin — investigates a GitHub issue against the real code (cross-repo trace,
  security audit, design challenge, batched grilling with recommended answers) and writes a
  self-contained implementation prompt for a separate coding session in any AI tool. Flags:
  `--worktree`, `--light` (mid-tier session with an escalate rule), `--greenfield` (drops
  compatibility work; off by default). The prompt tells the coding session to implement immediately,
  keep a slim progress file, and file issues in affected consumer repos after validation.

## [0.2.0] - 2026-10-02

### Added
- **dev-flow 0.2.0 — risk tiers.** Every issue is Tier 1, 2, or 3 (recorded in the ledger). Tier 3
  (security-critical, or a path listed under the context file's **Tier 3 paths**) runs the executor
  and security reviewers on Opus, adds an adversarial plan review, and always re-verifies security facts.
- **dev-flow 0.2.0 — second model (swappable).** Three roles bound by a single table: `diff-review`
  on every PR, `plan-review` on Tier 3, `rescue` after two failed attempts. Uses the Codex plugin when
  installed, else a fresh Claude subagent (reported as "not independent"). Advisory, P0/P1 only; never
  commits, pushes, or merges.
- **impl-issue** skill (bundled with dev-flow) — turns a finished investigation into an issue with
  SHA-pinned verified facts; dev-flow's Step 2 then skips re-reading `Read first` paths unchanged
  since that SHA (never for Tier 3 security facts).
- **dev-flow 0.2.0 — AGENTS.md guardrails.** The context file can point to `AGENTS.md` sections
  (`Guardrails: AGENTS.md › …`) plus its own **Extra locks**; bootstrap proposes the pointer when
  those sections exist. The inline guardrails block still works.
- **dependency-audit** plugin — read-only audit of dependencies for known vulnerabilities (CVEs) and
  outdated packages across npm/pnpm/yarn, Go, Python, and Cargo, producing a prioritized remediation
  report. Tool-driven (native audit tools) and token-conscious (summarizes tool output via `jq`, never
  dumps raw JSON).

### Changed
- **dev-flow:** opens each PR itself (`git push` + `gh pr create`) instead of handing off to a `/ship`
  skill. Before opening, a PR gate asks whether to open a ready PR, a draft PR, or hold (ledger goes to
  `awaiting-approval`). Stacked PRs target the parent PR's branch. Still never merges.
- **dev-flow:** Steps 3–4 run inside plan mode with a single approval gate at the end of Step 4
  (Opus planning with the `opusplan` model setting); the ledger is written after approval.
- **dev-flow:** green gate runs each task's own tests per task and the full gate once before push;
  never bypasses git hooks; CI stays the final gate.
- **dev-flow:** the final report lists which second-model roles ran and any fallback used.

### Removed
- **dev-flow:** the on-screen todo list. Recent Claude Code versions no longer offer the task
  tools on current models; the ledger is the progress record.

## [0.1.0]

First public release of the `claude-code-skills` marketplace.

### Added
- **dev-flow** plugin — drive one large, multi-phase / multi-PR change end to end: plan →
  execute task-by-task with a live ledger → ship per PR → resume cleanly across sessions.
  Repo-agnostic, driven by a per-repo `.claude/dev-flow-context.md`.
- **Auto-bootstrap** — on the first run in a repo with no context file, dev-flow detects the
  stack / base branch / build+test commands / reviewers, drafts the context file, and gates on
  human-confirmed security guardrails before running.
- `dev-flow-executor` and `dev-flow-explorer` agents bundled with the plugin.
- CONTRIBUTING notes, issue/PR templates, and a manual-install path in the README.

[Unreleased]: https://github.com/PramodTKodag/claude-code-skills/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/PramodTKodag/claude-code-skills/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/PramodTKodag/claude-code-skills/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/PramodTKodag/claude-code-skills/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/PramodTKodag/claude-code-skills/releases/tag/v0.1.0
