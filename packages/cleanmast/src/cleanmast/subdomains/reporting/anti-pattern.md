# Anti-Patterns — Reporting Subdomain

Audit date: 2026-06-26. Updated: 2026-07-26. Checked against `reporting/spec.md` and `subdomains/spec.md`.

> Resolved entries (V1–V6, S2, S11, D1) removed 2026-07-21. Wave 1 (V7, V8,
> S13, S6-F821) resolved 2026-07-26 — baseline gate green (ty, ruff, pytest,
> dvc-verify, lint-imports, ast-grep). IDs of remaining entries are stable —
> do not renumber.

---

## VIOLATIONS

None open.

---

## SMELLS

### S3. `Any` type usage / bare container types

**Files**:
- `subdomains/extreme_wind/section.py` — 5× `list[dict[str, Any]]` (lines 299, 346, 347, 447, 448)
- `subdomains/extreme_wind/compute/__init__.py` — `dict[str, Any]` return types + `list[dict[str, Any]]` accumulators (lines 110, 152, 184, 218, 319)
- `subdomains/extreme_wind/model/gumbel_qq.py:203` — bare `list[dict]`
- `subdomains/wind_temporal/compute.py` — 3× bare `list[dict]` (lines 97, 147, 200)
- `subdomains/turbulence/compute.py:197` — bare `list[dict]`
- `subdomains/representative_year/assemble.py` — 2× bare `list[dict]` (lines 38, 98)
- `subdomains/representative_year/compute.py` — unannotated `item` params (lines 140, 340) + bare `inputs: list` (line 397)

**Issue**: `Any` erases type safety. Bare `list[dict]` without value types makes static analysis and refactoring unreliable. These should be replaced with typed `TypedDict`, `NamedTuple`, or Pydantic models.

### S4. Duplicate constants/functions across modules

Unconsolidated duplicates (V1 DRY fix addressed `get_height_display_name` but not these):

| Constant/Function | Duplicated in |
|---|---|
| `SECTOR_COUNT` / `SECTOR_WIDTH` | `wind_rose` — 3 model files (`wind_rose_atom.py:36-37`, `wind_rose_grid_atom.py:36-37`, `wind_rose_power_grid_atom.py:36-37`) + `compute.py:16-17` |
| `_IEC_CATEGORIES`, `_compute_iec_ti` | `turbulence` — 3 model atoms (`turbulence_multi_atom.py:22-30`, `turbulence_per_height_atom.py:19-27`, `turbulence_summary_atom.py:21-29`) |
| `_MONTH_NAMES` | `wind_temporal` — `monthly_daily_power_atom.py:19` + `monthly_daily_wind_atom.py:19` |

**Future fix**: Consolidate into the capability's compute layer or shared constants. Apply the same pattern used for V1.

### S6. `# noqa` lint suppressions

| File | Suppression | Assessment |
|---|---|---|
| `subdomains/wind_rose/model/` (3 files, line 16 each) | `# noqa: E402` (matplotlib import order) | Should fix via import restructuring, not suppression |

### S7. Hardcoded magic numbers (height thresholds)

Height thresholds scattered as bare floats across capabilities:

| Capability | Values | Files |
|---|---|---|
| `wind_frequency` | 120.0, 160.0, 25.0 (4 model atoms); 3.0 (1 atom) | `wind_distribution_subgrid_atom.py:59-61`, `wind_frequency_hours_atom.py:42,67-69`, `wind_power_hours_atom.py:41,66-68`, `wind_productive_range_atom.py:42-45` |
| `weibull` | 120.0, 160.0 | `weibull_atom.py:101, 140` |
| `representative_year` | 120.0, 160.0 | `compute.py:360` |
| `air_density` | 125.0, 140.0, 160.0 | `model/air_density_atom.py:75-77` |

**Note**: `wind_frequency/compute.py:22` now defines `PRODUCTIVE_RANGE = (3.0, 25.0)` as a named constant, but the model atoms above still hardcode the same values instead of importing it.

**Future fix**: Extract into named constants in `compute/` or `model/` per capability; make the atoms consume them.

### S8. Hardcoded Typst template strings in render/

**Files**: `render/renderer.py` (font names, heading numbering, figure templates, default width `"80%"`), `render/report_builder.py:93-98`

Preamble logic duplicated between `renderer.py` and `report_builder.py`. `report_builder.py:93-98` reconstructs the preamble inline (fonts `'Linux Libertine'`, `'Source Han Serif SC'`, heading numbering `'1.'`) instead of calling `TypstRenderer.render_preamble(self.title)`, which already exists at `renderer.py:27`.

### S9. Overly broad exception handling

**File**: `render/report_builder.py:129`

`except Exception` catches everything during `polish_docx` call, re-raises as `RuntimeError` — masks the original exception type. Should catch the specific docx processing exception class, or at minimum log the full traceback.

### S10. Stringly-typed section registry

**File**: `assemble/section_assembler.py:34-50`

`SECTION_REGISTRY` maps 15 hardcoded string keys to `Section` classes. Keys are plain `str`, not validated against the `SubsectionType` Literal in `configuration/model/report_config.py:19-35`.

**Concrete drift confirmed 2026-07-26**: the registry contains `"extreme_wind"`, which is **not** a valid `SubsectionType` (dead key, unreachable from config), while `"timeseries"` **is** a valid `SubsectionType` but has **no** registry entry (would fail silently to a placeholder at runtime). Multiple keys (`fifty_year_method1/2/3`, `fifty_year_summary`, `iec_standards`) all map to `ExtremeWindSection` with no guard against further drift.

### S12. `object.__setattr__` bypass for frozen dataclass

**File**: `protocols/report_atom.py:88`

`object.__setattr__(self, '_df_hashkey', hashkey)` in `__post_init__` bypasses the frozen constraint to set a content hash. Intentional but fragile — consider `cached_property` or computing via `__init_subclass__` if class-level is sufficient.

### S14. `wind_frequency` ignores config air density

**File**: `subdomains/wind_frequency/compute.py:24, 214`

All other AD consumers read the mast-specific value from config (`item.parameters.air_density`, written by the recommend phase): `extreme_wind/section.py:264`, `wind_rose/section.py:65`, `wind_temporal/section.py:64`. `wind_frequency` instead defaults to its own hardcoded `AIR_DENSITY = 1.225` and calls `calculate_air_density_at_height(sensor.height)` (line 214) without passing the mast's ground density — so power-density results silently use 1.225 even when the config carries a measured value.

**Status**: ⛔ OPEN — needs a product decision (match the assessment reference's 1.225 behavior, or consume config AD like the other capabilities). If 1.225 is intentional, document it in `wind_frequency/spec.md`.
