# spec-lint

Check a `spec.md` file for structural correctness.

## Procedure

1. Read the `spec.md` file under review.
2. Verify the four required sections are present:
   - `## Purpose`
   - `## Rules`
   - `## Anti-patterns`
   - `## When in doubt`
3. Check that each `## Rules` item is numbered or bulleted and written as an enforceable statement.
4. If any section is missing, report `FAIL: missing {section}` for each absent section.
5. If all four sections are present and the Rules are enforceable, report `PASS`.

## Reference

See `references/spec-template.md` for the required four-section format and examples of enforceable rules.
