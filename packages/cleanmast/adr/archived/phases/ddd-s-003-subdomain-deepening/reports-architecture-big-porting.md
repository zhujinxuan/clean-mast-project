# Reports Architecture: Big Porting Map

> **ADR-GUARDRAILS:** ddd-s-003-subdomain-deepening
> **Status:** proposed (target-state documentation)
> **Parent ADR:** `packages/cleanmast/adr/ddd-s-003-subdomain-deepening.md`
> **Authoritative Source:** `.sisyphus/design-rationale.md`

Complete current-state to target-state mapping for the reports architecture.
Documents every existing file and its future home in the 10-subdomain structure.

---

## 1. Current State

### 1.1 Flat Directory Tree

```
packages/cleanmast/src/cleanmast/subdomains/assessment/domain/
├── entities/
│   ├── single_mast/          (26 files: 24 entities + __init__.py + 1 util)
│   ├── multi_masts/          ( 3 files:  2 entities + __init__.py)
│   ├── no_masts/             ( 2 files:  1 entity  + __init__.py)
│   └── report_atom.py        ( 1 file:  base class)
├── services/
│   ├── sections/             (15 files: 14 sections + __init__.py)
│   ├── calculators/          (16 files: 15 calculators + __init__.py)
│   ├── builders/             (11 files: 10 builders + __init__.py)
│   └── utils/                ( 4 files:  3 utils + __init__.py)
└── value_objects/
    ├── single_mast/          ( 6 files:  5 VOs + __init__.py)
    ├── multi_masts/          ( 3 files:  2 VOs + __init__.py)
    ├── no_masts/             ( 3 files:  2 VOs + __init__.py)
    └── collections/          ( 2 files:  1 VO + __init__.py)
```

### 1.2 Key Statistics

| Metric | Count |
|--------|-------|
| Total entities | 27 (24 single_mast + 2 multi_masts + 1 no_masts) |
| Total section services | 14 |
| Total calculator services | 15 |
| Total builder services | 10 |
| Total value_object files | 10 (5 single_mast + 2 multi_masts + 2 no_masts + 1 collections) |
| Total Python files (excl `__init__`) | **66** |
| Capability groups hidden in flat dirs | **10** |
| Cross-import violations | uncontrolled (single_mast entities import across capability boundaries) |

### 1.3 Architectural Problems

1. **Flat directory masks 10 distinct capabilities.** `entities/single_mast/` contains 24 files spanning 7 subdomains — there is no physical boundary between wind_rose and turbulence atoms.
2. **Calculator → Builder → Section split creates fragile coupling.** Each capability has files scattered across 3 directories (entities, calculators, builders, sections) with implicit naming conventions as the only link.
3. **No import discipline.** Entities in `single_mast/` freely import from other `single_mast/` files regardless of capability. The `iec_standards` subsection (in `services/sections/`) directly imports from `entities/no_masts/`, bypassing any protocol layer.
4. **Value objects are organized by mast-type, not capability.** `value_objects/single_mast/schemas.py` mixes schemas from wind_rose, weibull, turbulence, etc. into a single file.

---

## 2. Target State

### 2.1 Full Nested Subdomain Tree

