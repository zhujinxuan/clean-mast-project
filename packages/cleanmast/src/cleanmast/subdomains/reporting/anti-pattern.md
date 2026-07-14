# Anti-Patterns — Reporting Subdomain

Audit date: 2026-06-26. Updated: 2026-07-01. Checked against `reporting/spec.md` and `subdomains/spec.md`.

---

## VIOLATIONS

### V1. `get_height_display_name` DRY violation (RESOLVED)

**Resolution**: Consolidated into `reporting/model/height_label.py` (`consolidate-height-display` plan). All 7 duplicates removed (6 deleted, 1 converted to thin wrapper `_height_label` in wind_frequency). Canonical function now uses unified parentheses format: `"120m(外推)"`. ~50 callers updated.

**Status**: ✅ Done.

### V2. `ExtremeWindSection.from_computed_results` accepts pre-computed DataFrames (RESOLVED)

**File**: `subdomains/extreme_wind/section.py:100`  
**Rule**: Spec Rule 9 — "pre-computed DataFrame inputs are forbidden"

`from_computed_results` is a public classmethod accepting raw `pl.DataFrame` params. Only called internally by `from_inputs` today, but nothing prevents external bypass.

**Status**: ✅ Done. Method renamed to `_from_computed_results` (privatized).

### V3. `import tomli` / `import tomli_w` in model layer

**File**: `model/report_config.py:13-14`  
**Rule**: Spec Rule 11 — "Never `import tomli` or `import tomli_w` directly in reporting, application, or any subdomain."

`FlatReportConfig.from_toml` directly calls `tomli.load()` (line 221). `FlatReportConfig.to_toml` directly calls `tomli_w.dumps()` (line 232). TOML I/O must route through `cleanmast.subdomains.configuration.value_objects` Pydantic models.

**Status**: ⛔ OPEN.

### V4. Broken `__all__` in `extreme_wind/model/__init__.py`

**File**: `subdomains/extreme_wind/model/__init__.py:19`  
**Rule**: `__init__.py` exports only model types and api functions.

`get_height_display_name` listed in `__all__` but never imported in module namespace. Would raise `ImportError` at runtime on `from extreme_wind.model import get_height_display_name`.

**Status**: ⛔ OPEN.

### V5. Cross-layer import: model → compute in `extreme_wind`

**File**: `subdomains/extreme_wind/model/method2_atom.py:25-27`  
**Rule**: Pipeline direction — model ← protocols ← compute (model must not import compute).

`Method2QQSustainedAtom` and `Method2QQExtremeAtom` import `generate_gumbel_qq_subgrid` from `compute/gumbel_qq.py`. Model layer depending on compute breaks the pipeline architecture.

**Status**: ⛔ OPEN.

### V6. IO inside compute layer — `extreme_wind/compute/gumbel_qq.py`

**File**: `subdomains/extreme_wind/compute/gumbel_qq.py:157,160,228,231`  
**Rule**: Spec anti-pattern — "IO inside compute/; keep calculations pure."

`output_dir.mkdir()` + `image_path.write_bytes()` — writes PNG files from the compute layer. Image writing should move to the assemble or render layer.

**Status**: ⛔ OPEN.

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

### S1. `api.py` imports from `dataingestion.infrastructure`

`api.py:16` imports `load_timeseries` from `dataingestion.infrastructure`. Permitted by `subdomains/spec.md` Rule 13 but reaches into a downstream `infrastructure` module.

> **Note**: Low priority — permitted by spec and low risk.

### S2. Two `SingleMastAnalysisInput` classes in different subdomains (RESOLVED)

**Files**:
- `assessment/shared/value_objects/analysis_input.py` — basic (no `representative_year_calibration_payload`)
- `reporting/model/analysis_input.py` — extended (has `representative_year_calibration_payload`)

**Resolution**: Merged into `cleanmast.subdomains.reporting.model.analysis_input` (canonical). Assessment keeps a re-export shim for backward compat.

### S3. `Any` type usage / bare container types

