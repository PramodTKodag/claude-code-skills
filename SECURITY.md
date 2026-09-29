# Security policy

## Reporting a vulnerability

Please **do not open a public issue** for a security problem.

- Preferred: open a private report via **GitHub → Security → "Report a vulnerability"**
  (private vulnerability reporting is enabled on this repo).
- Or email **pramodkodag.dev@gmail.com** with steps to reproduce.

You'll get an acknowledgement as soon as possible. Please allow a reasonable window to fix before any
public disclosure.

## What counts as a vulnerability here

These are **Claude Code skills** — instructions and agents that can run shell commands and read files on
your machine when invoked. Relevant reports include:

- A skill that runs an unexpected, destructive, or data-exfiltrating command.
- A skill that leaks secrets, tokens, or file contents off the machine.
- A prompt-injection path that makes a skill act outside its stated read-only / scoped behavior
  (e.g. `dependency-audit` is read-only — a way to make it write or upgrade would qualify).

## Using skills safely

- **Install skills only from sources you trust, and read them before enabling** — a skill can run tools
  and shell commands.
- Skills here declare their tools in `SKILL.md` frontmatter; review `allowed-tools` before use.
- `dev-flow` never merges PRs or force-pushes on its own; `dependency-audit` never edits files or upgrades
  dependencies. A deviation from those stated contracts is a bug — please report it.
