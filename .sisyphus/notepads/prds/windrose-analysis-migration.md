# PRD: WindRose Analysis Migration (Julia → Python)

## Overview

Migrate the Julia `WindRose.jl` module to Python using the Analysis → Atom pattern.

**Source**: `CleanMastProject/src/ReportTimeSeries/WindRose.jl` (1000 lines)

---

## Analysis Types

The WindRose module produces **two main analysis types**:

### 1. Wind Direction Frequency Rose
- 16-sector direction frequency distribution
- Shows which directions wind comes from
- Can be calculated per-height and per-month

### 2. Wind Power Rose  
- 16-sector wind power density distribution
- Shows which directions contribute most energy
- Requires air density configuration

---

## Input Requirements

```python
@dataclass
class WindRoseInput:
    """Input for wind rose analysis."""
    mast_name: str
    timeseries_data: pl.DataFrame  # With timestamp column
    sensors: list[SensorColumn]    # Wind speed & direction sensors
    air_density: AirDensityConfig | None  # Optional, for power calculations
    heights_to_analyze: list[float]  # All heights, filter to >=100m for viz
```

### Sensor Requirements

| Sensor Type | Stat Type | Purpose |
|-------------|-----------|---------|
| WindSpeed | avg | Primary wind speed data |
| WindDirection | avg | Direction for sector assignment |

**Direction Interpolation**: If no direction sensor at exact height, interpolate between closest sensors above/below using angular mean.

---

## Output Schema

### WindRoseSchema (dataframely)

```python
class WindRoseSchema(dy.Schema):
    """Schema for wind rose analysis results."""
    sector: dy.Int64() = dy.Field(ge=1, le=16)  # 16 sectors
    sector_name: dy.String()  # N, NNE, NE, ..., NNW
    angle: dy.Float64()       # Center angle (0°, 22.5°, ...)
    height: dy.Float64()      # Sensor height
    interpolation_marker: dy.String() | None  # null | "外推"
    
    # Frequency analysis (always present)
    frequency: dy.Float64() = dy.Field(ge=0, le=1)  # 0.0 to 1.0
    count: dy.Int64() = dy.Field(ge=0)
    avg_speed: dy.Float64() = dy.Field(ge=0)
    
    # Power analysis (only if air_density provided)
    avg_power: dy.Float64() | None = dy.Field(ge=0)  # W/m²
    total_power: dy.Float64() | None = dy.Field(ge=0)
    power_frequency: dy.Float64() | None = dy.Field(ge=0, le=1)
```

---

## Atom Types Produced

### 1. SingleMastMonthlyWindFrequencyRoseAtom

```python
@dataclass
class SingleMastMonthlyWindFrequencyRoseAtom(
    ReportAtom[WindRoseSchema, SingleMastMeta]
):
    """Renders wind frequency rose for a single mast."""
    
    def renderImage(self, output_dir: Path) -> Path:
        """Generate polar chart with Altair.
        
        - Multi-height overlay (>=100m only)
        - 16 sectors as polar bars
        - Color-coded by height
        """
        
    def renderTable(self) -> str:
        """Typst table: 风向 | 100m | 120m 外推 | ..."""
        
    def renderSummary(self) -> str:
        """Chinese narrative: 
        "测风塔M01在120m, 140m高度主导风向为N、NNE,
         反映了该测风塔的风能资源方向特征。"
        """
```

### 2. SingleMastWindPowerRoseAtom

```python
@dataclass
class SingleMastWindPowerRoseAtom(
    ReportAtom[WindRoseSchema, SingleMastMeta]
):
    """Renders wind power rose for a single mast."""
    
    def renderImage(self, output_dir: Path) -> Path:
        """Generate power rose polar chart.
        
        - Similar to frequency rose BUT
        - Color encoding = power density (red gradient)
        - Shows energy contribution by direction
        """
        
    def renderTable(self) -> str:
        """Typst table with power density values."""
        
    def renderSummary(self) -> str:
        """Chinese narrative:
        "主导能流方向为N、NE，平均风功率密度为185W/m²。"
        """
```