```
packages/cleanmast/src/cleanmast/subdomains/assessment/
│
├── shared/                          # Contracts used by ≥2 subdomains
│   ├── protocols/
│   │   ├── section.py               # Section ABC (interface all subdomain sections implement)
│   │   ├── report_atom.py           # ReportAtom ABC (moved from entities/report_atom.py)
│   │   └── dataset_access.py        # DataSetAccess ABC
│   ├── adapter_protocols/
│   │   ├── config_provider.py       # ConfigProvider protocol
│   │   └── data_loader.py           # DataLoader protocol
│   ├── ir_types/
│   │   ├── typst_heading.py         # TypstHeading
│   │   ├── typst_section.py         # TypstSection
│   │   └── typst_body.py            # TypstBody
│   └── utils/
│       ├── subsection_renderer.py   # render_subsection_content() — pure, stateless
│       ├── merge.py                 # merge utility
│       └── height_filter.py         # height_filter utility
│
├── adapters/                        # Concrete implementations of shared protocols
│   ├── parquet_dataset.py           # ParquetDataSet (implements DataSetAccess)
│   ├── toml_config.py               # TomlConfig (implements ConfigProvider)
│   └── timeseries_loader.py         # TimeSeriesLoader (implements DataLoader)
│
├── domain/                          # Parent domain — orchestrator only
│   ├── services/
│   │   └── report_assembly.py       # ReportAssemblyService (sole orchestrator)
│   └── entities/
│       └── atom_collection.py       # AtomCollection (shared data structure)
│
└── subdomains/                      # 10 capability subdomains
    │
    ├── wind_rose/                   # adr-ddd-s-003-wind-rose.md
    │   ├── services/
    │   │   └── wind_rose_section.py          # WindRoseSection (calc + build + render)
    │   ├── entities/
    │   │   ├── wind_rose_atom.py             # SingleMastWindRoseAtom (polar chart)
    │   │   ├── wind_power_rose_atom.py       # SingleMastWindPowerRoseAtom
    │   │   └── monthly_wind_rose_grid_atom.py # SingleMastMonthlyWindRoseGridAtom
    │   └── value_objects/
    │       └── schemas.py                    # WindRoseSchema, WindRoseMeta
    │
    ├── weibull/                     # adr-ddd-s-003-weibull.md
    │   ├── services/
    │   │   └── weibull_section.py            # WeibullSection (calc + build + render)
    │   ├── entities/
    │   │   ├── weibull_subgrid_atom.py       # SingleMastWeibullSubgridAtom
    │   │   ├── weibull_fit_result_atom.py    # Weibull fit result
    │   │   ├── weibull_sector_grid_atom.py   # Sector × weibull grid
    │   │   └── wind_distribution_subgrid_atom.py # Wind distribution subgrid
    │   └── value_objects/
    │       └── schemas.py                    # WeibullSchema, WeibullMeta
    │
    ├── turbulence/                  # adr-ddd-s-003-turbulence.md
    │   ├── services/
    │   │   └── turbulence_section.py         # TurbulenceSection (calc + build + render)
    │   ├── entities/
    │   │   ├── turbulence_intensity_atom.py  # Per-height intensity
    │   │   ├── turbulence_per_height_atom.py # Per-height detail
    │   │   ├── turbulence_sector_atom.py     # Per-sector breakdown
    │   │   ├── turbulence_multi_point_atom.py # Multi-mast comparison
    │   │   └── turbulence_summary_atom.py    # Summary table
    │   └── value_objects/
    │       └── schemas.py                    # TurbulenceSchema, TurbulenceMeta
    │
    ├── wind_frequency/              # adr-ddd-s-003-wind-frequency.md
    │   ├── services/
    │   │   └── wind_frequency_section.py     # WindFrequencySection
    │   ├── entities/
    │   │   ├── wind_frequency_hours_atom.py  # Occurrence hours by bin
    │   │   ├── wind_power_hours_atom.py      # Power hours by bin
    │   │   ├── wind_productive_range_atom.py # Productive wind range
    │   │   └── wind_frequency_rose_atom.py   # Frequency rose (if present)
    │   └── value_objects/
    │       └── schemas.py                    # WindFrequencySchema, WindFrequencyMeta
    │
    ├── wind_temporal/               # adr-ddd-s-003-wind-temporal.md
    │   ├── services/
    │   │   └── wind_temporal_section.py      # WindTemporalSection
    │   ├── entities/
    │   │   ├── daily_pattern_atom.py         # Daily wind speed pattern
    │   │   ├── daily_power_pattern_atom.py   # Daily power density pattern
    │   │   ├── monthly_pattern_atom.py       # Monthly wind pattern
    │   │   ├── monthly_power_pattern_atom.py # Monthly power pattern
    │   │   ├── monthly_daily_wind_atom.py    # Monthly×daily wind grid
    │   │   ├── monthly_daily_power_atom.py   # Monthly×daily power grid
    │   │   └── wind_timeseries_atom.py       # Wind timeseries
    │   └── value_objects/
    │       └── schemas.py                    # TemporalPatternSchema, TurbWindSectorSchema, etc.
    │
    ├── vertical_profile/            # adr-ddd-s-003-vertical-profile.md
    │   ├── services/
    │   │   └── vertical_profile_section.py   # VerticalProfileSection
    │   ├── entities/
    │   │   ├── wind_shear_matrix_atom.py     # Wind shear matrix
    │   │   ├── wind_shear_profile_atom.py    # Profile chart
    │   │   └── wind_shear_by_sector_atom.py  # Per-sector shear
    │   └── value_objects/
    │       └── schemas.py                    # WindShearSchema, ShearMeta
    │
    ├── extreme_wind/                # adr-ddd-s-003-extreme-wind.md
    │   ├── services/
    │   │   ├── extreme_wind_section.py       # ExtremeWindSection (parent, wires 5 subs)
    │   │   ├── method1_subsection.py         # Gumbel method (calc + build + render)
    │   │   ├── method2_subsection.py         # Method 2
    │   │   ├── method3_subsection.py         # Method 3
    │   │   ├── summary_subsection.py         # Summary subsection
    │   │   └── iec_standards_subsection.py   # IEC standards (internal subsection)
    │   ├── entities/
    │   │   ├── method1_atom.py               # Method 1 result atom
    │   │   ├── method2_atom.py               # Method 2 result atom
    │   │   ├── method3_atom.py               # Method 3 result atom
    │   │   ├── summary_atom.py               # Summary atom
    │   │   └── iec_standards_atom.py         # IEC standards atom
    │   └── value_objects/
    │       └── schemas.py                    # GumbelParams, MethodSchemas, ExtremeWindMeta, IECStandardsSchema
    │
    ├── representative_year/         # adr-ddd-s-003-representative-year.md
    │   ├── services/
    │   │   └── representative_year_section.py  # RepresentativeYearSection
    │   ├── entities/
    │   │   └── representative_year_atom.py    # MultiMastRepresentativeYearAtom
    │   └── value_objects/
    │       └── schemas.py                     # RepresentativeYearSchema, RepYearMeta
    │
    └── air_density/                 # adr-ddd-s-003-air-density.md
        ├── services/
        │   └── air_density_section.py        # AirDensitySection
        ├── entities/
        │   └── air_density_atom.py           # MultiMastAirDensityAtom
        └── value_objects/
            └── schemas.py                     # AirDensitySchema, AirDensityMeta
```

