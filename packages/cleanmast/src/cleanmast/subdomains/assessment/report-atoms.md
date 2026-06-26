# Report Atoms

> Implementation reference for the ReportAtom pattern in assessment domain.
> Concise, unambiguous. Agents: update this when atom behavior changes.
> **Persists at `.sisyphus/report-atoms.md` — DO NOT DELETE during this worktree.**

## Upstream (what generates atoms)

- **Calculators** produce analysis results (DataFrames + statistics) from raw sensor data
- **Builders** convert analysis results → ReportAtom instances via `create()` factory classmethod
- Unified in target architecture: one SectionService per subdomain (calculator + builder + section merged)

## Downstream (what atoms generate)

- **Section services** call `atom.renderTable()`, `atom.renderImage()`, `atom.renderSummary()`
- **Typst IR** is the rendering target:
  - `renderTable() → TypstTable | None` — structured table IR node
  - `renderImage() → Path` — PNG image via Altair/vl-convert, cached by content hash
  - `renderSummary() → list[TypstParagraph]` — structured paragraph IR nodes
- **ReportAssemblyService** collects all section outputs into a unified TypstSection tree

## Types

- **ReportAtom[T, M]** — Entity base class. Identity via `SHA256(Parquet(df))[:12]`.
  - `T = TypeVar("T", bound=SchemaProtocol)` — validates df structure at creation time
  - `M = TypeVar("M", bound=MetaWithCaption)` — display metadata (caption, width, etc.)
  - `create(schema, df, meta) → Self` — factory with validation, sets `_df_hashkey = None`
  - `get_or_compute_df_hashkey() → str` — computes and caches content hash once
- **AtomCollection** — Frozen dataclass. Immutable once assembled.
  - `_by_mast: dict[str, list[ReportAtom]]` — atoms grouped by mast name
  - `_by_key: dict[tuple[str, type[ReportAtom]], list[ReportAtom]]` — atoms indexed by (mast, type)
  - `get(mast, atom_type) → first match` — returns first atom of given type for mast
  - `get_all_by_type(atom_type) → list[ReportAtom]` — all atoms of type across masts
- **Concrete atoms**: ~28 atom types in `entities/single_mast/`, `multi_masts/`, `no_masts/`
  - Wind Rose: 3 atoms (polar chart, power rose, monthly grid)
  - Weibull: consolidated into `SingleMastWeibullSubgridAtom`
  - Turbulence: 5 atoms (intensity, sector, per_height, multi, summary)
  - Wind Frequency: 4 atoms
  - Wind Temporal: 7 atoms (timeseries, daily, monthly patterns + power variants)
  - Vertical Profile: `SingleMastWindShearMatrixAtom`
  - 50-Year Max Wind: 4 atoms (method1, method2, method3, summary)
  - Multi-mast: 2 atoms (air_density, representative_year_calibration)
  - No-masts: 1 atom (iec_standards)

## Rationale

- **Content-addressable**: Same data → same SHA256 hash → automatic cache hit. Parquet serialization ensures stable binary representation across runs.
- **Polymorphic render**: One atom produces table + image + summary from the same DataFrame. Analysis and presentation are separate concerns.
- **Type-safe generic parameters**: T ensures DataFrame matches expected schema; M ensures metadata consistency. Catches mismatches at dev time.
- **Typst IR over raw strings**: Structured IR nodes (TypstTable, TypstParagraph) enable composable report assembly and format-agnostic rendering (PDF via Typst, DOCX). The return types evolved from the original `str` design to match the `typst_ir` package integration.

## Key Deviations from Original ADR (ddd-t-003)

| Aspect | Original ADR | Current Code | Reason |
|--------|-------------|-------------|--------|
| renderTable return | `str` | `TypstTable \| None` | IR integration with typst_ir package |
| renderSummary return | `str` | `list[TypstParagraph]` | Same — structured IR enables composability |
| AtomCollection._by_key value | single `ReportAtom` | `list[ReportAtom]` | Allows flexibility; `get()` returns first |
| M TypeVar bound | unbounded | `MetaWithCaption` | Stricter — guarantees `.caption` access |
| Weibull atoms | 3 separate | 1 consolidated subgrid | Design evolution for report layout |
