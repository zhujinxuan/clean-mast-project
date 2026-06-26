# spec-init

Create a new `spec.md` from the project template.

## Procedure

1. Read `references/spec-template.md` to confirm the four-section format.
2. Check whether a `spec.md` already exists at the target path.
3. If the file exists, warn the user and do not overwrite without explicit approval.
4. If the file does not exist, create it using the template from `references/spec-template.md`.
5. Fill the `## Purpose` section with one sentence derived from the target context or capability path.
6. Leave `## Rules`, `## Anti-patterns`, and `## When in doubt` populated with `[TODO]` placeholders.
7. Report the created file path to the user.

## Reference

See `references/spec-template.md` for the required four-section template.
