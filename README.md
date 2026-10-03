# claude-code-skills

[![Release](https://img.shields.io/github/v/release/PramodTKodag/claude-code-skills?sort=semver)](https://github.com/PramodTKodag/claude-code-skills/releases)
[![License](https://img.shields.io/github/license/PramodTKodag/claude-code-skills)](LICENSE)
[![Validate](https://github.com/PramodTKodag/claude-code-skills/actions/workflows/validate.yml/badge.svg)](https://github.com/PramodTKodag/claude-code-skills/actions/workflows/validate.yml)

A personal, open-source collection of [Claude Code](https://code.claude.com) plugins and
skills for real-world software engineering. Install what you want; each plugin is
self-contained.

> These run on **Claude Code** (the SKILL.md / plugin format is Claude Code's). Other AI
> coding tools don't execute them natively. The *methodology* is portable; the packaging is
> not — yet. (`plan-flow` is the exception; see [Using `plan-flow`](#using-plan-flow).)

## Plugins

| Plugin | What it does |
| ------ | ------------ |
| [`dev-flow`](plugins/dev-flow) | Drive one large, multi-phase or multi-PR change end to end — plan → execute task-by-task with a live ledger → ship per PR → resume cleanly across sessions. |
| [`dependency-audit`](plugins/dependency-audit) | Read-only audit of dependencies for known vulnerabilities (CVEs) and outdated packages across npm/pnpm/yarn, Go, Python, and Cargo → prioritized remediation report. |
| [`plan-flow`](plugins/plan-flow) | Everything before implementation — investigate a GitHub issue against the real code, trace cross-repo consumers, audit security, grill open decisions → one self-contained prompt for a separate coding session in any AI tool. |

More will be added over time.

## Install

This repo is a **plugin marketplace**. Add it once, then install the plugins you want.

```bash
# Add this marketplace
claude plugin marketplace add PramodTKodag/claude-code-skills

# Install a plugin
claude plugin install dev-flow@claude-code-skills

# Verify
claude plugin list
```

In an interactive session you can also use the `/plugin` panel, or the slash equivalents
(`/plugin marketplace add …`, `/plugin install …`).

To try a plugin without a marketplace:

```bash
# from a clone of this repo:
claude --plugin-dir ./plugins/dev-flow
```

### Manual install (no plugin system)

Copy the skill and its agents into your personal Claude Code dirs:

```bash
git clone https://github.com/PramodTKodag/claude-code-skills.git
cp -R claude-code-skills/plugins/dev-flow/skills/* ~/.claude/skills/
cp claude-code-skills/plugins/dev-flow/agents/*.md ~/.claude/agents/
```

Copying only the skill folder (without `agents/`) leaves the subagent-driven mode without its
workers — copy both, or use the marketplace/`--plugin-dir` methods above.

## Using `dev-flow`

`dev-flow` is repo-agnostic — the workflow is shared, and each repo keeps its specifics in a
`.claude/dev-flow-context.md` (identity, base branch, security guardrails, toolchain, reviewers).

**First run auto-bootstraps it.** In a repo with no context file, dev-flow inspects the repo, drafts
`.claude/dev-flow-context.md` (stack, base branch, build/test commands, reviewers), and asks you to confirm
the **security guardrails** — the one part it won't guess. Approve it and it continues.

Prefer to write it by hand? Copy
[`plugins/dev-flow/examples/dev-flow-context.example.md`](plugins/dev-flow/examples/dev-flow-context.example.md)
to `.claude/dev-flow-context.md` and fill it in. Either way, then run `/dev-flow <issue-number>` (add
`--worktree` to run in an isolated git worktree).

The security/domain guardrails you write are treated as **acceptance criteria** and injected
into every subagent dev-flow spawns. If your repo already keeps them in `AGENTS.md`, the context
file can point to those sections (`Guardrails: AGENTS.md › <sections>`) instead of copying them.

### How a run flows

- **Risk tiers.** Each issue gets Tier 1 (docs/tests/UI), 2 (business logic), or 3
  (security-critical: auth, keys/crypto, payments, permissions, or paths you list). Tier 3 adds
  an Opus executor, an adversarial plan review, and full re-verification of security facts.
- **One plan gate.** Planning runs in plan mode, so nothing is edited before you approve. With
  the `opusplan` model setting, planning runs on Opus and execution on Sonnet.
- **Ledger, not a live todo list.** Progress lives in `docs/plans/<issue>-progress.md`, which
  survives `/clear` and lets a fresh session resume exactly where the last one stopped.
- **Hand off from an investigation.** After you root-cause something, run `/impl-issue` in that
  session. It files an issue with SHA-pinned verified facts; `/dev-flow <issue>` in a fresh
  session then skips re-reading paths that haven't changed since.

### Second model (optional)

dev-flow can use an independent second model for three roles: a diff review before every push,
an adversarial plan review on Tier 3, and a rescue after two failed attempts. If the
[Codex plugin](https://github.com/openai/codex-plugin-cc) is installed it uses Codex; otherwise
a fresh Claude subagent does the job and the report says it wasn't independent. The second
model never commits, pushes, or merges. To swap in another model, edit the **Second model**
table in `skills/dev-flow/references/dev-flow-reference.md`.

### Composed skills (optional)

`dev-flow` orchestrates steps like planning, execution, TDD, and review. It **invokes a
sub-skill if you have it installed, and otherwise performs that step inline itself** — so it
works with no extra dependencies. If you use [Superpowers](https://github.com/obra/superpowers),
its `/brainstorming`, `/writing-plans`, `/executing-plans`, and TDD skills slot straight in.
`CodeRabbit` / `/pr-followthrough` steps are optional and only fire if you use those tools.

## Using `plan-flow`

`plan-flow` does everything *before* implementation. Give it a GitHub issue and it reads the real
code, traces cross-repo consumers, audits security, challenges the design, grills you on open
decisions, and writes one self-contained prompt that a separate coding session (any AI tool)
executes. It never edits product code.

```text
/plan-flow 123                 # plan issue 123 in the current repo
/plan-flow 123 --worktree      # the prompt directs the coding session into a git worktree
/plan-flow 123 --light         # small issue: run the whole session on a mid-tier model
/plan-flow 123 --greenfield    # no live users or data: plan without compatibility work
```

- **Presets.** `Full` (default) plans on a deep-reasoning model, optionally with cheap subagents for
  reads and research. `--light` runs the whole session on a mid-tier model and escalates (asks you to
  switch) if it finds a security-sensitive path, a contract another repo consumes, or an architecture
  decision.
- **Compatibility.** The default assumes existing consumers and data, so breaking changes get a
  migration or rollout path. `--greenfield` drops that work.
- **Output.** `docs/plans/<issue>-implementation-prompt.md` (never staged), also printed for copying.
  The prompt pins the commit its facts were verified at, tells the coding session to implement
  immediately, keep a slim progress file, review its own diff for security before the PR (on
  security-sensitive issues), and, after validation, file detailed issues in any affected consumer repos.
- **Pairs with `impl-issue`.** An issue carrying `Verified at: <repo>@<sha>` lets `plan-flow` skip
  re-reading paths unchanged since that commit.
- **Context.** Reads `AGENTS.md` / `CLAUDE.md` and, if present, the `.claude/dev-flow-context.md` that
  `dev-flow` writes; otherwise it infers the base branch and test commands and asks you to confirm.

`plan-flow` follows the open Agent Skills layout, so for other tools copy the skill folder where the
tool looks for skills — Codex and Cursor read `~/.agents/skills/`:

```bash
cp -R plugins/plan-flow/skills/plan-flow ~/.agents/skills/
```

## Security & disclaimer

- **Install skills only from sources you trust, and read them before enabling.** A skill can
  run tools and shell commands on your machine.
- `dev-flow` never merges PRs and never force-pushes on its own — it opens PRs and leaves
  merging to you.
- Provided as-is, for general use. Behavior depends on your Claude Code version and the model
  you run it on.

## License

[Apache-2.0](LICENSE) © 2026 Pramod Kodag.
