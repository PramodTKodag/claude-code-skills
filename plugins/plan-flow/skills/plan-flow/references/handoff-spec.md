# Handoff spec

Contents: Fields · Rules · Decision comment · Output · Executor evidence · Completion comments · Examples

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
| `pr_rows` | object[] | `{branch, base, objectives[n], keyword:"Closes"/"Refs"}`, bottom first; each objective in exactly one row; exactly one `Closes`. `base` is the base branch or an earlier row's branch (a stack is one chain); a stacked row's objectives all come after its base row's, and `Closes` sits on the top row |
| `follow_up` | string | consumer search result and any follow-up |
| `rollback` | string | how to undo |

`objectives` on acceptance, evidence, decisions and controls routes the item to those objective files only; omit it for items every file needs. An objective file carries only its own items, so tag precisely and never copy whole-plan context into one.

## Rules

- `prerequisites` may name only objectives in the same row or a row it stacks on; the first objective of a stacked row inherits all objectives below it automatically.
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

The progress file `<issue>-plan-progress.json` is created by the executor in the same directory and is never written here.

Estimated sizes (chars/4, not measured tokens): compact about 2.2k; objective files about 1.5k each; gates about 1.6k; ship about 2.0k. A soft over-budget warning means trim prose or re-check sizing, never drop a fact, control, test or stop.

## Executor evidence

- Every file carries the Tests rule: a run passes only if its output shows the expected tests ran and passed (no zero-test or unmatched-filter pass), and no test or assertion is deleted, skipped or weakened to get green.
- The executor keeps `<issue>-plan-progress.json` in the planning directory: fixed keys (including `comments`, the posted completion comment IDs), values only edited, one `criteria` entry per Acceptance ID (`pending`, then `passing` or `failing` with evidence). Gates fill the evidence; ship refuses unvalidated criteria.
- Gates and compact files carry one `git diff --name-only` scope command per PR row, built from the row's objective `files`; any path it prints is justified or reverted.
- The renderer reports a soft warning when acceptance criteria exceed four per objective.

## Completion comments

- Each objective file, the gates file and the ship file posts one `Execution complete: <phase>` issue comment, only once that phase's work is fully done: objective after commit and passing validation, gates after every criteria entry is set, ship after every PR row is open. A compact file posts one per stage (objective, gates, ship).
- A stop, failure or `Hold` posts nothing. The ID goes under `comments` in the progress file; a resumed run never reposts.
- Content is what was done (SHAs, tests, results, PR URLs, gaps), under the same public-text rules as decision comments. Never edits the issue body or earlier comments.

## Examples

Working specs, one per case, in `../evals/specs/` (relative to this file): `compact-bounded`, `phased-related-flows` (3 objectives, 1 PR), `phased-indivisible`, `sensitive-phased` (S controls + review), `external-wait`, `multi-pr`. Read the nearest one only when a field's shape is unclear.
