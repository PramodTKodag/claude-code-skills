---
name: impl-issue
description: Drafts a GitHub issue that hands verified investigation findings to an implementation session, so it can execute without re-investigating. Use when a debugging/investigation session has confirmed root cause and the next step is implementation, or the teammate invokes /impl-issue.
disable-model-invocation: true
argument-hint: "[repo]"
---

# Impl Issue

Turn a completed investigation into an implementation-ready GitHub issue — the fixed template lets `/dev-flow`
skip re-verifying facts this session already confirmed (see its Step 2 pre-verified check).

## When to use

After you've root-caused a bug or confirmed a design decision in the current conversation — not before. If you
haven't actually read the code and verified the root cause yet, investigate first; this skill only packages
findings you already have. Then run `/dev-flow <issue>` in a **fresh** session.

## Process

1. **Resolve repo + commit.** `git rev-parse --show-toplevel` for the repo, `git rev-parse HEAD` for the sha
   the verification was done against. If the working tree is dirty or verification happened against a
   different commit, ask which sha to record — don't guess.
2. **Separate verified from assumed.** For every claim this session actually confirmed by reading code (not
   inferred, not assumed), it goes under **Root cause (verified)** with a `file:function` citation. Anything
   plausible but unread goes under **Assumptions** instead. When in doubt, it's an assumption — a wrong
   "verified" fact is worse than an honest gap, since dev-flow will skip re-checking it.
3. **Fill the template exactly** (below) — every section present, `(none)` where empty, no extra sections.
   Set the **Security** tier per `/dev-flow`'s **Risk tiers** (Tier 3 = security-critical); when unsure, pick
   the higher tier.
4. **Read first list — max 10.** Only paths the implementer actually needs to open, each with a one-line why.
   This list is also what `/dev-flow` diffs against the verified sha to decide what to re-check — keep it tight
   and accurate, not exhaustive.
5. **Strip attribution and cross-repo refs** per house rules below — scan the whole draft, not just the
   sections written from scratch.
6. **Show the draft to the teammate and stop.** Do not run `gh issue create` until they approve or edit it. Filing
   is a confirm-first action, same as any other action visible to others.
7. On approval, file with `gh issue create`; report the URL.

## House rules (non-negotiable)

- **No AI/agent/tool names anywhere in the issue** — no "Claude", "Codex", "agent", skill names, or "verified by
  <tool>". `Verified at:` names the repo and commit, never who or what did the verifying.
- **No cross-repo / cross-service references** — no other-repo names, `svc#NNN` links, or `file:line` citations
  into a different repo. Describe neighbor/external behavior generically (e.g. "rate limit exceeded → 429"),
  per the **Neighbor contract** section.
- **Prose reads like a human engineer wrote it** — no em dashes, emoji, TL;DR, filler praise, or sign-off lines
  anywhere in the issue (use a `github-voice` skill if you have one). Keep the template's sections as-is:
  `/dev-flow` reads them.
- **No destructive framing** — this skill only drafts and, on approval, files an issue; it never edits code,
  closes issues, or touches PRs.

## Template

Fill exactly this structure — copy verbatim, don't rename, reorder, or add sections:

```markdown
## Problem
(2-3 lines)
## Root cause (verified)
Verified at: <repo>@<commit sha>
- <fact> (evidence: <file>:<function>)
## Assumptions (NOT verified, implementer must check)
## Decision
Chosen: … | Rejected: … (why)
## Scope
In: … | Out: …
## Acceptance criteria
- [ ] (testable)
## Security
Tier: 1 / 2 / 3 · Invariants touched: … (or "none")
## Neighbor contract
(external behavior described generically: no other-repo names, links, or file refs)
## Read first (max 10)
- <path>: why
```

## Common mistakes

| Mistake | Fix |
|---|---|
| Marking something "verified" because it's plausible | If you didn't read it this session, it's an Assumption |
| Filing straight after drafting | Always show the draft and wait for explicit approval first |
| Citing another repo's file:line for neighbor behavior | Rewrite generically — behavior only, no repo/file names |
| Listing every file the change might touch under "Read first" | Cap at 10 — only what the implementer must open |
| Leaving "Verified by Claude" or similar in the body | Strip all AI/tool/agent names before showing the draft |

## Related

- **`/dev-flow`** Step 2 trusts this template's `Verified at` + `Read first` fields to skip re-deep-diving
  unchanged paths — Tier 3 always re-verifies regardless.
