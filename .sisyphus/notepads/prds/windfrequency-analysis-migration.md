# PRD: WindFrequency Analysis Migration (Julia → Python)

## Overview

Migrate the Julia `WindFrequency.jl` module to Python using the Analysis → Atom pattern.

**Source**: `CleanMastProject/src/ReportTimeSeries/WindFrequency.jl` (380 lines)

---

## Analysis Purpose

Calculate wind speed frequency and wind power frequency distributions across speed bins (0-28 m/s, 1 m/s bins).

**Key Outputs**:
- Wind speed frequency by 1 m/s bins
- Wind power frequency (energy contribution) by speed bins
- Occurrence hours (8760 * frequency)
- Summary tables for 3-25 m/s range

**Use Cases**:
- Wind resource assessment
- Wind turbine siting
- Annual energy production estimation

---

## Input Requirements

```python
@dataclass
class WindFrequencyInput:
    """Input for wind frequency analysis."""
    mast_name: str
    timeseries_data: pl.DataFrame
    sensors: list[SensorColumn]  # WindSpeed avg sensors
    air_density: AirDensityConfig | None
    wind_speed_bins: range = range(0, 29, 1)  # 0-28 m/s, 1m bins
```

### Sensor Requirements

| Sensor Type | Stat Type | Purpose |
|-------------|-----------|---------|
| WindSpeed | avg | Wind speed measurements |

---

## Output Schema

### WindFrequencySchema (dataframely)

```python
class WindFrequencySchema(dy.Schema):
    """Schema for wind frequency analysis results."""
    height: dy.Float64() = dy.Field(ge=0)
    interpolation_marker: dy.String() | None
    
    # Bin definition
    bin_start: dy.Float64() = dy.Field(ge=0)
    bin_end: dy.Float64() = dy.Field(ge=0)
    bin_center: dy.Float64() = dy.Field(ge=0)
    
    # Frequency data
    frequency: dy.Float64() = dy.Field(ge=0, le=1)  # 0.0 to 1.0
    occurrence_hours: dy.Int64() = dy.Field(ge=0)   # frequency * 8760
    
    # Power frequency (only if air_density provided)
    power_frequency: dy.Float64() | None = dy.Field(ge=0, le=1)
    power_hours: dy.Int64() | None = dy.Field(ge=0)
```

---

## Atom Types Produced

### 1. SingleMastWindFrequencyTableAtom

```python
@dataclass
class SingleMastWindFrequencyTableAtom(
    ReportAtom[WindFrequencySchema, SingleMastMeta]
):
    """Wind speed frequency table (all heights)."""
    
    def renderTable(self) -> str:
        """Typst table:
        
        | 风速区间 | 100m频率 | 100m小时数 | 120m频率 | 120m小时数 | ... |
        |----------|----------|------------|----------|------------|-----|
        | 0-1      | 2.5%     | 219        | 2.3%     | 201        | ... |
        | 1-2      | 5.1%     | 447        | 4.8%     | 420        | ... |
        ...
        """
        
    def renderSummary(self) -> str:
        """Summary of most frequent wind speed ranges."""
```

### 2. SingleMastWindPowerFrequencyTableAtom

```python
@dataclass
class SingleMastWindPowerFrequencyTableAtom(
    ReportAtom[WindFrequencySchema, SingleMastMeta]
):
    """Wind power frequency table (all heights)."""
    
    def renderTable(self) -> str:
        """Typst table:
        
        | 风速区间 | 100m功率频率 | 100m功率小时数 | ... |
        |----------|--------------|----------------|-----|
        """
```

### 3. SingleMastWindFrequencyDistributionAtom

```python
@dataclass
class SingleMastWindFrequencyDistributionAtom(
    ReportAtom[WindFrequencySchema, SingleMastMeta]
):
    """Bar chart showing wind speed frequency + power frequency (one height)."""
    
    height: float
    
    def renderImage(self, output_dir: Path) -> Path:
        """Generate grouped bar chart:
        
        - X-axis: Wind Speed (m/s), bins 0-25 m/s
        - Y-axis: Frequency (0-1.0)
        - Blue bars: Wind Speed Frequency
        - Red bars: Wind Power Frequency
        - Title: "Wind Speed and Power Frequency Distribution - {mast} ({height}m)"
        """
        # Use Altair mark_bar with dodge
```

### 4. SingleMastWindRangeSummaryAtom

```python
@dataclass
class SingleMastWindRangeSummaryAtom(
    ReportAtom[WindFrequencySchema, SingleMastMeta]
):
    """Summary table for 3-25 m/s range (typical turbine operating range)."""
    
    def renderTable(self) -> str:
        """Typst table:
        
        | 高度 | 风速频率 | 风速出现小时数 | 风能频率 | 风能出现小时数 |
        |------|----------|----------------|----------|----------------|
        | 100m | 85.2%    | 7463           | 92.1%    | 8068           |
        | 120m | 87.1%    | 7630           | 93.5%    | 8191           |
        """
```

---

## Domain Service: WindFrequencyCalculator