### 2.2 Key Architectural Changes

| Aspect | Current | Target |
|--------|---------|--------|
| Entity organization | By mast-type (single_mast/ multi_masts/ no_masts/) | By capability subdomain |
| Service pattern | Calculator → Builder → Section (3 classes) | One unified SectionService (calc + build + render) |
| Value objects | By mast-type, one file per type | By subdomain, one schemas.py per subdomain |
| Cross-import discipline | None (free import across capability boundaries) | Subdomain → shared/ + parent adapters/ (via protocols) + self only |
| Base classes | `entities/report_atom.py` (concrete location) | `shared/protocols/report_atom.py` (protocol location) |

---

## 3. Current → Target Mapping Table

> **Legend:** 🟢 = entity, 🔵 = section service, 🟡 = calculator (merged into section), 🟠 = builder (merged into section)

### 3.1 Entities: single_mast → Subdomains

| # | Current Path | Target Path | Subdomain | Type |
|---|-------------|-------------|-----------|------|
| 1 | `entities/single_mast/wind_rose.py` | `subdomains/wind_rose/entities/wind_rose_atom.py` | wind_rose | 🟢 |
| 2 | `entities/single_mast/wind_rose_power_grid.py` | `subdomains/wind_rose/entities/wind_power_rose_atom.py` | wind_rose | 🟢 |
| 3 | `entities/single_mast/wind_rose_grid.py` | `subdomains/wind_rose/entities/monthly_wind_rose_grid_atom.py` | wind_rose | 🟢 |
| 4 | `entities/single_mast/weibull_subgrid.py` | `subdomains/weibull/entities/weibull_subgrid_atom.py` | weibull | 🟢 |
| 5 | `entities/single_mast/wind_distribution_subgrid.py` | `subdomains/weibull/entities/wind_distribution_subgrid_atom.py` | weibull | 🟢 |
| 6 | `entities/single_mast/turbulence_intensity.py` | `subdomains/turbulence/entities/turbulence_intensity_atom.py` | turbulence | 🟢 |
| 7 | `entities/single_mast/turbulence_per_height.py` | `subdomains/turbulence/entities/turbulence_per_height_atom.py` | turbulence | 🟢 |
| 8 | `entities/single_mast/turbulence_sector.py` | `subdomains/turbulence/entities/turbulence_sector_atom.py` | turbulence | 🟢 |
| 9 | `entities/single_mast/turbulence_multi.py` | `subdomains/turbulence/entities/turbulence_multi_point_atom.py` | turbulence | 🟢 |
| 10 | `entities/single_mast/turbulence_summary.py` | `subdomains/turbulence/entities/turbulence_summary_atom.py` | turbulence | 🟢 |
| 11 | `entities/single_mast/wind_frequency_hours.py` | `subdomains/wind_frequency/entities/wind_frequency_hours_atom.py` | wind_frequency | 🟢 |
| 12 | `entities/single_mast/wind_power_hours.py` | `subdomains/wind_frequency/entities/wind_power_hours_atom.py` | wind_frequency | 🟢 |
| 13 | `entities/single_mast/wind_productive_range.py` | `subdomains/wind_frequency/entities/wind_productive_range_atom.py` | wind_frequency | 🟢 |
| 14 | `entities/single_mast/daily_pattern.py` | `subdomains/wind_temporal/entities/daily_pattern_atom.py` | wind_temporal | 🟢 |
| 15 | `entities/single_mast/daily_power_pattern.py` | `subdomains/wind_temporal/entities/daily_power_pattern_atom.py` | wind_temporal | 🟢 |
| 16 | `entities/single_mast/monthly_pattern.py` | `subdomains/wind_temporal/entities/monthly_pattern_atom.py` | wind_temporal | 🟢 |
| 17 | `entities/single_mast/monthly_power_pattern.py` | `subdomains/wind_temporal/entities/monthly_power_pattern_atom.py` | wind_temporal | 🟢 |
| 18 | `entities/single_mast/monthly_daily_wind.py` | `subdomains/wind_temporal/entities/monthly_daily_wind_atom.py` | wind_temporal | 🟢 |
| 19 | `entities/single_mast/monthly_daily_power.py` | `subdomains/wind_temporal/entities/monthly_daily_power_atom.py` | wind_temporal | 🟢 |
| 20 | `entities/single_mast/timeseries.py` | `subdomains/wind_temporal/entities/wind_timeseries_atom.py` | wind_temporal | 🟢 |
| 21 | `entities/single_mast/wind_shear_matrix.py` | `subdomains/vertical_profile/entities/wind_shear_matrix_atom.py` | vertical_profile | 🟢 |
| 22 | `entities/single_mast/fifty_year_max_wind_method1.py` | `subdomains/extreme_wind/entities/method1_atom.py` | extreme_wind | 🟢 |
| 23 | `entities/single_mast/fifty_year_max_wind_method2.py` | `subdomains/extreme_wind/entities/method2_atom.py` | extreme_wind | 🟢 |
| 24 | `entities/single_mast/fifty_year_max_wind_method3.py` | `subdomains/extreme_wind/entities/method3_atom.py` | extreme_wind | 🟢 |
| 25 | `entities/single_mast/fifty_year_max_wind_summary.py` | `subdomains/extreme_wind/entities/summary_atom.py` | extreme_wind | 🟢 |

