# Planning guidance

Contents: Evidence · Ownership and security · Compatibility · Security review · Governing decisions · Grilling · Sizing · Conditional checks · Branches

Keep working facts short; do not write another plan document.

## Evidence

- Read actual behavior, callers, tests and the exact build and CI targets. Record each repo SHA, relevant dirty paths and verified `file:line`; mark assumptions. The issue is a hypothesis; source is truth, not docs, comments or earlier summaries.
- If the issue body has `Verified at: <repo>@<sha>` and a `Read first` list, fetch, diff those paths against base and trust unchanged ones. Re-verify every security-invariant fact regardless.
- Resolve consumed dependency revisions and overrides before treating a sibling checkout as provider truth.
- Use bounded searches and ranges; widen until the relevant behavior is covered. Never truncate away a governing rule to save reads.
- Confirm the commands test the intended checkout: some stacks false-green when a worktree is tested with main-checkout targets (container mounts, build contexts, services). Do not invent a worktree convention or bypass the repo's admission rules.
- Before changing an interface another repo consumes (HTTP contract, FFI, schema), read the provider-side implementation.
- Search online only for time-sensitive or uncertain facts (versions, standards, APIs); use primary sources and cite them.

## Ownership and security

- Put the fix in the component that owns it, never as a downstream workaround. If another repo owns a needed fix, record a dependency or follow-up and ask about a separately authorized issue; never plan a second implementation workspace.
- Consumers come from the profile's downstream list and from what the code shows, each labelled verified or unverified; no list proves exhaustive coverage.
- Challenge the plan: does it hit the root cause? Is there a simpler design, a better boundary, existing infrastructure, an unlisted edge case? Compare alternatives on security, correctness, maintainability and complexity, and recommend one.
- Audit touched authn/authz, ownership, signing, keys, replay, payments, inputs, trust boundaries and logging. Give issue-specific requirements stable IDs (`S1`, `S2`) with the objectives they constrain. Standing invariants stay as a binding pointer to the repo's security guidance.
- Never weaken a control; a change that does is a stop, ask. Never put secrets, key material or exploit detail in a public artifact.
- A known external dependency leaves the plan ready; the affected file opens with a `wait` (on / check / resume) in the spec.

## Compatibility

