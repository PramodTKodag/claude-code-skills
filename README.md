# claude-code-skills

A personal, open-source collection of [Claude Code](https://code.claude.com) plugins and
skills for real-world software engineering. Install what you want; each plugin is
self-contained.

> These run on **Claude Code** (the SKILL.md / plugin format is Claude Code's). Other AI
> coding tools don't execute them natively. The *methodology* is portable; the packaging is
> not — yet.

## Plugins

| Plugin | What it does |
| ------ | ------------ |
| [`dev-flow`](plugins/dev-flow) | Drive one large, multi-phase or multi-PR change end to end — plan → execute task-by-task with a live ledger → ship per PR → resume cleanly across sessions. |

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

## Using `dev-flow`

`dev-flow` is repo-agnostic. To use it in a project, add a **per-repo context file** that
tells it the repo's identity, base branch, security guardrails, toolchain, and reviewers:

1. Copy [`plugins/dev-flow/examples/dev-flow-context.example.md`](plugins/dev-flow/examples/dev-flow-context.example.md)
   to `.claude/dev-flow-context.md` in your repo.
2. Fill in the real values (keep it lean — it loads on every run).
3. Run `/dev-flow <issue-number>` (add `--worktree` to run in an isolated git worktree).

The security/domain guardrails you write are treated as **acceptance criteria** and injected
into every subagent dev-flow spawns.

### Composed skills (optional)

`dev-flow` orchestrates steps like planning, execution, TDD, and review. It **invokes a
sub-skill if you have it installed, and otherwise performs that step inline itself** — so it
works with no extra dependencies. If you use [Superpowers](https://github.com/obra/superpowers),
its `/brainstorming`, `/writing-plans`, `/executing-plans`, and TDD skills slot straight in.
`CodeRabbit` / `/pr-followthrough` steps are optional and only fire if you use those tools.

## Security & disclaimer

- **Install skills only from sources you trust, and read them before enabling.** A skill can
  run tools and shell commands on your machine.
- `dev-flow` never merges PRs and never force-pushes on its own — it opens PRs and leaves
  merging to you.
- Provided as-is, for general use. Behavior depends on your Claude Code version and the model
  you run it on.

## License

[Apache-2.0](LICENSE) © 2026 Pramod Kodag.
