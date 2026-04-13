---
name: list-atoms
description: |
  List and analyze all report atom classes in the CleanMast Python codebase.
  Discovers atoms by scanning entities/single_mast/ and value_objects/single_mast/
  under packages/cleanmast/src/cleanmast/subdomains/assessment/domain/.
---

You are the `list-atoms` command. Your job is to inventory every `ReportAtom` subclass in the CleanMast Python codebase, categorize them, and report useful metadata about each.

## Atom locations to scan

Primary directories:
- `packages/cleanmast/src/cleanmast/subdomains/assessment/domain/entities/single_mast/`
- `packages/cleanmast/src/cleanmast/subdomains/assessment/domain/value_objects/single_mast/`

Base class:
- `packages/cleanmast/src/cleanmast/subdomains/assessment/domain/entities/report_atom.py`

## Step 1: Discovery (rg or ast-grep)

Run ONE of the following searches to find all concrete atom class definitions:

**Primary — ripgrep (rg):**
```bash
rg "class\s+\w+Atom\s*\(\s*ReportAtom\[" packages/cleanmast/src/cleanmast/subdomains/assessment/domain --sort path
```

**Alternative — ast-grep (if rg unavailable):**
```bash
sg --lang python -p "class $NAME($BASE):" packages/cleanmast/src/cleanmast/subdomains/assessment/domain | grep "ReportAtom"
```

Capture for each match:
- `ClassName` (the atom class)
- `File path`
- `Line number`

## Step 2: File-by-file analysis

For each file that defines an atom, read it briefly to extract:
1. **Schema type** — what `ReportAtom[T, M]` generic parameter `T` is used (e.g., `WeibullSchema`, `TurbulenceSchema`).
2. **Render methods present** — check if it implements:
   - `renderTable(self)`
   - `renderImage(self, output_dir, force=False)`
   - `renderSummary(self)`
3. **Category** — assign one of:
   - `Weibull`
   - `Turbulence`
   - `WindFrequency`
   - `WindRose`
   - `TemporalPattern`
   - `VerticalProfile`
   - `ValueObject` (for atoms under `value_objects/`)
   - `Other`

## Step 3: Cross-reference with registries

Read the following "section service" files to see which atoms are explicitly wired into report subsections. Note any atoms that exist in source but are MISSING from these lists:
- `packages/cleanmast/src/cleanmast/subdomains/assessment/application/subsections/weibull_subsection.py`
- `packages/cleanmast/src/cleanmast/subdomains/assessment/application/subsections/turbulence_subsection.py`
- `packages/cleanmast/src/cleanmast/subdomains/assessment/application/subsections/wind_frequency_subsection.py`
- `packages/cleanmast/src/cleanmast/subdomains/assessment/application/subsections/vertical_profile_subsection.py`
- `packages/cleanmast/src/cleanmast/subdomains/assessment/application/subsections/wind_temporal_subsection.py`
- `packages/cleanmast/src/cleanmast/subdomains/assessment/application/subsections/wind_rose.py`

Also read `packages/cleanmast/tests/assessment/conftest.py` and look for the `all_atoms` fixture. Note any atoms that appear in source but are NOT in `all_atoms`.

## Step 4: Output format

Respond with a structured markdown report containing:

### Summary statistics
- Total atoms discovered
- Atoms by category (count table)
- Atoms missing from subsection registries (if any)
- Atoms missing from test `all_atoms` fixture (if any)

### Atom inventory table
| # | Class Name | Category | File | Schema | Table | Image | Summary |
|---|------------|----------|------|--------|-------|-------|---------|
| 1 | ... | ... | ... | ... | ✅/❌ | ✅/❌ | ✅/❌ |

### Observations (optional)
Any anomalies, duplications, or naming inconsistencies you notice.

## Rules
- Do NOT hallucinate atoms. Only list classes that literally inherit from `ReportAtom[...]`.
- Prefer `rg` for speed, but fall back to reading files directly if rg is unavailable or matches are ambiguous.
- Always verify `renderTable`, `renderImage`, and `renderSummary` presence by reading each atom file when in doubt.
- Keep the report concise but complete.