- `existing` (default): existing consumers and data are assumed. Every breaking change to an API, type, schema or behavior gets a migration or rollout path and a decision entry.
- `greenfield` (`--greenfield`): no live users, consumers or stored data to preserve, so plan no shims, legacy paths, dual support or old-data migrations in product code, and change earlier decisions (the issue's premise, an existing API) when a better design is warranted, after asking. Greenfield never authorizes overriding an accepted decision, weakening a control or redeploying immutable state; flag already-deployed immutable state (contracts, shared dev or test data) as a cost.
- Both modes keep the smallest correct diff.

## Security review

Required for sensitive work: auth, keys or crypto, payments, permissions, trust boundaries, any security-control row, or the paths the profile lists as sensitive.

- Fresh context, never the planning thread. Give the reviewer the issue, the source paths and the S list, not your conclusion.
- Prefer a domain reviewer agent when the host has one for the area. A different-vendor model is best when offered; a separate instance of the same model counts as an independent-context review, not a different-vendor one; say which.
- Only P0/P1 findings with `file:line` count. Resolve each, or ask on real disagreement. Put reviewer, scope and resolved findings into `security.review`.
- Reviewer unavailable: the plan is blocked; report the required route. Never downgrade silently.

## Governing decisions

Planning reads one register: the anchor repo's own `decisions/` folder. Decisions kept in other repos or folders are out of scope.

- Run the lookup once, with 5-12 behavior terms and touched paths (your own words, never pasted issue text) on stdin:

  ```sh
  python3 <skill-dir>/scripts/decisions_lookup.py <<'TERMS'
  <terms>
  TERMS
  ```

  It fetches first, then reads `decisions/` from the repo's default branch (the working tree when there is no origin ref). No flag or profile setting adds another folder. Decisions are added, changed and removed often: never reuse an earlier run, a remembered ID or a cached list. Rerun if the behavior terms change. If a coverage line says `fetch failed`, the host may be blocking writes to `.git` (a sandbox): ask for approval to run the fetch outside it and rerun; if not granted, state under `assumptions` that the decisions may be stale.
- Also read every ADR ID and binding document named by AGENTS.md, CLAUDE.md, the issue or the affected code, even if the lookup missed it. Matching is lexical on titles and summaries, so a miss proves nothing; ranking only orders reading.
- Read Status and Decision of each hit that could constrain the design; no whole-folder dumps. Accepted binds. Proposed or Unrecognized is unsettled: ask if the design depends on it. Superseded, Deprecated and Rejected do not bind; follow Superseded to its replacement.
- A contradiction with an accepted decision needs the owning decision process: stop and ask. Planning never edits an ADR or invents policy.
- Record each binding ID, section and rule under decisions. Put the lookup's coverage lines (ref and SHA read, README mismatches, gaps) under `assumptions`. If the repo has no `decisions/` folder, state that gap. Never write "no decision found" as proof of absence; state the coverage limit.

## Grilling

Every plan settles its open design choices with the user before Settle; Full depth grills deeper.

- **All depths:** ask each material choice the code, issue, comments and decisions cannot settle, one at a time, through the interactive tool (see Questions): 2-4 concrete options, recommended first with its reason. Never ask what the issue states, what the code shows, or what an earlier answer settled.
- **Full depth adds:**
  - List the design branches first: behavior, ownership, contract, data and state, failure and abuse cases, security controls, rollout or compatibility, PR grouping. Take them parents before children, so each answer decides the next question.
  - Challenge, do not transcribe. Test the issue's hypothesis and every answer against the evidence: name a contradiction with an accepted decision or `file:line`, and the edge cases the answer leaves open (failure, concurrency, replay, rollback, abuse). Push back once, with evidence, on a weak answer; after that the user's choice stands and is never reopened.
  - Stop when no open decision remains: each resolved, or deferred as a labelled assumption with its reason. Restate the settled decisions in a few lines and have the user confirm or correct them before sizing.
- Each answer enters the plan check's decision list with its why and rejected alternative.

## Sizing

One objective = one coding session: a coherent behavior change, its focused tests, a commit, a stop. Split at meaningful behavior and test boundaries, not by directory, file count or criterion count. A shared goal or policy does not merge distinct flows into one objective.

- **Compact** (`layout: compact`, exactly one objective): one bounded change, limited context, straightforward test and review, completed in one focused session. Sensitivity alone does not force phases; required reviews still apply.
- **Phased** (`layout: phased`): several substantial flows, a broad test matrix, high complexity, or likely multiple sessions. One file per objective plus gates and ship. Also use it for a substantial indivisible single objective.
- Objectives may depend on earlier ones on the same branch ("testable" means after prerequisites). Fold trivial helpers and their tests into the objective they serve; no session per layer or test file.
- "One objective" or "one PR" alone never proves compact. Many changed files is a prompt to reassess, not a threshold. Put a concrete one-line reason in `layout_reason`.
- PR grouping is separate and settled once. One objective is one PR with no question. With two or more, ask once, recommended first by coupling and size: one PR (tightly coupled or small together), one PR per objective (each stands alone), or a custom split. Coupled changes that must land together stay in one PR with full cross-flow checks before publication.
- Several PRs form a stack, decided here and never at execution. Order top-down from the end goal: foundations at the bottom, dependents above, so code never depends on a higher PR. Build bottom-up: objectives run in order, each stacked branch is cut from the local tip of the one below, and nothing is pushed until ship. Merge bottom-up, by the user. Independent PRs that do not depend on each other target the base branch directly instead of stacking.
- Each objective names confirmed files or APIs, named tests, a first action, one focused command, prerequisites and any wait check. Tests follow the repo convention; do not impose TDD.

Example: a freeze policy across account recovery, key rotation and device management is three ordered objectives, a combined security and race gate, one PR. A localized correction with one test path is compact.

## Conditional checks

Map each conditional check in the repo guidance or CI config to a path trigger and put it in `gates.conditional` (for example a secret scan when HTTP, DTO or logging code changes; an end-to-end suite when signing code changes; consumer checks when an exported API changes). The renderer cannot infer these; a missed one is a plan defect.

## Branches

Branch names follow the repo grammar from AGENTS.md, CLAUDE.md or the profile; without one, `<type>/<issue>-<slug>`. The base branch comes from preflight and the repo guidance; `pr_rows[].base` and the `base` field agree with it. A stacked row's `base` is the branch of the row below it; the top row carries `Closes`.
