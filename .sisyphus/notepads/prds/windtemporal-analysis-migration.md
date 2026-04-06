# PRD: WindTemporal Analysis Migration (Julia → Python)

## Overview

Migrate the Julia `WindTemporal.jl` module to Python using the Analysis → Atom pattern.

**Source**: `CleanMastProject/src/ReportTimeSeries/WindTemporal.jl` (714 lines)

---

## Analysis Purpose

Analyze temporal patterns in wind speed and wind power data:
- Time series plots
- Daily (24-hour) patterns
- Monthly patterns
- Monthly-daily combined patterns (24h x 12 months)

---

## Input Requirements

```python
@dataclass
class WindTemporalInput:
    """Input for temporal wind analysis."""
    mast_name: str
    timeseries_data: pl.DataFrame  # Must have timestamp column
    sensors: list[SensorColumn]    # WindSpeed avg sensors
    air_density: AirDensityConfig | None
    min_plot_height: float = 100.0  # Only plot heights >= this
```

### Sensor Requirements

| Sensor Type | Stat Type | Purpose |
|-------------|-----------|---------|
| WindSpeed | avg | Wind speed measurements |

---

## Output Schema

### TemporalPatternSchema (dataframely)

```python
class TemporalPatternSchema(dy.Schema):
    """Schema for temporal analysis results."""
    mast_name: dy.String()
    timestamp: dy.Datetime()
    
    # For time series data
    wind_speed: dy.Float64() | None
    wind_power: dy.Float64() | None
    height: dy.Float64()
    
    # For aggregated patterns
    hour: dy.Int64() | None = dy.Field(ge=0, le=23)
    month: dy.Int64() | None = dy.Field(ge=1, le=12)
    
    # Statistics
    mean_speed: dy.Float64() | None
    mean_power: dy.Float64() | None
```

---

## Atom Types Produced

### 1. SingleMastWindTimeseriesAtom

```python
@dataclass
class SingleMastWindTimeseriesAtom(
    ReportAtom[TemporalPatternSchema, SingleMastMeta]
):
    """Full time series line chart."""
    
    def renderImage(self, output_dir: Path) -> Path:
        """Generate line chart:
        
        - X-axis: Time (full date range)
        - Y-axis: Wind Speed (m/s)
        - Multiple lines: one per height (>=100m)
        - Legend showing heights
        """
        
    def renderTable(self) -> str:
        """Typst table with summary statistics."""
```

### 2. SingleMastDailyPatternAtom

```python
@dataclass
class SingleMastDailyPatternAtom(
    ReportAtom[TemporalPatternSchema, SingleMastMeta]
):
    """24-hour average pattern (diurnal cycle)."""
    
    def renderImage(self, output_dir: Path) -> Path:
        """Generate line chart:
        
        - X-axis: Hour of Day (0-23)
        - Y-axis: Wind Speed (m/s)
        - Multiple lines: one per height
        - Title: "24-Hour Wind Speed Pattern"
        """
        
    def renderTable(self) -> str:
        """Typst table: 小时 | 100m | 120m | ..."""
```

### 3. SingleMastDailyPowerPatternAtom

```python
@dataclass
class SingleMastDailyPowerPatternAtom(
    ReportAtom[TemporalPatternSchema, SingleMastMeta]
):
    """24-hour wind power pattern (if air_density provided)."""
    
    def renderImage(self, output_dir: Path) -> Path:
        """Similar to daily pattern but for wind power density."""
```

### 4. SingleMastMonthlyPatternAtom

```python
@dataclass
class SingleMastMonthlyPatternAtom(
    ReportAtom[TemporalPatternSchema, SingleMastMeta]
):
    """Monthly average pattern (seasonal cycle)."""
    
    def renderImage(self, output_dir: Path) -> Path:
        """Generate grouped bar chart:
        
        - X-axis: Month (1-12)
        - Y-axis: Wind Speed (m/s)
        - Grouped bars: one group per height
        - Title: "Monthly Wind Speed Pattern"
        """
```

### 5. SingleMastMonthlyPowerPatternAtom

```python
@dataclass
class SingleMastMonthlyPowerPatternAtom(
    ReportAtom[TemporalPatternSchema, SingleMastMeta]
):
    """Monthly wind power pattern."""
```

### 6. SingleMastMonthlyDailyWindAtom

```python
@dataclass
class SingleMastMonthlyDailyWindAtom(
    ReportAtom[TemporalPatternSchema, SingleMastMeta]
):
    """3x4 grid showing daily pattern for each month."""
    
    def renderImage(self, output_dir: Path) -> Path:
        """Generate 3x4 faceted plot:
        
        - Rows: 3
        - Columns: 4
        - Each subplot: 24-hour pattern for one month
        - X-axis: Hour (0-23)
        - Y-axis: Wind Speed
        - Color: Height
        
        Size: 1200x900 pixels
        """
```

### 7. SingleMastMonthlyDailyPowerAtom

```python
@dataclass
class SingleMastMonthlyDailyPowerAtom(
    ReportAtom[TemporalPatternSchema, SingleMastMeta]
):
    """3x4 grid showing daily power pattern for each month."""
```

---

