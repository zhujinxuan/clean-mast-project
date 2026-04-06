# Work Plan: Implement WindRose Monthly Grid Atom

## TL;DR

Implement the **missing** WindRose component: `SingleMastMonthlyWindRoseGridAtom` - a 3x4 grid showing monthly wind roses for all 12 months.

**Discovery**: Momus found that other WindRose atoms ALREADY EXIST:
- ✅ `SingleMastMonthlyWindFrequencyRoseAtom` - exists
- ✅ `SingleMastWindPowerRoseAtom` - exists
- ✅ `WindRoseCalculator` - exists
- ✅ `WindRoseSchema` - exists
- ❌ `SingleMastMonthlyWindRoseGridAtom` - **MISSING** (this plan)

---

## Context

The Julia `WindRose.jl` creates 3x4 grid figures (12 subplots) showing monthly wind roses:
- Lines 487-623: Monthly frequency rose grid
- Lines 625-762: Monthly power rose grid

This is the ONLY WindRose component not yet implemented in Python.

---

## Work Objectives

### Deliverables
1. `SingleMastMonthlyWindRoseGridAtom` class
2. Altair-based 3x4 faceted visualization
3. Tests

### Definition of Done
```python
# Atom can be created and rendered
atom = SingleMastMonthlyWindRoseGridAtom.create(
    schema=WindRoseSchema,
    df=monthly_data,
    meta=SingleMastMeta(mast_name="M01", caption="各月风向频率玫瑰图"),
)
image_path = atom.renderImage(Path("./output"))
# Output: 3x4 grid PNG (4000x2700 pixels)
```

---

## Verification Strategy

TDD approach: Test grid structure, facet count, image generation.

---

## Execution Strategy

Single wave - one atom implementation.

---

## Task Dependency Graph

| Task | Depends On | Reason |
|------|-----------|--------|
| 1. SingleMastMonthlyWindRoseGridAtom | None | Uses existing WindRoseSchema |
| 2. Refactor misplaced atoms | Task 1 | Move existing atoms to correct folder |

## Parallel Execution Graph

```
Wave 1 (New Atom):
└── Task 1: SingleMastMonthlyWindRoseGridAtom [visual-engineering]
    Location: entities/single_mast/ (CORRECT)

Wave 2 (Refactoring):
└── Task 2: Refactor existing atoms to entities/ [quick]
    Move: value_objects/single_mast/wind_rose.py → entities/single_mast/wind_rose.py
    Update all imports

Wave FINAL (Verification):
└── F1-F4: Verification tasks
```

**Critical Path**: Task 1 → Task 2
**Parallel Speedup**: N/A (sequential dependency)

---

## Agent Dispatch Summary

| Wave | Tasks | Agent Profile |
|------|-------|---------------|
| 1 | 1 | visual-engineering |

---

## TODOs

- [x] 1. SingleMastMonthlyWindRoseGridAtom

  **What to do**:
  Create the monthly grid atom in `packages/cleanmast/src/cleanmast/subdomains/reporting/entities/single_mast/wind_rose_grid.py`.
  
  **IMPORTANT**: Per ddd-t-002-entities-value-objects, ReportAtoms ARE ENTITIES and belong in `entities/` folder, not `value_objects/`.
  
  **NOTE**: Existing WindRose atoms are currently MISPLACED in `value_objects/single_mast/`:
  - `wind_rose.py` (contains MonthlyWindFrequencyRoseAtom, WindPowerRoseAtom)
  
  The new atom should go in the CORRECT location: `entities/single_mast/`.
  The existing misplaced atoms will be refactored in a separate task.

  **Evidence**: Screenshot of generated 3x4 grid

