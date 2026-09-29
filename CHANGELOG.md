# Changelog

All notable changes to this repo are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); this repo is pre-1.0, so
minor/patch semantics are loose while it's greenfield.

## [Unreleased]

### Added
- **dependency-audit** plugin — read-only audit of dependencies for known vulnerabilities (CVEs) and
  outdated packages across npm/pnpm/yarn, Go, Python, and Cargo, producing a prioritized remediation
  report. Tool-driven (native audit tools) and token-conscious (summarizes tool output via `jq`, never
  dumps raw JSON).

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