### 3.2 Entities: multi_masts → Subdomains

| # | Current Path | Target Path | Subdomain | Type |
|---|-------------|-------------|-----------|------|
| 26 | `entities/multi_masts/air_density.py` | `subdomains/air_density/entities/air_density_atom.py` | air_density | 🟢 |
| 27 | `entities/multi_masts/representative_year_calibration.py` | `subdomains/representative_year/entities/representative_year_atom.py` | representative_year | 🟢 |

### 3.3 Entities: no_masts → Subdomains

| # | Current Path | Target Path | Subdomain | Type |
|---|-------------|-------------|-----------|------|

### 3.4 Services: Sections → Subdomains

| # | Current Path | Target Path | Subdomain | Type |
|---|-------------|-------------|-----------|------|
| 29 | `services/sections/wind_rose.py` | `subdomains/wind_rose/services/wind_rose_section.py` | wind_rose | 🔵 |
| 30 | `services/sections/weibull_subsection.py` | `subdomains/weibull/services/weibull_section.py` | weibull | 🔵 |
| 31 | `services/sections/turbulence_subsection.py` | `subdomains/turbulence/services/turbulence_section.py` | turbulence | 🔵 |
| 32 | `services/sections/wind_frequency_subsection.py` | `subdomains/wind_frequency/services/wind_frequency_section.py` | wind_frequency | 🔵 |
| 33 | `services/sections/wind_temporal_subsection.py` | `subdomains/wind_temporal/services/wind_temporal_section.py` | wind_temporal | 🔵 |
| 34 | `services/sections/vertical_profile_subsection.py` | `subdomains/vertical_profile/services/vertical_profile_section.py` | vertical_profile | 🔵 |
| 35 | `services/sections/fifty_year_max_wind_section.py` | `subdomains/extreme_wind/services/extreme_wind_section.py` | extreme_wind | 🔵 |
| 36 | `services/sections/fifty_year_max_wind_method1_subsection.py` | `subdomains/extreme_wind/services/method1_subsection.py` | extreme_wind | 🔵 |
| 37 | `services/sections/fifty_year_max_wind_method2_subsection.py` | `subdomains/extreme_wind/services/method2_subsection.py` | extreme_wind | 🔵 |
| 38 | `services/sections/fifty_year_max_wind_method3_subsection.py` | `subdomains/extreme_wind/services/method3_subsection.py` | extreme_wind | 🔵 |
| 39 | `services/sections/fifty_year_max_wind_summary_subsection.py` | `subdomains/extreme_wind/services/summary_subsection.py` | extreme_wind | 🔵 |
| 41 | `services/sections/air_density_subsection.py` | `subdomains/air_density/services/air_density_section.py` | air_density | 🔵 |
| 42 | `services/sections/representative_year_calibration.py` | `subdomains/representative_year/services/representative_year_section.py` | representative_year | 🔵 |

