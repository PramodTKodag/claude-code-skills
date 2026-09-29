---
name: dependency-audit
description: >-
  Audit a project's dependencies for known vulnerabilities (CVEs) and outdated packages across
  npm/pnpm/yarn, Go, Python, and Cargo, then produce a prioritized, read-only remediation report.
  Use when the teammate asks to audit or check dependencies, scan for vulnerable or outdated
  packages, run a supply-chain / dependency security check, or mentions npm audit, govulncheck,
  pip-audit, or cargo audit. Read-only — it never edits files or upgrades anything.
user-invocable: true
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(npm audit*)
  - Bash(npm outdated*)
  - Bash(pnpm audit*)
  - Bash(pnpm outdated*)
  - Bash(yarn audit*)
  - Bash(yarn outdated*)
  - Bash(govulncheck*)
  - Bash(go list*)
  - Bash(pip-audit*)
  - Bash(pip list*)
  - Bash(uv*)
  - Bash(cargo audit*)
  - Bash(cargo outdated*)
  - Bash(jq*)
effort: medium
---

# Dependency audit

Scan the dependency graph for **known vulnerabilities** and **outdated packages**, then hand back one
prioritized report. **Read-only**: run audit tools, never modify manifests, lockfiles, or code — the
teammate (or `/dev-flow`) applies fixes.

## Procedure

1. **Detect ecosystems.** Glob for manifests — `package.json`, `pnpm-lock.yaml`/`yarn.lock`, `go.mod`,
   `requirements.txt`/`pyproject.toml`, `Cargo.toml`. Report which were found; audit only those.
2. **Run each ecosystem's native tools once** — the exact audit + outdated commands, their `jq`
   extraction filters, and install hints are in
   [references/ecosystems.md](references/ecosystems.md). Prefer the tool the lockfile implies
   (`pnpm` over `npm` when `pnpm-lock.yaml` exists, etc.).
3. **Missing tool = "not run", never a silent pass.** If an audit tool isn't installed, list it under
   *Tools not run* with the one-line install from the reference; do not infer results from the manifest.
4. **Synthesize** the outputs into the report below. Then stop — propose, don't apply.

## Token discipline (required)

- **Never** paste raw `audit`/`outdated` JSON into the conversation. Always pipe it through the `jq`
  filter in the reference to keep only `{package, severity, id, installed, fixed, path}`, then work from
  that.
- Run each tool **once**; capture the filtered summary and discard the raw output.
- Read manifests with `grep`/targeted reads, never whole large lockfiles.
- Load `references/ecosystems.md` only when you need a command you don't already have.

## Output

Report, most severe first:

- **Summary:** `N vulnerabilities (c critical / h high / m moderate / l low), M outdated` across the
  ecosystems scanned.
- **Vulnerabilities** — table: `severity · package · installed → fixed · advisory/CVE · dependency path`.
- **Outdated** — table: `package · current → latest · jump (patch / minor / major)`.
- **Prioritized remediation:**
  1. **Safe now** — patch/minor upgrades that fix a vuln or are low-risk, each with the **exact command**.
  2. **Needs review** — major/breaking upgrades, flagged separately with why (API break, transitive pin).
- **Tools not run** — any ecosystem whose audit tool was missing, with the install hint.

State clearly that nothing was changed. If the teammate wants the fixes applied, recommend running them
through `/dev-flow` (or manually) — this skill does not upgrade.

## Guardrails

- Read-only: no `Edit`/`Write`, no `npm install`/upgrade, no lockfile changes.
- Report severities and versions **as the tools report them** — do not guess CVE IDs or fixed versions.
- If a scanned ecosystem has zero findings, say so explicitly rather than omitting it.