- [x] 2. Refactor Misplaced WindRose Atoms

  **What to do**:
  Move existing WindRose atoms from `value_objects/` to `entities/` per ddd-t-002.
  
  **Files to move**:
  - `packages/cleanmast/src/cleanmast/subdomains/reporting/value_objects/single_mast/wind_rose.py`
    → `packages/cleanmast/src/cleanmast/subdomains/reporting/entities/single_mast/wind_rose.py`
  
  **Steps**:
  1. Create `entities/single_mast/` directory
  2. Move `wind_rose.py` to new location
  3. Update imports in all files that reference it:
     - `value_objects/single_mast/__init__.py`
     - Any test files
     - Any service files
  4. Update `entities/__init__.py` to export the atoms
  5. Run tests to verify nothing broken
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: File moves and import updates
  
  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: None
  - **Blocked By**: Task 1 (so new atom is in correct location first)
  
  **Acceptance Criteria**:
  - [ ] Files moved to correct locations
  - [ ] All imports updated
  - [ ] No broken references
  - [ ] Tests still pass
  
  **QA Scenario**:
  ```
  Scenario: Verify file locations correct
    Tool: Bash
    Steps:
      1. ls packages/cleanmast/src/cleanmast/subdomains/reporting/entities/single_mast/
      2. ls packages/cleanmast/src/cleanmast/subdomains/reporting/value_objects/single_mast/
    Expected: 
      - entities/single_mast/ has: wind_rose.py, wind_rose_grid.py
      - value_objects/single_mast/ does NOT have wind_rose.py
    Evidence: ls output
  
  Scenario: Import test
    Tool: Python REPL
    Steps:
      1. from cleanmast.subdomains.reporting.entities.single_mast import SingleMastMonthlyWindFrequencyRoseAtom
      2. from cleanmast.subdomains.reporting.entities.single_mast import SingleMastMonthlyWindRoseGridAtom
    Expected: No ImportError
    Evidence: REPL output
  ```
  
  **Commit**: YES
  - Message: `refactor(reporting): move WindRose atoms from value_objects to entities per ddd-t-002`
  - Files: 
    - Deleted: `value_objects/single_mast/wind_rose.py`
    - Added: `entities/single_mast/wind_rose.py`
    - Modified: Import statements across codebase

  **Implementation Details**:
  ```python
  @dataclass
  class SingleMastMonthlyWindRoseGridAtom(
      ReportAtom[WindRoseSchema, SingleMastMeta]
  ):
      """3x4 grid of monthly wind roses (all 12 months)."""
      
      analysis_type: str  # "frequency" or "power"
      
      def renderImage(self, output_dir: Path) -> Path:
          """Generate 3x4 grid figure (12 months).
          
          Chart spec:
          - Rows: 3
          - Columns: 4
          - Each subplot: polar wind rose for one month
          - Multi-height overlay per subplot (>=100m only)
          - Legend on right side (outside grid)
          
          Altair implementation:
          - Use facet with columns=4
          - Each facet: polar mark_arc
          - Size: 4000x2700 pixels (for report quality)
          """
          # Filter to heights >= 100m
          plot_df = self.df.filter(pl.col("height") >= 100)
          
          # Create base chart
          base = alt.Chart(plot_df).mark_arc(stroke="white").encode(
              theta=alt.Theta("sector:O", sort=None),
              radius=alt.Radius("frequency:Q", scale=alt.Scale(zero=True)),
              radius2=alt.datum(0),
              color=alt.Color("height:N", title="高度"),
          )
          
          # Facet by month (3 rows x 4 cols)
          chart = base.facet(
              facet=alt.Facet("month:N", title="月份"),
              columns=4,
          ).properties(
              title=f"{self.meta.mast_name} 各月风向频率玫瑰图",
          )
          
          # Save with high resolution
          output_path = output_dir / f"{self.get_or_compute_df_hashkey()}.png"
          chart.save(output_path, format="png", scale_factor=2)
          return output_path
      
      def renderTable(self) -> str:
          """Summary table of monthly dominant directions."""
          # Group by month, find dominant sector
          ...
          
      def renderSummary(self) -> str:
          """Chinese narrative about seasonal patterns."""
          ...
  ```

  **Must NOT do**:
  - Reimplement existing WindRoseCalculator
  - Reimplement existing frequency/power rose atoms
  - Change existing schemas

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Reason**: Complex Altair faceted visualization with polar coordinates
  - **Skills**: None required
  - **Skills Evaluated but Omitted**:
    - `polars`: Already used via existing code
    - `altair-visualization`: Category covers this

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 1 (single task)
  - **Blocks**: Final verification
  - **Blocked By**: None

  **References**:
  - Julia source: `CleanMastProject/src/ReportTimeSeries/WindRose.jl` lines 487-762
  - Existing atoms: `packages/cleanmast/src/cleanmast/subdomains/reporting/value_objects/single_mast/wind_rose.py`
  - Existing schema: `packages/cleanmast/src/cleanmast/subdomains/reporting/value_objects/single_mast/schemas.py` lines 42-60
  - Faceted charts: Altair documentation on facet()

  **Acceptance Criteria**:
  - [ ] Atom class created with correct inheritance
  - [ ] `renderImage()` generates 3x4 grid PNG
  - [ ] Grid shows 12 months (Jan-Dec)
  - [ ] Each subplot shows 16-sector polar chart
  - [ ] Multi-height overlay works
  - [ ] Image size >= 4000x2700 pixels
  - [ ] `renderTable()` returns valid Typst table
  - [ ] `renderSummary()` returns Chinese narrative

  **QA Scenarios**:
  ```
  Scenario: Generate monthly frequency grid
    Tool: Bash (pytest)
    Preconditions: WindRoseCalculator produces monthly data
    Steps:
      1. cd packages/cleanmast
      2. uv run pytest tests/report/test_wind_rose_grid_atom.py::TestMonthlyWindRoseGridAtom::test_render_image -v
    Expected Result: Test passes, image file created in /tmp/test_output/
    Failure Indicators: No image file, wrong dimensions, missing months
    Evidence: Screenshot of generated grid

  Scenario: Verify grid dimensions
    Tool: Python REPL
    Preconditions: Atom created with sample data
    Steps:
      1. from PIL import Image
      2. img = Image.open(output_path)
      3. assert img.size[0] >= 4000  # width
      4. assert img.size[1] >= 2700  # height
    Expected Result: Assertions pass
    Evidence: Terminal output showing dimensions

  Scenario: Test with frequency data
    Tool: Bash (pytest)
    Steps:
      1. uv run pytest tests/report/test_wind_rose_grid_atom.py -k frequency -v
    Expected Result: 3 tests pass (image, table, summary)
    Evidence: pytest output

  Scenario: Test with power data
    Tool: Bash (pytest)
    Steps:
      1. uv run pytest tests/report/test_wind_rose_grid_atom.py -k power -v
    Expected Result: 3 tests pass (image, table, summary)
    Evidence: pytest output
  ```

  **Evidence to Capture**:
  - [ ] Generated 3x4 grid PNG (frequency)
  - [ ] Generated 3x4 grid PNG (power)
  - [ ] Table Typst output
  - [ ] Summary text output

  **Commit**: YES
  - Message: `feat(reporting): add SingleMastMonthlyWindRoseGridAtom for 3x4 monthly grids`
  - Files: 
    - `packages/cleanmast/src/cleanmast/subdomains/reporting/value_objects/single_mast/wind_rose_grid.py`
    - `packages/cleanmast/tests/report/test_wind_rose_grid_atom.py`
  - Pre-commit: `uv run pytest packages/cleanmast/tests/report/test_wind_rose_grid_atom.py -v`

