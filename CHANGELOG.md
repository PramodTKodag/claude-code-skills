# Changelog

All notable changes to this repo are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); this repo is pre-1.0, so
minor/patch semantics are loose while it's greenfield.

## [Unreleased]

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

[0.1.0]: https://github.com/PramodTKodag/claude-code-skills/releases/tag/v0.1.0
