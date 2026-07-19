# ddd-s-004 Execution — Kickoff Package

Status: **ready to launch on a dedicated branch**, blocked on Fork 2 (scope) + handoff §6 questions.
Created: 2026-07-19 (discussion between user + agent, workspace `veritial-atoms-use-original-heights`).

## What this is

Everything a future session needs to execute ADR ddd-s-004 (composition root + DI)
without re-deriving this discussion.

## Files

| File | Role |
|---|---|
| `session-prompt.md` | Paste-ready launcher prompt for the executing session. Fork 1 pre-settled; Fork 2 + §6 questions asked at kickoff. |
| `kickoff-decisions.md` | Grill record: settled/pending forks, layer-role definitions, full cross-domain edge inventory (grep evidence, supersedes the handoff's partial list). |

## Related documents (in repo, committed)

- `packages/cleanmast/adr/ddd-s-004-composition-root-di.md` — the decision.
- `packages/cleanmast/adr/phases/ddd-s-004-composition-root-di/on-plan.md` — handoff: evidence, principles, spec updates, 4-wave plan, verification gate, open questions, traps.

## How to resume

1. Create the execution branch.
2. Paste `session-prompt.md` into a new agent session.
3. Answer the kickoff questions when the agent asks (Fork 2 is the big one — see `kickoff-decisions.md`).

## Warning

The golden gate requires local untracked dirs `projects/2026-07-02-松原/` (untouched
golden master) and `projects/2026-07-02-松原-gate/` (1.8GB working copy). They are NOT
in git. On a fresh clone, recreate the gate copy before starting.