---

## Final Verification Wave

- [ ] F1. **Plan Compliance Audit** (oracle)
  Verify only grid atom was implemented, no duplication of existing code.
  Check: `git diff --stat` shows only 2 new files.

- [ ] F2. **Code Quality Review** (unspecified-high)
  Run `tsc --noEmit` + `ruff` + `pytest`.
  Check: No lint errors, tests pass.

- [ ] F3. **Visual QA** (unspecified-high)
  Manually inspect generated 3x4 grid:
  - 12 subplots present
  - Each shows polar chart
  - Legend visible
  - Chinese labels correct

- [ ] F4. **Integration Check** (deep)
  Verify atom integrates with existing WindRoseCalculator output.
  Check: Can create atom from real calculator results.

---

## Commit Strategy

1. `feat(reporting): add SingleMastMonthlyWindRoseGridAtom for 3x4 monthly grids`
   - Atom implementation (in correct entities/ location)
   - Tests
   - Pre-commit: pytest

2. `refactor(reporting): move WindRose atoms from value_objects to entities per ddd-t-002`
   - Move wind_rose.py to correct location
   - Update all imports
   - Pre-commit: all tests pass

---

## Success Criteria

- [ ] SingleMastMonthlyWindRoseGridAtom implemented in `entities/single_mast/`
- [ ] 3x4 grid renders correctly (12 months)
- [ ] Both frequency and power versions work
- [ ] Tests pass
- [ ] Image quality suitable for reports (>=4000x2700)
- [ ] No duplication of existing WindRose code
- [ ] **REFACTORING COMPLETE**: Existing atoms moved from `value_objects/` to `entities/`
- [ ] All imports updated and working
