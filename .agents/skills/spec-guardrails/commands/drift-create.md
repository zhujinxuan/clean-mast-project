# drift-create

Add a new entry to `drift-log.md`.

## Procedure

1. Ask the user: "This change affects the `{context}` context. Should I record this in `drift-log.md`?"
2. If the user declines, stop and note that no drift entry was created.
3. If the user accepts, determine the nature of the drift using exactly one of `DELIBERATE`, `BUGFIX`, or `CONTENT`.
4. Write a short `What` description that is four lines or fewer.
5. Set `Date` to today's date in `YYYY-MM-DD` form.
6. Assign the next sequential entry number.
7. Append a new row to the `drift-log.md` table with `Status=PENDING`.
8. If the user requested a `--ref`, create `drift-references/{date}-{name}.md` with full context, divergence, decision, and follow-up notes.
9. Report the new entry number and reference file path if one was created.

## Reference

See `references/drift-spec.md` for the recording protocol, nature classification, and reference file template.
