# drift-lint

Check a `drift-log.md` file for format and consistency.

## Procedure

1. Read `references/drift-spec.md` to confirm the table format and limits.
2. Read the `drift-log.md` file.
3. Count data rows matching `| N | ... |`, excluding the header and separator lines.
4. Verify the row count is 30 or fewer.
5. For each row, count newlines in the `What` field and verify it is four lines or fewer.
6. Verify every `Ref` path points to an existing file.
7. If any `RESOLVED` entries are found, suggest moving them to `drift-references/archive/`.
8. Report the row count, any limit violations, any missing reference files, and any RESOLVED entries that need archiving.

## Reference

See `references/drift-spec.md` for the drift-log format, status lifecycle, and archival rules.
