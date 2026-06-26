# drift-review

Review and update statuses in `drift-log.md`.

## Procedure

1. Read `references/drift-spec.md` for the status lifecycle and archival rules.
2. Read the `drift-log.md` file.
3. List every entry with `Status=PENDING`.
4. For each `PENDING` entry, ask the user to choose `CONFIRM` or `RESOLVE`.
5. Update the entry status: set `CONFIRMED` for accepted deliberate drift, or `RESOLVED` for fixed or no-longer-applicable drift.
6. Identify entries with `Status=CONFIRMED` whose date is more than 90 days old.
7. List those stale confirmed entries and suggest archiving them to `drift-references/archive/{YYYY-MM}.md`.
8. Report the final status counts and any archival recommendations.

## Reference

See `references/drift-spec.md` for the status lifecycle and archival rules.