> **Note on iec_standards:** `iec_standards` is an internal subsection of `extreme_wind`, not a separate subdomain. It is only used within `FiftyYearMaxWindSection` — no other subdomain imports it. The `iec_standards_subsection.py` lives inside `subdomains/extreme_wind/services/` and shares the subdomain's value_objects.

### 3.5 Services: Calculators → Merged into Section Services

| # | Current Path | Target Subdomain | Merge Target | Type |
|---|-------------|-----------------|-------------|------|
| 43 | `services/calculators/wind_rose_calculator.py` | wind_rose | merged into `wind_rose_section.py` | 🟡 |
| 44 | `services/calculators/weibull_fitter.py` | weibull | merged into `weibull_section.py` | 🟡 |
| 45 | `services/calculators/turbulence_calculator.py` | turbulence | merged into `turbulence_section.py` | 🟡 |
| 46 | `services/calculators/wind_frequency_calculator.py` | wind_frequency | merged into `wind_frequency_section.py` | 🟡 |
| 47 | `services/calculators/wind_temporal_analyzer.py` | wind_temporal | merged into `wind_temporal_section.py` | 🟡 |
| 48 | `services/calculators/monthly_stats_calculator.py` | wind_temporal | merged into `wind_temporal_section.py` | 🟡 |
| 49 | `services/calculators/monthly_power_calculator.py` | wind_temporal | merged into `wind_temporal_section.py` | 🟡 |
| 50 | `services/calculators/vertical_profile_analyzer.py` | vertical_profile | merged into `vertical_profile_section.py` | 🟡 |
| 51 | `services/calculators/fifty_year_max_wind_method1_calculator.py` | extreme_wind | merged into `method1_subsection.py` | 🟡 |
| 52 | `services/calculators/fifty_year_max_wind_method2_calculator.py` | extreme_wind | merged into `method2_subsection.py` | 🟡 |
| 53 | `services/calculators/fifty_year_max_wind_method3_calculator.py` | extreme_wind | merged into `method3_subsection.py` | 🟡 |
| 54 | `services/calculators/fifty_year_max_wind_summary_calculator.py` | extreme_wind | merged into `summary_subsection.py` | 🟡 |
| 55 | `services/calculators/gumbel_qq_plot_service.py` | extreme_wind | merged into `method1_subsection.py` | 🟡 |
| 56 | `services/calculators/air_density_calculator.py` | air_density | merged into `air_density_section.py` | 🟡 |
| 57 | `services/calculators/representative_year_calibration_analyzer.py` | representative_year | merged into `representative_year_section.py` | 🟡 |