```python
class WindFrequencyCalculator:
    """Domain service for wind frequency analysis."""
    
    HOURS_PER_YEAR: int = 8760
    DEFAULT_BINS: range = range(0, 29, 1)  # 0-28 m/s
    
    def calculate(
        self,
        input: WindFrequencyInput
    ) -> AnalysisResult[WindFrequencySchema]:
        """
        Main analysis method.
        
        For each height:
        1. Extract wind speed data
        2. Create histogram with 1 m/s bins
        3. Calculate frequency = count / total
        4. Calculate occurrence hours = frequency * 8760
        5. If air_density: calculate power for each observation
        6. If air_density: sum power in each bin
        7. If air_density: calculate power_frequency = bin_power / total_power
        """
        
    def _calculate_histogram(
        self,
        wind_speeds: pl.Series,
        bins: range
    ) -> tuple[np.ndarray, np.ndarray]:
        """Create histogram and return counts + bin edges."""
        
    def _calculate_power_frequency(
        self,
        wind_speeds: pl.Series,
        air_density: float,
        bins: range
    ) -> np.ndarray:
        """
        Calculate wind power contribution in each bin.
        
        Steps:
        1. Calculate power for each observation: P = 0.5 * ρ * v³
        2. Sum power in each bin
        3. Calculate frequency: bin_power / total_power
        """
        
    def _calculate_range_summary(
        self,
        df: pl.DataFrame,
        min_speed: float,
        max_speed: float
    ) -> dict:
        """
        Calculate summary statistics for a speed range (e.g., 3-25 m/s).
        
        Returns:
            {
                "total_wind_freq": float,
                "total_wind_hours": int,
                "total_power_freq": float,
                "total_power_hours": int,
            }
        """
```

---

## Analysis → Atom Conversion

```python
class WindFrequencyAnalysisToAtoms:
    """Converts WindFrequency AnalysisResult to ReportAtoms."""
    
    def convert(
        self,
        result: AnalysisResult[WindFrequencySchema],
        mast_name: str
    ) -> list[ReportAtom]:
        """Create atoms from analysis result."""
        atoms = []
        
        # 1. Wind speed frequency table (all heights)
        speed_table_atom = SingleMastWindFrequencyTableAtom.create(
            schema=WindFrequencySchema,
            df=result.data,
            meta=SingleMastMeta(
                mast_name=mast_name,
                caption="风速频率表"
            ),
        )
        atoms.append(speed_table_atom)
        
        # 2. Wind power frequency table (if power data present)
        if self._has_power_data(result):
            power_table_atom = SingleMastWindPowerFrequencyTableAtom.create(
                schema=WindFrequencySchema,
                df=result.data,
                meta=SingleMastMeta(
                    mast_name=mast_name,
                    caption="风功率频率表"
                ),
            )
            atoms.append(power_table_atom)
        
        # 3. Individual distribution plots (one per height)
        for height in result.data["height"].unique():
            height_data = result.data.filter(pl.col("height") == height)
            
            dist_atom = SingleMastWindFrequencyDistributionAtom.create(
                schema=WindFrequencySchema,
                df=height_data,
                meta=SingleMastMeta(
                    mast_name=mast_name,
                    caption=f"{height}m风速与风功率频率分布"
                ),
            )
            dist_atom.height = height
            atoms.append(dist_atom)
        
        # 4. 3-25 m/s range summary
        range_data = self._calculate_range_summary(result, 3, 25)
        range_atom = SingleMastWindRangeSummaryAtom.create(
            schema=WindFrequencySchema,
            df=range_data,
            meta=SingleMastMeta(
                mast_name=mast_name,
                caption="风速区间3-25m/s统计汇总"
            ),
        )
        atoms.append(range_atom)
        
        return atoms
```

---

## Visualization Specifications

### Wind Speed + Power Frequency Chart

```python
# Reshape data for grouped bar chart
plot_df = pl.DataFrame({
    "bin_center": list(bin_centers) * 2,
    "value": list(frequencies) + list(power_frequencies),
    "type": ["风速频率"]*len(bin_centers) + ["风功率频率"]*len(bin_centers),
})

# Limit x-axis to data range + 1, max 25 m/s
max_nonzero = plot_df.filter(pl.col("value") > 0)["bin_center"].max()
x_max = min(max_nonzero + 1, 25)

chart = alt.Chart(plot_df).mark_bar().encode(
    x=alt.X("bin_center:Q", title="风速(m/s)", scale=alt.Scale(domain=[0, x_max])),
    y=alt.Y("value:Q", title="频率"),
    color=alt.Color("type:N", title="类型"),
    xOffset=alt.XOffset("type:N"),  # Grouped bars
).properties(
    title=f"风速与风功率频率分布 - {mast_name} ({height}m)",
    width=600,
    height=400,
)
```

---

## Key Formulas

### Wind Power Density

```
P = 0.5 * ρ * v³
```

Where:
- `P` = wind power density (W/m²)
- `ρ` = air density (kg/m³)
- `v` = wind speed (m/s)

### Frequency

```
frequency = count_bin / total_count
```

### Occurrence Hours

```
hours = frequency * 8760  # Hours in a year
```

### Power Frequency

```
power_frequency = power_bin / total_power
```

Where `power_bin` = sum of power densities in that bin.

---

## Testing Strategy

```python
class TestWindFrequencyCalculator:
    def test_histogram_creation(self):
        """Test binning into 1 m/s intervals."""
        
    def test_frequency_calculation(self):
        """Test frequencies sum to 1.0."""
        
    def test_power_calculation(self):
        """Test power density formula."""
        # P = 0.5 * 1.225 * 10³ = 612.5 W/m² at 10 m/s
        
    def test_range_summary(self):
        """Test 3-25 m/s range filtering."""
```

---

## Migration Checklist

- [ ] Create `WindFrequencySchema` with dataframely
- [ ] Implement `WindFrequencyCalculator` domain service
- [ ] Implement histogram binning
- [ ] Implement power density calculation
- [ ] Create `SingleMastWindFrequencyTableAtom`
- [ ] Create `SingleMastWindPowerFrequencyTableAtom`
- [ ] Create `SingleMastWindFrequencyDistributionAtom`
- [ ] Create `SingleMastWindRangeSummaryAtom`
- [ ] Implement grouped bar chart visualization
- [ ] Create analysis → atom converter
- [ ] Write unit tests
- [ ] Write integration tests
