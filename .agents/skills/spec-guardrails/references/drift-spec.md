# Drift Spec

A `drift-log.md` records deviations between a spec and the code that implements it. Use it for semi-stabilized modules where unrecorded drift will confuse future maintainers.

## 1. Drift-log.md Format

A drift log uses a six-column table:

| # | Date | Nature | What | Status | Ref |
|---|------|--------|------|--------|-----|
| 1 | YYYY-MM-DD | DELIBERATE | Short description of the divergence | PENDING | `drift-references/YYYY-MM-DD-name.md` |
| 2 | YYYY-MM-DD | BUGFIX | What was fixed and why | RESOLVED | `drift-references/YYYY-MM-DD-name.md` |

- Each row should fit in four lines or fewer.
- Keep the total log to 30 items or fewer.

### Reference File Template

Each drift entry links to a detailed reference file:

```
drift-references/{yyyy-mm-dd}-{name}.md
```

Example:

```
drift-references/2026-06-24-reporting-io-exception.md
```

The reference file explains the context, the exact divergence, the decision, and any follow-up work. Keep the drift-log row short and point readers to the reference file for details.

## 2. Status Lifecycle

A drift is either unwanted (PENDING) or deliberate (CONFIRMED). Both tracks can end at RESOLVED or SUPERSEDED.

```
  PENDING ──────→ RESOLVED ────→ archive
       \_____→ SUPERSEDED ──→ archive

  CONFIRMED ────→ SUPERSEDED ──→ archive
            \_→ RESOLVED ────→ archive
```

- **PENDING**: A divergence that should be fixed — the code needs to match the spec.
- **CONFIRMED**: Reviewed and accepted as deliberate drift. Usually stable; may later transition to RESOLVED (deliberately fixed) or SUPERSEDED (better design replaces it).
- **RESOLVED**: The code was changed so the drift no longer applies. Archive.
- **SUPERSEDED**: A newer entry or better design replaces this one. The drift is no longer relevant. Archive.

## 3. Archival Rules

- Items in **RESOLVED** or **SUPERSEDED** status are automatically archived to `drift-references/archive/{YYYY-MM}.md`.
- The active log keeps only **PENDING** and **CONFIRMED** items.
- When an item is archived, keep its reference number reserved or reuse it with a note to avoid confusion.

## 4. Recording Protocol

### When to Record Drift

Record drift after completing a significant change to a semi-stabilized module. A module is semi-stabilized when its spec has settled but the code still evolves as edge cases are found.

Examples that warrant a drift entry:

- You changed behavior that the spec did not anticipate.
- You changed a spec rule and the code now diverges from older expectations.
- You fixed a divergence so the code now matches the spec again.

### Detection Checklist

Before finishing a change, ask:

1. Does this change behavior that an existing rule covers?
2. Does this change add, remove, or relax a spec rule?
3. Does this fix a place where the code already diverged from the spec?

If the answer to any question is yes, consider recording drift.

### Agent Question Template

When you detect a possible drift, ask yourself:

> This change affects the `{context}` context. Should I record it in `drift-log.md`?

Replace `{context}` with the relevant context or module name. If the answer is yes, ask the user for permission before appending. Do not append silently.

## 5. Nature Classification

Use exactly one of these nature labels:

| Nature | Use when |
|--------|----------|
| **DELIBERATE** | The divergence is an intentional architectural choice. The code is correct, but the spec or assessment reference needs to catch up or explicitly accept the exception. |
| **BUGFIX** | The divergence was a bug. The fix restores alignment with the spec or assessment reference. |
| **CONTENT** | The change adds a new feature or fills a gap the spec or assessment reference did not cover. May need spec expansion or reference alignment note. |

## 6. Context Lifecycle

- **Rename**: Keep the drift entry. A renamed concept is still the same divergence; update the description and add a reference note.
- **Refactor**: If the refactor removes the divergence entirely and the spec is now accurate, archive the entry as SUPERSEDED. Confirm with the user before archiving.

Always record enough context so a future reader can understand why the drift existed, not just what changed.

## 7. Future: Shell-Based Linting

A lightweight shell check could validate that `drift-log.md` does not exceed its table limits. For example, counting pipe characters to guard against too many rows or columns:

```
grep -c "|" drift-log.md | awk '{if ($1>36) print "too many columns/rows"}'
```

This is only a conceptual note for future automation; it is not an active enforcement rule.