### 3.6 Services: Builders → Merged into Section Services

| # | Current Path | Target Subdomain | Merge Target | Type |
|---|-------------|-----------------|-------------|------|
| 58 | `services/builders/wind_rose_builder.py` | wind_rose | merged into `wind_rose_section.py` | 🟠 |
| 59 | `services/builders/weibull_builder.py` | weibull | merged into `weibull_section.py` | 🟠 |
| 60 | `services/builders/turbulence_builder.py` | turbulence | merged into `turbulence_section.py` | 🟠 |
| 61 | `services/builders/wind_frequency_builder.py` | wind_frequency | merged into `wind_frequency_section.py` | 🟠 |
| 62 | `services/builders/wind_temporal_builder.py` | wind_temporal | merged into `wind_temporal_section.py` | 🟠 |
| 63 | `services/builders/vertical_profile_builder.py` | vertical_profile | merged into `vertical_profile_section.py` | 🟠 |
| 64 | `services/builders/fifty_year_max_wind_method1_builder.py` | extreme_wind | merged into `method1_subsection.py` | 🟠 |
| 65 | `services/builders/fifty_year_max_wind_method2_builder.py` | extreme_wind | merged into `method2_subsection.py` | 🟠 |
| 66 | `services/builders/fifty_year_max_wind_method3_builder.py` | extreme_wind | merged into `method3_subsection.py` | 🟠 |
| 67 | `services/builders/fifty_year_max_wind_summary_builder.py` | extreme_wind | merged into `summary_subsection.py` | 🟠 |

### 3.7 Shared Infrastructure (Base Classes and Utilities)

These files do not belong to any subdomain — they are cross-cutting contracts shared by ≥2 subdomains:

| # | Current Path | Target Path | Rationale |
|---|-------------|-------------|-----------|
| 68 | `entities/report_atom.py` | `shared/protocols/report_atom.py` | Base class used by all 27 entities |
| 69 | `services/utils/subsection_renderer.py` | `shared/utils/subsection_renderer.py` | Pure utility used by all sections |
| 70 | `services/utils/merge.py` | `shared/utils/merge.py` | Used by ≥2 subdomains |
| 71 | `services/utils/height_filter.py` | `shared/utils/height_filter.py` | Used by ≥2 subdomains |
| 72 | `value_objects/collections/atom_collection.py` | `domain/entities/atom_collection.py` | Parent domain — not subdomain-specific |
| 73 | `value_objects/analysis_input.py` | `shared/protocols/analysis_input.py` | Cross-subdomain input type |

### 3.8 Value Objects: Per-Subdomain Schemas

Value objects currently organized by mast-type will be split per subdomain:

| # | Current Path | Target Path | Subdomain |
|---|-------------|-------------|-----------|
| 74 | `value_objects/single_mast/schemas.py` (wind_rose portion) | `subdomains/wind_rose/value_objects/schemas.py` | wind_rose |
| 75 | `value_objects/single_mast/schemas.py` (weibull portion) | `subdomains/weibull/value_objects/schemas.py` | weibull |
| 76 | `value_objects/single_mast/schemas.py` (turbulence portion) | `subdomains/turbulence/value_objects/schemas.py` | turbulence |
| 77 | `value_objects/single_mast/schemas.py` (wind_freq portion) | `subdomains/wind_frequency/value_objects/schemas.py` | wind_frequency |
| 78 | `value_objects/single_mast/schemas.py` (temporal portion) | `subdomains/wind_temporal/value_objects/schemas.py` | wind_temporal |
| 79 | `value_objects/single_mast/schemas.py` (vertical portion) | `subdomains/vertical_profile/value_objects/schemas.py` | vertical_profile |
| 79a | `domain/value_objects/schemas.py` — `VerticalProfileSchema`, `WindShearSchema` | `subdomains/vertical_profile/value_objects/schemas.py` *(merged)* | vertical_profile |
| 80 | `value_objects/single_mast/schemas.py` (extreme portion) | `subdomains/extreme_wind/value_objects/schemas.py` | extreme_wind |
| 81 | `value_objects/single_mast/report_meta.py` | `subdomains/wind_rose/value_objects/schemas.py` *(merged)* | wind_rose |
| 82 | `value_objects/multi_masts/schemas.py` | split | air_density + representative_year |

