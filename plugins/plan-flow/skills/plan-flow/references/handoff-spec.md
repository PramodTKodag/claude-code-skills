# Handoff spec

Contents: Fields · Rules · Decision comment · Output · Examples

One JSON object on stdin to `render_handoff.py`. Every fact appears once; the renderer copies it to the files that need it. All text fields are single lines. The renderer rejects anything missing or malformed with a field-named error.

## Fields

| Field | Type | Notes |
|---|---|---|
| `issue` | string | full `https://github.com/<org>/<repo>/issues/<n>` |
| `title` | string | handoff title |
| `base` | string | `<branch>@<sha>`, 7-40 hex, from `git rev-parse` |
| `planned` | string? | `YYYY-MM-DD`; defaults to today |
| `compatibility` | `existing` / `greenfield` | existing unless `--greenfield` |
| `layout` | `compact` / `phased` | compact takes exactly one objective |
| `layout_reason` | string | concrete reason, not "one PR" |
| `execution_root` | string | absolute path of the anchor checkout (or approved worktree) |
| `setup` | string | workspace setup the executor performs |
| `root_cause`, `target_behavior` | string | one line each |
| `assumptions` | string[]? | labelled unverified facts |
| `dirty` | string? | relevant dirty paths; default `none` |
| `security` | object | `sensitive` bool; `controls[{id:"S<n>", text, objectives?}]`; `binding?` (default: the repo's security guidance); `review` (required when sensitive: reviewer, scope, resolved findings) |
| `acceptance` | object[] | `{id:"AC<n>", text, objectives:[n]}`; every objective needs at least one |
| `evidence` | object[] | `{at:"path:line", claim, objectives?}`; at least one |
| `decisions` | object[] | `{text, why, rejected, objectives?}`; at least one |
| `rules` | string[]? | extra binding rules for every file |
| `objectives` | object[] | `{title, files[], tests[], action, validate, prerequisites?[n], wait?{on, check, resume}}` |
| `gates` | object | `commands[]`; `conditional?[{when, command}]` |
| `pr_rows` | object[] | `{branch, base, objectives[n], keyword:"Closes"/"Refs"}`; each objective in exactly one row; exactly one `Closes` |
| `follow_up` | string | consumer search result and any follow-up |
| `rollback` | string | how to undo |

`objectives` on acceptance, evidence, decisions and controls routes the item to those objective files only; omit it for items every file needs. An objective file carries only its own items, so tag precisely and never copy whole-plan context into one.

## Rules

- Evidence `at` is `path` or `path:line`; the renderer builds each file's Freshness command from its own evidence paths.
- `validate` and every `gates.commands` entry are bare commands; the renderer wraps them as `set -o pipefail; <cmd> 2>&1 | tail -n 60`.
- `S<n>` control text is copied verbatim into every objective it tags, plus gates and ship. Write it once, exactly.
- A `wait` makes that file open with a STOP line; `check` is an exact command, `resume` the exact expected result.
- Never put secrets, key material or exploit detail in any field. A follow-up for another repo names only what that work needs and stands alone.
- Use the repo's own domain terms and glossary.

## Decision comment

Posted right after the explicit save answer and before the renderer runs. Renderer reruns never repost. A decision settled after that post (a later answer) goes in one follow-up comment of the same form; never repost a decision.

- Content: only the `decisions` settled beyond what the issue's body and comments already state, each as the choice, why and rejected alternative. Same text the plan check showed; no extra material. None new: post nothing.
- Post with the body on stdin so no text reaches a shell: `gh issue comment <issue URL> --body-file - <<'COMMENT'`. Start with `Planning decisions`.
- Public text: the Rules above apply (no secrets, key material or exploit detail; the repo's domain terms). Never add AI attribution. Never edit the issue body or earlier comments.
- If `gh` is unavailable or the post is denied, do not skip silently: print the comment body in the report for the user to post, and say so.

## Output

| Layout | Files in the planning directory |
|---|---|
| compact | `<issue>-exec.md` |
| phased | `<issue>-exec-obj-<n>.md` per objective, `<issue>-exec-gates.md`, `<issue>-exec-ship.md` |

The progress file `<issue>-plan-progress.md` is created by the executor in the same directory and is never written here.

Estimated sizes (chars/4, not measured tokens): compact about 1.6k; objective files about 1k each; ship about 1.6k. A soft over-budget warning means trim prose or re-check sizing, never drop a fact, control, test or stop.

## Examples

Working specs, one per case, in `../evals/specs/` (relative to this file): `compact-bounded`, `phased-related-flows` (3 objectives, 1 PR), `phased-indivisible`, `sensitive-phased` (S controls + review), `external-wait`, `multi-pr`. Read the nearest one only when a field's shape is unclear.
