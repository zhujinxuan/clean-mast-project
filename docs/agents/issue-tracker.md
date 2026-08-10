# Issue tracker: Local Markdown

Issues and specs for this repo live as markdown files in `.scratch/`.

(The git remote is Gitee; there is no `gh`/`glab` CLI integration, so the tracker is local files.)

## Conventions

- One feature per directory: `.scratch/<feature-slug>/`
- The spec is `.scratch/<feature-slug>/spec.md`
- Implementation issues are one file per ticket at `.scratch/<feature-slug>/issues/` — never a single combined tickets file
- **Ticket naming** (multi-worktree safety):
  - `/to-tickets` batches (the whole set created in one session): `<NN>-<slug>.md`, numbered from `01` in dependency order
  - Ad-hoc tickets (drift findings, mid-work discoveries — anything created outside a batch, possibly in a different worktree): `<YYYY-MM-DD>-<slug>.md`. The date prefix guarantees a unique path across worktrees and avoids two worktrees independently picking the same `NN`
  - Blocking edges reference tickets by filename slug (`Blocked by: 02-config-heights`, `Blocked by: 2026-08-10-gumbel-fit`), never by bare number
- **Lint**: staged tickets are checked by a pre-commit hook (`.githooks/pre-commit` → `scripts/lint_tickets.py`). Run all tickets manually with `uv run python scripts/lint_tickets.py --all`. Requires `git config core.hooksPath .githooks` once per clone.
- Triage state is recorded as a `Status:` line near the top of each issue file (see `triage-labels.md` for the role strings)
- Comments and conversation history append to the bottom of the file under a `## Comments` heading
- **`.scratch/` is committed to git** — tickets travel with branches across worktrees. Commit ticket files together with the work they describe; an uncommitted ticket exists only in that worktree's working directory and can be lost.
- Every implementation ticket's acceptance criteria end with: `` `uv run python scripts/verify_baseline.py --package cleanmast` is green ``

## Drift is a ticket

When code is discovered to diverge from a `spec.md` standards doc, or a known gap/bug surfaces mid-work, file it as a ticket under `.scratch/` — never in a `drift-log.md`. There is no drift-log machinery in this repo anymore.

## When a skill says "publish to the issue tracker"

Create a new file under `.scratch/<feature-slug>/` (creating the directory if needed).

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally pass the path or the issue number directly.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a file with one **child** file per ticket.

- **Map**: `.scratch/<effort>/map.md` — the Notes / Decisions-so-far / Fog body.
- **Child ticket**: `.scratch/<effort>/issues/NN-<slug>.md`, numbered from `01`, with the question in the body. A `Type:` line records the ticket type (`research`/`prototype`/`grilling`/`task`); a `Status:` line records `claimed`/`resolved`.
- **Blocking**: a `Blocked by: NN, NN` line near the top. A ticket is unblocked when every file it lists is `resolved`.
- **Frontier**: scan `.scratch/<effort>/issues/` for files that are open, unblocked, and unclaimed; first by number wins.
- **Claim**: set `Status: claimed` and save before any work.
- **Resolve**: append the answer under an `## Answer` heading, set `Status: resolved`, then append a context pointer (gist + link) to the map's Decisions-so-far in `map.md`.