## Domain Service: WindTemporalAnalyzer

```python
class WindTemporalAnalyzer:
    """Domain service for temporal wind pattern analysis."""
    
    def analyze_wind_speed_timeseries(
        self,
        input: WindTemporalInput
    ) -> pl.DataFrame:
        """
        Generate full time series data for plotting.
        
        Returns DataFrame with:
        - timestamp
        - {height}m columns for each height
        """
        
    def analyze_daily_pattern(
        self,
        input: WindTemporalInput
    ) -> tuple[pl.DataFrame, pl.DataFrame | None]:
        """
        Calculate 24-hour average patterns.
        
        Steps:
        1. Add hour column (0-23)
        2. Group by hour, calculate mean for each height
        3. If air_density: calculate power for each observation
        4. If air_density: calculate mean power by hour
        
        Returns:
            (speed_df, power_df | None)
        """
        
    def analyze_monthly_pattern(
        self,
        input: WindTemporalInput
    ) -> tuple[pl.DataFrame, pl.DataFrame | None]:
        """
        Calculate monthly average patterns.
        
        Steps:
        1. Add month column (1-12)
        2. Group by month, calculate mean for each height
        3. If air_density: calculate power means
        
        Returns:
            (speed_df, power_df | None)
        """
        
    def analyze_monthly_daily(
        self,
        input: WindTemporalInput,
        analyze_power: bool = False
    ) -> pl.DataFrame:
        """
        Calculate hourly patterns for each month.
        
        Creates DataFrame for faceted plotting:
        - hour (0-23)
        - month (1-12)
        - height
        - value (wind speed or power)
        """
        
    def calculate(
        self,
        input: WindTemporalInput
    ) -> AnalysisResult[TemporalPatternSchema]:
        """
        Main analysis method.
        
        Runs all temporal analyses and combines results.
        """
```

---

## Analysis → Atom Conversion

```python
class WindTemporalAnalysisToAtoms:
    """Converts Temporal AnalysisResult to ReportAtoms."""
    
    def convert(
        self,
        result: AnalysisResult[TemporalPatternSchema],
        mast_name: str
    ) -> list[ReportAtom]:
        """Create atoms from analysis result."""
        atoms = []
        
        # 1. Time series plot
        timeseries_atom = SingleMastWindTimeseriesAtom.create(...)
        atoms.append(timeseries_atom)
        
        # 2. Daily pattern
        daily_atom = SingleMastDailyPatternAtom.create(...)
        atoms.append(daily_atom)
        
        # 3. Monthly pattern
        monthly_atom = SingleMastMonthlyPatternAtom.create(...)
        atoms.append(monthly_atom)
        
        # 4. Monthly-daily grid (wind)
        monthly_daily_wind = SingleMastMonthlyDailyWindAtom.create(...)
        atoms.append(monthly_daily_wind)
        
        # 5. Power patterns (if available)
        if self._has_power_data(result):
            daily_power = SingleMastDailyPowerPatternAtom.create(...)
            atoms.append(daily_power)
            
            monthly_power = SingleMastMonthlyPowerPatternAtom.create(...)
            atoms.append(monthly_power)
            
            monthly_daily_power = SingleMastMonthlyDailyPowerAtom.create(...)
            atoms.append(monthly_daily_power)
        
        return atoms
```

---

## Visualization Specifications

### Monthly Pattern (Grouped Bars)

```python
chart = alt.Chart(df).mark_bar().encode(
    x=alt.X("month:O", title="月份"),
    y=alt.Y("mean_speed:Q", title="平均风速(m/s)"),
    color=alt.Color("height:N", title="高度"),
    xOffset=alt.XOffset("height:N"),  # Grouped bars
).properties(
    title=f"月度风速分布 - {mast_name}",
    width=800,
    height=600,
)
```

### Monthly-Daily Faceted Grid

```python
chart = alt.Chart(df).mark_line().encode(
    x=alt.X("hour:O", title="小时"),
    y=alt.Y("wind_speed:Q", title="风速(m/s)"),
    color=alt.Color("height:N", title="高度"),
    facet=alt.Facet("month_name:N", columns=4),  # 4 columns
).properties(
    width=250,
    height=200,
)
```

---

## Testing Strategy

```python
class TestWindTemporalAnalyzer:
    def test_daily_pattern(self):
        """Test 24-hour aggregation."""
        
    def test_monthly_pattern(self):
        """Test monthly aggregation."""
        
    def test_monthly_daily(self):
        """Test hourly x monthly aggregation."""
        
    def test_power_calculation(self):
        """Test wind power temporal patterns."""
```

---

## Migration Checklist

- [ ] Create `TemporalPatternSchema` with dataframely
- [ ] Implement `WindTemporalAnalyzer` domain service
- [ ] Implement time series extraction
- [ ] Implement daily aggregation (24-hour)
- [ ] Implement monthly aggregation
- [ ] Implement monthly-daily faceted data
- [ ] Create all 7 atom types
- [ ] Implement line charts
- [ ] Implement grouped bar charts
- [ ] Implement faceted grids
- [ ] Create analysis → atom converter
- [ ] Write unit tests
- [ ] Write integration tests
