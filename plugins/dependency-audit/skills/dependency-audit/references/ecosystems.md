# Ecosystem commands

Per-ecosystem detect file, audit command (+ `jq` filter to keep context small), outdated command, and
install hint. Run the audit **once**, pipe through the filter, discard raw output.

## Contents
- [Node — npm / pnpm / yarn](#node--npm--pnpm--yarn)
- [Go](#go)
- [Python](#python)
- [Rust — Cargo](#rust--cargo)

## Node — npm / pnpm / yarn

Detect: `package.json` (+ `pnpm-lock.yaml` → pnpm, `yarn.lock` → yarn, else `package-lock.json` → npm).

Vulnerabilities:
```bash
# npm / pnpm expose the same --json shape:
npm audit --json  | jq '[.vulnerabilities[] | {package: .name, severity, via: (.via), range}]'
pnpm audit --json | jq '[.advisories[]? // (.vulnerabilities[]?)]'   # pnpm v8+ mirrors npm; fall back if empty
# yarn (berry): yarn npm audit --json ; yarn (classic): yarn audit --json
```
Keep only `{package, severity, id/advisory, installed, fixed (patched_versions), path}`.

Outdated:
```bash
npm outdated --json  | jq 'to_entries | map({package: .key, current: .value.current, latest: .value.latest})'
pnpm outdated --format json 2>/dev/null || pnpm outdated
```

Install hints: `npm`/`pnpm`/`yarn` ship with the toolchain; no separate install for `audit`/`outdated`.

## Go

Detect: `go.mod`.

Vulnerabilities (govulncheck reports only *reachable* vulns — note that in the report):
```bash
govulncheck -json ./... | jq -c 'select(.osv != null) | {id: .osv.id, pkg: .osv.affected[0].package.name, summary: .osv.summary}'
# simpler: govulncheck ./...   (human summary) if -json is noisy
```
Outdated:
```bash
go list -u -m -f '{{if .Update}}{{.Path}} {{.Version}} -> {{.Update.Version}}{{end}}' all
```
Install hint: `go install golang.org/x/vuln/cmd/govulncheck@latest`.

## Python

Detect: `requirements.txt`, `pyproject.toml`, or `poetry.lock`/`uv.lock`.

Vulnerabilities:
```bash
pip-audit -f json 2>/dev/null | jq '[.dependencies[]? | select(.vulns|length>0) | {package: .name, version, vulns: [.vulns[].id]}]'
# uv projects: uv pip audit  (or run pip-audit against the resolved env)
```
Outdated:
```bash
pip list --outdated --format json | jq 'map({package: .name, current: .version, latest: .latest_version})'
```
Install hint: `pipx install pip-audit` (or `uv tool install pip-audit`).

## Rust — Cargo

Detect: `Cargo.toml` (+ `Cargo.lock`).

Vulnerabilities:
```bash
cargo audit --json | jq '[.vulnerabilities.list[] | {id: .advisory.id, package: .package.name, version: .package.version, title: .advisory.title}]'
```
Outdated:
```bash
cargo outdated --format json 2>/dev/null | jq '[.dependencies[] | select(.latest != .project) | {package: .name, current: .project, latest: .latest}]'
```
Install hints: `cargo install cargo-audit`, `cargo install cargo-outdated`.