### 3. SingleMastMonthlyWindRoseGridAtom (NEW)

```python
@dataclass
class SingleMastMonthlyWindRoseGridAtom(
    ReportAtom[WindRoseSchema, SingleMastMeta]
):
    """3x4 grid of monthly wind roses (all 12 months)."""
    
    analysis_type: str  # "frequency" or "power"
    
    def renderImage(self, output_dir: Path) -> Path:
        """Generate 3x4 grid figure (12 months).
        
        - Each subplot = one month
        - Multi-height overlay per subplot
        - Shared legend on right side
        """
```

---

## Domain Service: WindRoseCalculator

```python
class WindRoseCalculator:
    """Domain service for wind rose analysis."""
    
    NUM_SECTORS: int = 16
    SECTOR_WIDTH: float = 22.5  # degrees
    
    SECTOR_LABELS: list[str] = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
    ]
    
    def calculate(
        self, 
        input: WindRoseInput
    ) -> AnalysisResult[WindRoseSchema]:
        """
        Main analysis method.
        
        Steps:
        1. Find wind speed sensors at each height
        2. Find/interpolate direction sensor for each height
        3. Assign each timestamp to 16 sectors
        4. Calculate frequency per sector
        5. If air_density: calculate power per sector
        6. Return validated DataFrame with schema
        """
        
    def _get_direction_data(
        self,
        speed_sensor: SensorColumn,
        ts: TimeSeriesData
    ) -> tuple[pl.DataFrame, str]:
        """Get direction column for speed sensor.
        
        If exact height match: use existing direction sensor.
        If no match: interpolate between closest sensors using angular mean.
        """
        
    def _assign_sectors(
        self,
        df: pl.DataFrame,
        dir_column: str
    ) -> pl.DataFrame:
        """Assign each row to wind direction sector (1-16)."""
        # sector = floor((direction + 11.25) / 22.5) + 1
        
    def _calculate_sector_statistics(
        self,
        df: pl.DataFrame,
        speed_col: str,
        has_power: bool,
        air_density: float | None
    ) -> pl.DataFrame:
        """Calculate frequency, avg_speed, [avg_power] per sector."""
```

---

## Analysis → Atom Conversion

```python
class WindRoseAnalysisToAtoms:
    """Converts WindRose AnalysisResult to ReportAtoms."""
    
    def convert(
        self,
        result: AnalysisResult[WindRoseSchema],
        mast_name: str
    ) -> list[ReportAtom]:
        """Create atoms from analysis result.
        
        Returns:
        - SingleMastMonthlyWindFrequencyRoseAtom (overall + monthly)
        - SingleMastWindPowerRoseAtom (if power data present)
        - SingleMastMonthlyWindRoseGridAtom (3x4 grid for each type)
        """
        atoms = []
        
        # Overall frequency rose
        overall_freq = self._create_frequency_atom(result, mast_name, "overall")
        atoms.append(overall_freq)
        
        # Monthly frequency roses (if monthly data present)
        monthly_freq = self._create_frequency_atom(result, mast_name, "monthly")
        atoms.append(monthly_freq)
        
        # Monthly grid (3x4)
        monthly_grid_freq = SingleMastMonthlyWindRoseGridAtom.create(
            schema=WindRoseSchema,
            df=result.data,
            meta=SingleMastMeta(mast_name=mast_name, caption="各月风向频率玫瑰图"),
        )
        atoms.append(monthly_grid_freq)
        
        # Power roses (if power data present)
        if self._has_power_data(result):
            overall_power = self._create_power_atom(result, mast_name, "overall")
            atoms.append(overall_power)
            
            monthly_power = self._create_power_atom(result, mast_name, "monthly")
            atoms.append(monthly_power)
            
            monthly_grid_power = SingleMastMonthlyWindRoseGridAtom.create(
                schema=WindRoseSchema,
                df=result.data,
                meta=SingleMastMeta(mast_name=mast_name, caption="各月风能玫瑰图"),
            )
            atoms.append(monthly_grid_power)
        
        return atoms
```

---

## Visualization Requirements

### Polar Chart Specifications

