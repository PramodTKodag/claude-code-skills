# Engineering principles

The baseline dev-flow holds every stage to. Short on purpose — the repo-specific
detail lives in each repo's `.claude/dev-flow-context.md`.

- **Smallest correct diff.** Do the real end-state fix, but no more than the change
  needs. No speculative abstraction, no unrelated refactoring riding along.
- **No workarounds.** Sustainable root-cause solutions only — no shims, aliases,
  temporary bypasses, or TODO-hacks.
- **Reuse-first, not reuse-forced.** Search for an existing fit before adding a new
  type/helper/pattern; build new cleanly when nothing fits rather than contorting the
  change into an ill-fitting abstraction.
- **Security invariants are acceptance criteria, not guidance.** A change that weakens
  a repo's stated guardrail (per its context file) is a hard stop — surface it, never
  trade it for a green gate.
- **Real data only.** Only test code may use fake/dummy data, never a real code path.
- **Validation gaps are merge blockers.** If you could not run something, say so under
  "Not validated" — never imply coverage you don't have.
- **Never assume — ask.** Any real ambiguity stops the work and goes to the human,
  during the work, not after it.
- **Modular, idiomatic code** for the repo's language; self-explanatory names; proper
  logs; follow the repo's existing conventions.
