# Contributing / working notes

Maintained solo — these are notes to self (and anyone who forks) for adding and testing skills.
This repo is a **Claude Code plugin marketplace**: a collection of plugins, each bundling one or
more skills (and optionally agents/commands).

## Repo layout

```
.claude-plugin/marketplace.json   # the catalog — one entry per plugin
plugins/<plugin>/
  .claude-plugin/plugin.json       # plugin manifest (name, version, license, keywords)
  skills/<skill>/SKILL.md          # the skill (+ references/ loaded on demand)
  agents/*.md                      # optional subagents
  examples/                        # optional sample inputs/config
```

## Adding a new skill or plugin

1. Create `plugins/<your-plugin>/` with a `.claude-plugin/plugin.json` and at least one
   `skills/<skill>/SKILL.md`.
2. Add one entry to `.claude-plugin/marketplace.json` (`name`, `source`, `description`).
   The entry `name` **must match** the plugin's own `plugin.json` `name`.
3. Validate: `claude plugin validate ./plugins/<your-plugin>` (add `--strict` in CI).

## Developing & testing locally

```bash
# Load a plugin without a marketplace:
claude --plugin-dir ./plugins/<your-plugin>

# Or add this repo as a local marketplace and install:
claude plugin marketplace add .
claude plugin install <plugin>@claude-code-skills
```

Edits to a loaded skill hot-reload in-session, so iterate with a fresh Claude and a real task.

## SKILL.md conventions (per Anthropic best practices)

- Frontmatter: `name` (lowercase-hyphen, no "claude"/"anthropic", ≤64 chars) and a
  trigger-dense, **third-person** `description` (what it does **and** when to use it).
- Keep the SKILL.md body lean (**< 500 lines**); push detail into `references/*.md`, one level
  deep, with a table of contents on any file over ~100 lines.
- Prefer one clear default over listing many options; no time-sensitive claims in the body.

## Commit & PR

- Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:` …), imperative, concise.
- One logical change per PR; fill in the PR template.
- Everything in this repo is licensed under Apache-2.0.
