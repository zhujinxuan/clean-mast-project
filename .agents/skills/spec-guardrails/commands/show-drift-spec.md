# show-drift-spec

Display the drift-log column schema, Nature classification, and Status lifecycle.

## Procedure

1. Display the drift-log table schema:

| Column | Meaning |
|--------|---------|
| # | Sequential entry number |
| Date | When the drift was recorded (YYYY-MM-DD) |
| Nature | Classification: DELIBERATE, BUGFIX, or CONTENT |
| What | Short description of the divergence (max 4 lines) |
| Status | Lifecycle: PENDING -> CONFIRMED/RESOLVED -> SUPERSEDED |
| Ref | Link to detailed reference file in drift-references/ |

2. Display the Nature classification:

| Nature | When to use |
|--------|-------------|
| DELIBERATE | Intentional divergence from spec or assessment reference. Code is correct. |
| BUGFIX | Bug fix restoring alignment with the spec or assessment reference. |
| CONTENT | New feature or gap-fill the spec or assessment reference didn't cover. |

3. Display the Status lifecycle:

PENDING -> CONFIRMED / RESOLVED -> SUPERSEDED

- PENDING: Recorded, not yet reviewed.
- CONFIRMED: Reviewed and accepted as deliberate drift.
- RESOLVED: Code changed; drift no longer applies (auto-archived).
- SUPERSEDED: A newer entry replaces this one.

4. Note: "spec" in Nature descriptions means "the spec or assessment reference."
   Multiple drifts may reference the same assessment reference module.

## Reference

See `references/drift-spec.md` for the full drift protocol including
recording protocol, archival rules, context lifecycle, and reference file template.