**Files**:
- `subdomains/extreme_wind/section.py` — 4× `list[dict[str, Any]]`
- `subdomains/extreme_wind/compute/__init__.py` — `dict[str, Any]` return types
- `subdomains/extreme_wind/compute/gumbel_qq.py` — bare `list[dict]`
- `subdomains/wind_temporal/compute.py` — 3× bare `list[dict]`
- `subdomains/representative_year/compute.py` — missing annotations on `item` params + bare `list`

**Issue**: `Any` erases type safety. Bare `list[dict]` without value types makes static analysis and refactoring unreliable. These should be replaced with typed `TypedDict`, `NamedTuple`, or Pydantic models.

### S4. Duplicate constants/functions across modules

Unconsolidated duplicates (V1 DRY fix addressed `get_height_display_name` but not these):

| Constant/Function | Duplicated in |
|---|---|
| `SECTOR_COUNT` / `SECTOR_WIDTH` | `wind_rose` — 3 model files + compute.py |
| `_IEC_CATEGORIES`, `_compute_iec_ti` | `turbulence` — 3 model atoms |
| `_SECTOR_NAMES` | `representative_year` — compute.py + sector_table_atom.py |
| `_MONTH_NAMES` | `wind_temporal` — monthly_daily_power + monthly_daily_wind atoms |
| Gas constants (`GAS_CONSTANT_DRY_AIR`, etc.) | `air_density` — compute.py + air_density_atom.py |

**Future fix**: Consolidate into the capability's compute layer or shared constants. Apply the same pattern used for V1.

### S5. IO inside model definitions

**File**: `model/report_config.py:218-233`

`FlatReportConfig.from_toml` opens and reads a TOML file via `open(path, 'rb')` + `tomli.load()`. `FlatReportConfig.to_toml` writes to disk via `path.write_text()`. Models should not perform file IO. This is the same root cause as V3 — once TOML routing goes through `configuration.value_objects`, the IO moves out of the model.

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
| `wind_temporal` | 100.0 | 6 files, 10 occurrences |
| `weibull` | 120.0, 160.0 | weibull_atom.py |
| `representative_year` | 120.0, 160.0, 2.0, 30 | compute.py |
| `air_density` | 125.0, 140.0, 160.0 | air_density_atom.py |

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


### S11. Lazy import in method body (RESOLVED)

**File**: `protocols/report_atom.py:187`

`from typst_ir import TypstFigure` was imported inside `renderImageTypst()` method body. Not a circular import — `typst_ir` is an external package with no reverse dependency. The `TYPE_CHECKING` guard at the top already provided the type; the runtime import simply needed to be at the top level.

**Resolution**: Moved `from typst_ir import TypstFigure` to top-level alongside `polars`. `TypstParagraph` and `TypstTable` remain under `if TYPE_CHECKING:` (type-only).

**Status**: ✅ Done.

### S12. `object.__setattr__` bypass for frozen dataclass

**File**: `protocols/report_atom.py:92`

`object.__setattr__(self, '_df_hashkey', hashkey)` in `__post_init__` bypasses the frozen constraint to set a content hash. Intentional but fragile — consider `cached_property` or computing via `__init_subclass__` if class-level is sufficient.

### S13. Re-export parent dependency through child `__init__.py`

**Files**:
- `subdomains/wind_rose/model/__init__.py` — re-exports `get_height_display_name`
- `subdomains/vertical_profile/model/__init__.py` — re-exports `get_height_display_name`

Child capability `__init__.py` re-exports a symbol from the parent `reporting/model/`. Consumers should import directly from `reporting.model.height_label` rather than through capability model layers.

---

## KNOWN DEVIATIONS

### D1. `representative_year` accepts `MesoSectionInput` instead of `SingleMastAnalysisInput` (RESOLVED)

**Status**: ✅ Done. Standardized to `SingleMastAnalysisInput` with `RepresentativeYearCalibrationPayload`. `MesoSectionInput` removed. 16-sector analysis with Altair scatter grids added.
