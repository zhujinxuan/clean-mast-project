# Anti-Patterns — Reporting Subdomain

Audit date: 2026-06-26. Updated: 2026-07-21. Checked against `reporting/spec.md` and `subdomains/spec.md`.

> Resolved entries (V1–V6, S2, S11, D1) removed 2026-07-21. IDs of the
> remaining entries are stable — do not renumber.

---

## VIOLATIONS

### V7. Dead code in `wind_rose/compute.py`

**File**: `subdomains/wind_rose/compute.py:28-35`  
**Rule**: Unused definitions.

`_detect_interpolation_marker` function + `_FILL_TYPE_PATTERN` + `_FILL_TYPE_LABELS` constants defined but never called. Dead `import re` inside the unused function body (line 41).

**Status**: ⛔ OPEN.

### V8. Dead code in `air_density/compute.py`

**File**: `subdomains/air_density/compute.py:57-70`  
**Rule**: Unused definitions.

`detect_interpolation_marker` function + `FILL_TYPE_PATTERN` / `FILL_TYPE_LABELS` constants — duplicated from wind_rose, never called within air_density.

**Status**: ⛔ OPEN.

---

## SMELLS

### S3. `Any` type usage / bare container types

**Files**:
- `subdomains/extreme_wind/section.py` — 4× `list[dict[str, Any]]`
- `subdomains/extreme_wind/compute/__init__.py` — `dict[str, Any]` return types
- `subdomains/extreme_wind/model/gumbel_qq.py` — bare `list[dict]`
- `subdomains/wind_temporal/compute.py` — 3× bare `list[dict]`
- `subdomains/representative_year/compute.py` — missing annotations on `item` params + bare `list`

**Issue**: `Any` erases type safety. Bare `list[dict]` without value types makes static analysis and refactoring unreliable. These should be replaced with typed `TypedDict`, `NamedTuple`, or Pydantic models.

### S4. Duplicate constants/functions across modules

Unconsolidated duplicates (V1 DRY fix addressed `get_height_display_name` but not these):

| Constant/Function | Duplicated in |
|---|---|
| `SECTOR_COUNT` / `SECTOR_WIDTH` | `wind_rose` — 3 model files + compute.py |
| `_IEC_CATEGORIES`, `_compute_iec_ti` | `turbulence` — 3 model atoms |
| `_MONTH_NAMES` | `wind_temporal` — monthly_daily_power + monthly_daily_wind atoms |

**Future fix**: Consolidate into the capability's compute layer or shared constants. Apply the same pattern used for V1.

### S6. `# noqa` lint suppressions

| File | Suppression | Assessment |
|---|---|---|
| `subdomains/wind_rose/model/` (3 files) | `# noqa: E402` (matplotlib import order) | Should fix via import restructuring, not suppression |
| `subdomains/air_density/section.py` (2 lines) | `# noqa: F821` on `math.isnan` | **Unnecessary** — `math` is already imported; these suppressions can be deleted |

### S7. Hardcoded magic numbers (height thresholds)

Height thresholds scattered as bare floats across capabilities:

| Capability | Values | Files |
|---|---|---|
| `wind_frequency` | 120.0, 160.0, 3.0, 25.0 | 5 files |
| `weibull` | 120.0, 160.0 | weibull_atom.py |
| `representative_year` | 120.0, 160.0 | compute.py:360 |
| `air_density` | 125.0, 140.0, 160.0 | model/air_density_atom.py |

**Future fix**: Extract into named constants in `compute/` or `model/` per capability.

### S8. Hardcoded Typst template strings in render/

**Files**: `render/renderer.py` (font names, section markers, figure templates, default widths), `render/report_builder.py:94-98`

Preamble logic duplicated between `renderer.py` and `report_builder.py`. Font names (`'Linux Libertine'`, `'Source Han Serif SC'`), heading numbering `'1.'`, figure templates, default width `'80%'` hardcoded as inline strings. `report_builder.py` should call `TypstRenderer.render_preamble(self.title)` instead of reconstructing the preamble inline.

### S9. Overly broad exception handling

**File**: `render/report_builder.py:130`

`except Exception` catches everything during `polish_docx` call, re-raises as `RuntimeError` — masks the original exception type. Should catch the specific docx processing exception class, or at minimum log the full traceback.

### S10. Stringly-typed section registry

**File**: `assemble/section_assembler.py:36-52`

`SECTION_REGISTRY` maps 15 hardcoded string keys to `Section` classes. Not validated against `VALID_SUBSECTION_TYPES` from `report_config.py`. Multiple keys (`fifty_year_method1/2/3`, `fifty_year_summary`, `iec_standards`) all map to `ExtremeWindSection` with no guard against drift. A missing or mismatched key would fail silently at runtime.

### S12. `object.__setattr__` bypass for frozen dataclass

**File**: `protocols/report_atom.py:92`

`object.__setattr__(self, '_df_hashkey', hashkey)` in `__post_init__` bypasses the frozen constraint to set a content hash. Intentional but fragile — consider `cached_property` or computing via `__init_subclass__` if class-level is sufficient.

### S13. Re-export parent dependency through child `__init__.py`

**Files**:
- `subdomains/wind_rose/model/__init__.py` — re-exports `get_height_display_name`
- `subdomains/vertical_profile/model/__init__.py` — re-exports `get_height_display_name`

Child capability `__init__.py` re-exports a symbol from the parent `reporting/model/`. Consumers should import directly from `reporting.model.height_label` rather than through capability model layers.