> **Note:** Value object splitting is a pure refactoring step. Current `schemas.py` files contain multiple independent schema classes. Each class moves to the subdomain that owns it. The single `report_meta.py` is conceptually multiple metas merged; it will be decomposed per-subdomain.

---

## 4. Import Rule Visualization

### 4.1 The Rule

```
Subdomain → shared/ + parent adapters/ (via protocols) + self only
             NO cross-subdomain imports
```

### 4.2 Allowed vs Forbidden Matrix

```
                          ┌──────────────────────────────────────────────────────────────┐
                          │                      IMPORT TARGET                            │
                          ├────────────┬──────────────┬──────────────┬────────────────────┤
                          │ shared/    │ parent       │ own          │ other subdomains   │
                          │ (protocols)│ adapters/    │ entities/    │                    │
                          │            │ (via protocol)│ services/   │                    │
┌─────────────────────────┼────────────┼──────────────┼──────────────┼────────────────────┤
│ F  wind_rose             │    ✅      │     ✅       │     ✅       │        ❌          │
│ R  weibull               │    ✅      │     ✅       │     ✅       │        ❌          │
│ O  turbulence            │    ✅      │     ✅       │     ✅       │        ❌          │
│ M  wind_frequency        │    ✅      │     ✅       │     ✅       │        ❌          │
│    wind_temporal         │    ✅      │     ✅       │     ✅       │        ❌          │
│    vertical_profile      │    ✅      │     ✅       │     ✅       │        ❌          │
│    extreme_wind          │    ✅      │     ✅       │     ✅       │        ❌          │
│    representative_year   │    ✅      │     ✅       │     ✅       │        ❌          │
│    air_density           │    ✅      │     ✅       │     ✅       │        ❌          │
├─────────────────────────┼────────────┼──────────────┼──────────────┼────────────────────┤
│    parent domain         │    ✅      │     ✅       │     ✅       │   ✅ (orchestrates)│
└─────────────────────────┴────────────┴──────────────┴──────────────┴────────────────────┘
```

### 4.3 Concrete Import Examples

**✅ ALLOWED — wind_rose imports:**

```python
# Protocol (shared/)
from cleanmast.subdomains.assessment.shared.protocols import Section, ReportAtom, DataSetAccess

# IR types (shared/)
from cleanmast.subdomains.assessment.shared.ir_types import TypstHeading, TypstSection, TypstBody

# Utility (shared/)
from cleanmast.subdomains.assessment.shared.utils import subsection_renderer

# Adapter protocol (parent adapters/, via protocol only — never direct import)
# Usage: method signatures accept DataSetAccess protocol, not ParquetDataSet

# Own entities
from cleanmast.subdomains.assessment.subdomains.wind_rose.entities import wind_rose_atom
```

**❌ FORBIDDEN — Cross-subdomain imports:**

```python
# NEVER: wind_rose importing from weibull
from cleanmast.subdomains.assessment.subdomains.weibull.entities import weibull_subgrid_atom  # ❌

# NEVER: turbulence importing from wind_rose
from cleanmast.subdomains.assessment.subdomains.wind_rose.services import wind_rose_section  # ❌

# NEVER: direct concrete adapter import
from cleanmast.subdomains.assessment.adapters import parquet_dataset  # ❌
```

### 4.4 Resolution Path for Cross-Cutting Needs

When subdomain A needs data produced by subdomain B:

1. **Via parent orchestrator:** `ReportAssemblyService` calls A → gets result → passes to B (preferred)
2. **Via shared protocol:** Define a new protocol in `shared/protocols/` that B implements and A depends on (for stable contracts)
3. **Via adapter protocols:** If both subdomains need the same data source, they share `DataSetAccess` from `shared/adapter_protocols/`

---

## 5. Migration Notes

### 5.1 What This Document Covers

This document is a **structural map** — it defines *where* every file goes and *what rules* must be followed.
It does NOT prescribe *how* to perform the code migration (that is a separate implementation task).

### 5.2 Migration Phases (Future)

The migration will proceed in phases, each phase verified before the next:

| Phase | Description | Scope |
|-------|-------------|-------|
| **Phase 1: Scaffolding** | Create all 10 subdomain directories with `__init__.py`, `adr-*.md`, and empty package structure | 0 code changes, 0 test failures |
| **Phase 2: Entity Migration** | Move entity files to their target subdomains, update imports | Entity files only, sections still work via re-exports |
| **Phase 3: Service Merge** | Merge calculator + builder + section into unified SectionService per subdomain | One subdomain at a time |
| **Phase 4: Protocol Gate** | Extract shared protocols (`Section`, `ReportAtom`, `DataSetAccess`) to `shared/`, enforce import rule | Cross-subdomain imports become compile errors |
| **Phase 5: Adapter Extraction** | Move concrete adapter implementations to `adapters/`, wire via dependency injection | Parent domain wires all adapters |

### 5.3 Critical Risks

| Risk | Mitigation |
|------|------------|
| Circular import during entity move | Use lazy imports / `TYPE_CHECKING` during transition |
| Breaking the section rendering pipeline | Move one subdomain at a time, verify render output after each |
| `iec_standards` section currently lives under `extreme_wind` | `iec_standards` is an internal subsection of `extreme_wind`; `iec_standards_subsection.py` stays in `subdomains/extreme_wind/services/` |
| Value object `schemas.py` split breaks dependent modules | Each subdomain gets its own `schemas.py`; shared types stay in `shared/` |
| 73 files across 10 subdomains = probability of concurrent edits | One subdomain migrated and verified per PR |

### 5.4 Tracking

| Subdomain | Entities Moved | Section Merged | Import Rule Enforced | ADR Written |
|-----------|:---:|:---:|:---:|:---:|
| wind_rose | ⬜ | ⬜ | ⬜ | ✅ |
| weibull | ⬜ | ⬜ | ⬜ | ⬜ |
| turbulence | ⬜ | ⬜ | ⬜ | ⬜ |
| wind_frequency | ⬜ | ⬜ | ⬜ | ⬜ |
| wind_temporal | ⬜ | ⬜ | ⬜ | ⬜ |
| vertical_profile | ⬜ | ⬜ | ⬜ | ⬜ |
| extreme_wind | ⬜ | ⬜ | ⬜ | ⬜ |
| representative_year | ⬜ | ⬜ | ⬜ | ⬜ |
| air_density | ⬜ | ⬜ | ⬜ | ⬜ |

> Legend: ✅ = done (wind_rose has L3 ADR from design-rationale.md), ⬜ = pending

---

## Appendix A: File Count Summary

| Directory | Files | `__init__.py` | Substantive | Mapped To |
|-----------|-------|:---:|-------------|------------|
| `entities/single_mast/` | 26 | 1 | 25 | 7 subdomains |
| `entities/multi_masts/` | 3 | 1 | 2 | 2 subdomains |
| `entities/no_masts/` | 2 | 1 | 1 | 1 subdomain |
| `services/sections/` | 15 | 1 | 14 | 8 subdomains |
| `services/calculators/` | 16 | 1 | 15 | merged into sections |
| `services/builders/` | 11 | 1 | 10 | merged into sections |
| **Total** | **73** | **6** | **67** | **10 subdomains + shared/** |

## Appendix B: Subdomain File Allocation

| Subdomain | Entities | Section Files | After Merge | ADR |
|-----------|:---:|:---:|:---:|:---:|
| wind_rose | 3 | 1 | **1** (unified) | L3 ✓ |
| weibull | 2 | 1 | **1** (unified) | ⬜ |
| turbulence | 5 | 1 | **1** (unified) | ⬜ |
| wind_frequency | 3 | 1 | **1** (unified) | ⬜ |
| wind_temporal | 7 | 1 | **1** (unified) | ⬜ |
| vertical_profile | 1 | 1 | **1** (unified) | ⬜ |
| extreme_wind | 5 | 6 (parent + 5 subs) | **6** (parent + 5 subs) | ⬜ |
| representative_year | 1 | 1 | **1** (unified) | ⬜ |
| air_density | 1 | 1 | **1** (unified) | ⬜ |
| **Subtotal** | **28** | **14** | **14** | — |

> **Note:** `extreme_wind` retains 6 service files (parent + 5 internal subsections) per L3 ADR principle: *"One parent section, five child subsections. Internal nesting mirrors the report structure itself."*

(End of file)
