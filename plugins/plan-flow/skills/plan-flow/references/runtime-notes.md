---
layer: repo
last-reviewed: 2026-10-03
---

# Runtime notes — tiers, modes, subagents per tool

Load only when preflight needs a tool's switch command or model name. Names drift: re-check against the tool's model picker when one looks wrong.

Deep has two equivalent settings per tool: **workhorse at high effort** or **flagship at medium effort**. Use whichever is already active, else the cheaper. Never use the largest tier (for example a Fable model). The Light preset runs the whole session on the Standard column. A missing model falls back to the strongest available at or below its tier.

| Tool | Scout | Standard | Deep (planning) |
|------|-------|----------|-----------------|
| Claude Code | Haiku 4.5, low | Sonnet 5.5, medium | Sonnet 5.5 high, or Opus 5.5 medium |
| Codex | gpt-6-luna | gpt-6.1-sol, medium | gpt-6.1-sol high, or gpt-6-astra medium |
| Cursor | Haiku 4.5 or Cursor's fast model | Sonnet 5.5, medium | Sonnet 5.5 high, or Opus 5.5 medium |
| Other | smallest fast model | mid-size coding model | strongest reasoning model short of the largest |

Provenance (2026-10-03): Codex names read from the Codex model cache (luna = fast and affordable, sol = workhorse, astra = frontier); a fresh Codex session may start below Deep, in which case preflight prints the switch. Claude names from Claude Code's model list. The Cursor rows are planning defaults and the Cursor Scout row is not checked against the picker.

## Switching

- **Claude Code** — mode: plan mode. Model and effort: `/model`. Subagents: pass `model` per dispatch; Scout and Standard reads use the built-in `Explore` agent. Questions: the structured-question tool. Independent review: the Codex plugin when installed, else a fresh Deep subagent labelled "not independent".
- **Codex** — model: `/model`. Plan mode where the build offers it; check the mode picker. Subagents only if the build offers them. No different-vendor reviewer: use a fresh Deep subagent labelled "not independent".
- **Cursor** — mode: Plan mode (`/plan` or `--mode=plan`); it asks clarifying questions natively. Model: the picker. Custom subagents live in `.cursor/agents/*.md` with a `model:` field; that field is [reported ignored in some builds](https://forum.cursor.com/t/subagent-model-choice-not-respected/163645), so confirm the picked model before trusting a Scout dispatch.
- **Any tool** — if it cannot switch model or mode programmatically, print the one-line switch the teammate must make, then wait.
