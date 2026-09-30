# dev-flow context — <your-service>

> Copy this file to `.claude/dev-flow-context.md` in the repo you want to drive with
> `/dev-flow`, then fill in the real values. dev-flow reads it FIRST (Step 0) and injects
> the Domain guardrails into every subagent. Keep it lean — it loads fully on every run.

## Identity

- **What it is:** one paragraph — what this repo is, its role, its language/stack.
- **Base branch:** `main` (or `dev` / `develop` / `trunk`). Never work on it directly.
- **Neighbors (read-only during the flow):** first-party/internal deps this repo relies on,
  and how to list them (imports / `go list -m all` / `package.json` / lockfile). Give the
  local path to each so dev-flow can read the real code, not docs.
- **Worktree naming:** `../<service>-worktrees/<service>-<issue>` (used with `--worktree`).
- **Execution convention:** `TDD` (default) | `tests-alongside` | `plan-walk`. Only state it
  if it differs from TDD.

## Domain guardrails (SECURITY — acceptance criteria, applied verbatim)

Guardrails: AGENTS.md › Security Rules, Domain Invariants

> Pointer form (above): dev-flow reads the named `AGENTS.md` sections fresh on every run, so
> the rules live in one place. Delete the pointer line to use the inline form instead and
> list the rules below.

### Extra locks (not in AGENTS.md)

- Rules only this file holds — or, in inline form, this repo's hard rules: authn/authz, key
  material, data handling, protocol/on-chain invariants, public-API compatibility, whatever
  must never regress.
- A change that would weaken any of these is a **HARD STOP** — surface it to the human;
  never trade it for a green gate.
- If the repo has no security-sensitive surface, say so explicitly so nothing is assumed.

## Tier 3 paths

- Paths whose changes are always Tier 3 (security-critical), e.g. `internal/auth/`,
  `internal/crypto/`, `billing/`. Write "none" if nothing qualifies.

## Toolchain & green-gate commands

- The build / lint / test / type-check / security-scan commands for this stack.
- The ONE full-checkpoint sequence the manager runs once before push (all must be green).
- Any safety notes (e.g. a shared dev stack that must not be restarted; a worktree that
  false-greens under the wrong command).

## Reviewer routing (only reviewers that exist for THIS repo)

| Change surface | Reviewer |
| -------------- | -------- |
| <e.g. auth / data / migrations> | <agent or `/review-feedback` with a focus> |
| general correctness | `/review-feedback` + built-in `Explore` |

## Conditional triggers (fire only when the diff matches)

| Diff touches… | Fire | Where |
| ------------- | ---- | ----- |
| <e.g. a DB migration> | <the repo's migration check> | pre-push gate |

## Downstream-contract drift

- Which downstream repo's tests this repo's contracts feed (or "none"). dev-flow asks before
  filing any tracking issue in another repo.