**Tool**: Altair (vega-lite) with polar coordinates

```python
# Frequency Rose
chart = alt.Chart(df).mark_arc(stroke="white").encode(
    theta=alt.Theta("sector:O", title="风向", sort=None),
    radius=alt.Radius("frequency_pct:Q", title="频率(%)", scale=alt.Scale(zero=True)),
    radius2=alt.datum(0),  # Start from center
    color=alt.Color("height_display:N", title="高度"),
    tooltip=["sector_name", "height_display", "frequency_pct"],
)

# Power Rose (different color encoding)
chart = alt.Chart(df).mark_arc(stroke="white").encode(
    theta=alt.Theta("sector:O", title="风向", sort=None),
    radius=alt.Radius("frequency_pct:Q", title="频率(%)"),
    radius2=alt.datum(0),
    color=alt.Color("avg_power:Q", title="风功率密度(W/m²)", scale=alt.Scale(scheme="reds")),
)
```

### Multi-Height Overlay

- Filter to heights >= 100m for visualization
- Sort heights descending (tallest first)
- Color palette: blue, red, green, orange, purple, cyan, brown, pink
- Line width: 3px for visibility

### 3x4 Monthly Grid

- Size: 4000x2700 pixels
- 3 rows x 4 columns = 12 months
- Legend on right side (column 5)
- Each subplot: polar axis with minimal grid

---

## Report Sections (Future)

**WindRoseSection** will aggregate these atoms:

```python
@dataclass
class WindRoseSection:
    """Section for wind rose analysis."""
    atoms: AtomCollection
    title: str = "风向风能分布"
    level: int = 1
    
    def render(self, images_dir: Path) -> str:
        """Render order:
        1. Overall frequency rose
        2. Overall power rose (if available)
        3. Monthly frequency grid
        4. Monthly power grid (if available)
        5. Summary tables
        """
```

---

## Testing Strategy

### Unit Tests

```python
class TestWindRoseCalculator:
    def test_sector_assignment(self):
        """Test direction → sector mapping."""
        # 0° = N (sector 1)
        # 22.5° = NNE (sector 2)
        
    def test_direction_interpolation(self):
        """Test angular interpolation between sensors."""
        
    def test_frequency_calculation(self):
        """Test frequency sums to 1.0."""
        
    def test_power_calculation(self):
        """Test power density formula."""
        # P = 0.5 * ρ * v³
```

### Integration Tests

```python
class TestWindRoseAtoms:
    def test_frequency_rose_atom(self, sample_data):
        """Test atom creation and rendering."""
        
    def test_power_rose_atom(self, sample_data_with_air_density):
        """Test power rose with air density."""
        
    def test_monthly_grid_atom(self, sample_data):
        """Test 3x4 grid generation."""
```

---

## Dependencies

### Required Packages

```toml
[tool.poetry.dependencies]
altair = "^5.0"          # Polar charts
vl-convert-python = "^1.0"  # PNG export
polars = "^1.0"
dataframely = "^0.1"
```

### Julia Equivalents

| Julia | Python |
|-------|--------|
| CairoMakie | Altair + vl-convert |
| DataFrames | Polars |
| Statistics | scipy.stats |

---

## Migration Checklist

- [ ] Create `WindRoseSchema` with dataframely
- [ ] Implement `WindRoseCalculator` domain service
- [ ] Implement direction interpolation logic
- [ ] Create `SingleMastMonthlyWindFrequencyRoseAtom`
- [ ] Create `SingleMastWindPowerRoseAtom`
- [ ] Create `SingleMastMonthlyWindRoseGridAtom`
- [ ] Implement polar chart rendering with Altair
- [ ] Implement multi-height overlay logic
- [ ] Implement 3x4 grid generation
- [ ] Create analysis → atom converter
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Performance test with large datasets
- [ ] Documentation

---

## Open Questions

1. **Monthly data granularity**: Should monthly analysis use all data or representative year only?
2. **Direction interpolation**: Is angular mean sufficient or need vector average?
3. **Missing sector handling**: Show as 0% or omit from chart?
4. **Air density variation**: Use height-adjusted air density or constant?
