# PRD: Turbulence Analysis Migration (Julia → Python)

## Overview

Migrate the Julia `Turbulence.jl` module to Python using the Analysis → Atom pattern.

**Source**: `CleanMastProject/src/ReportTimeSeries/Turbulence.jl` (835 lines)

---

## Analysis Purpose

Calculate turbulence intensity (TI) statistics for wind resource assessment and IEC 61400-1 compliance.

**Key Outputs**:
- Turbulence intensity by wind speed bin
- Sector-wise turbulence statistics
- IEC turbulence category classification (A, B, C, A+)
- Meteodyn WT format export (for wind modeling software)

---

## Input Requirements

```python
@dataclass
class TurbulenceInput:
    """Input for turbulence intensity analysis."""
    mast_name: str
    timeseries_data: pl.DataFrame
    sensors: list[SensorColumn]
    target_heights: list[float]  # Heights to analyze
    wind_speed_bins: list[float]  # Default: 0:1:28 m/s
```

### Sensor Requirements

| Sensor Type | Stat Type | Purpose |
|-------------|-----------|---------|
| WindSpeed | avg | Mean wind speed |
| WindSpeed | sd | Standard deviation (for TI calculation) |
| WindDirection | avg | Direction for sector analysis |

**Note**: Both `avg` and `sd` stat types required for same height.

---

## Output Schema

### TurbulenceSchema (dataframely)

```python
class TurbulenceSchema(dy.Schema):
    """Schema for turbulence intensity results."""
    # Wind speed bin
    wind_speed_min: dy.Float64() = dy.Field(ge=0)
    wind_speed_max: dy.Float64() = dy.Field(ge=0)
    wind_speed_center: dy.Float64() = dy.Field(ge=0)
    
    # Height
    height: dy.Float64() = dy.Field(ge=0)
    
    # Turbulence statistics
    mean_ti: dy.Float64() = dy.Field(ge=0, le=1)
    std_ti: dy.Float64() = dy.Field(ge=0, le=1)
    representative_ti: dy.Float64() = dy.Field(ge=0, le=1)  # P90 = mean + 1.28*std
    occurrence: dy.Int64() = dy.Field(ge=0)
    
    # IEC category
    iec_category: dy.String()  # "A+", "A", "B", "C"
```

### TurbulenceSectorSchema (for sector-wise analysis)

```python
class TurbulenceSectorSchema(dy.Schema):
    """Schema for sector-wise turbulence statistics."""
    sector: dy.String()  # N, NNE, NE, ...
    height: dy.Float64()
    
    mean_speed: dy.Float64()
    mean_ti: dy.Float64()
    ti_std: dy.Float64()
    occurrence: dy.Int64()
```

---

## Atom Types Produced

### 1. SingleMastTurbulenceIntensityAtom

```python
@dataclass
class SingleMastTurbulenceIntensityAtom(
    ReportAtom[TurbulenceSchema, SingleMastMeta]
):
    """Turbulence intensity by wind speed bin (one height)."""
    
    height: float
    
    def renderImage(self, output_dir: Path) -> Path:
        """Generate TI vs Wind Speed chart with IEC bands.
        
        Chart spec:
        - X-axis: Wind Speed (m/s)
        - Y-axis: Turbulence Intensity (0-1.0)
        - Red line: Representative TI (P90)
        - Blue band: IEC Category A (I_ref=0.16)
        - Green band: IEC Category B (I_ref=0.14)
        - Yellow band: IEC Category C (I_ref=0.12)
        """
        
    def renderTable(self) -> str:
        """Typst table:
        
        | 风速区间 | 平均TI | TI标准差 | 代表TI(P90) | IEC类别 | 数据点数 |
        """
        
    def renderSummary(self) -> str:
        """Chinese narrative with IEC classification."""
```

### 2. SingleMastTurbulenceSectorAtom

```python
@dataclass
class SingleMastTurbulenceSectorAtom(
    ReportAtom[TurbulenceSectorSchema, SingleMastMeta]
):
    """Sector-wise turbulence statistics (one height)."""
    
    height: float
    
    def renderImage(self, output_dir: Path) -> Path:
        """Polar chart showing TI by direction sector."""
        
    def renderTable(self) -> str:
        """Typst table:
        
        | 风向扇区 | 平均风速 | 平均TI | TI标准差 | 数据点数 |
        """
```

### 3. SingleMastTurbulenceMultiHeightAtom

```python
@dataclass
class SingleMastTurbulenceMultiHeightAtom(
    ReportAtom[TurbulenceSchema, SingleMastMeta]
):
    """Combined TI plot for all heights >= 100m with IEC comparison."""
    
    def renderImage(self, output_dir: Path) -> Path:
        """Generate combined plot:
        
        - X-axis: Wind Speed (m/s), 0-30 m/s
        - Y-axis: Turbulence Intensity, 0-1.0
        - Filled bands: IEC A, B, C categories
        - Lines: Representative TI for each height (>=100m)
        - Legend: Height labels
        
        Size: 800x600 pixels
        """
```

### 4. SingleMastTurbulenceSummaryAtom

```python
@dataclass
class SingleMastTurbulenceSummaryAtom(
    ReportAtom[TurbulenceSchema, SingleMastMeta]
):
    """Summary table across all heights and wind speed ranges."""
    
    def renderTable(self) -> str:
        """Typst table showing:
        
        | 高度(m) | 风速范围 | 平均TI | 代表TI(P90) | TI标准差 |
        |---------|----------|--------|-------------|----------|
        | 120     | 全风速   | 0.12   | 0.18        | 0.05     |
        | 120     | >3 m/s  | 0.11   | 0.16        | 0.04     |
        | 120     | 14.5-16.5| 0.10   | 0.14        | 0.03     |
        | 120     | 9.5-10.5 | 0.11   | 0.15        | 0.04     |
        ...
        """
```

---

## Domain Service: TurbulenceCalculator

```python
class TurbulenceCalculator:
    """Domain service for turbulence intensity analysis."""
    
    # IEC 61400-1 reference turbulence intensities
    IEC_CATEGORIES: dict[str, float] = {
        "A": 0.16,  # High turbulence
        "B": 0.14,  # Medium turbulence
        "C": 0.12,  # Low turbulence
    }
    
    DEFAULT_WIND_SPEED_BINS: list[float] = list(range(0, 29, 1))  # 0-28 m/s
    
    def calculate_ti_series(
        self,
        df: pl.DataFrame,
        ws_col: str,      # Wind speed avg column
        sd_col: str,      # Wind speed std dev column
        wd_col: str,      # Wind direction column
    ) -> pl.DataFrame:
        """
        Calculate TI time series.
        
        Formula: TI = σ / max(μ, 1.0)
        Where:
        - σ = wind speed standard deviation
        - μ = mean wind speed
        - min denominator = 1.0 m/s (to avoid division by zero)
        
        Returns DataFrame with columns:
        - ws_avg, ws_sd, wd, ti, sector
        """
        
    def calculate_iec_ti(
        self,
        wind_speed: float,
        i_ref: float
    ) -> float:
        """
        Calculate IEC reference turbulence intensity.
        
        Formula: TI = I_ref * (0.75 + 5.6/V)
        Where V = wind speed in m/s
        """
        if wind_speed <= 0:
            return 0.0
        return i_ref * (0.75 + 5.6 / wind_speed)
        
    def get_iec_category(
        self,
        representative_ti: float,
        wind_speed: float
    ) -> str:
        """
        Determine IEC turbulence category.
        
        Compares representative TI to IEC curves:
        - A+: TI > TI_A
        - A:  TI_B < TI ≤ TI_A
        - B:  TI_C < TI ≤ TI_B
        - C:  TI ≤ TI_C
        """
        ti_a = self.calculate_iec_ti(wind_speed, self.IEC_CATEGORIES["A"])
        ti_b = self.calculate_iec_ti(wind_speed, self.IEC_CATEGORIES["B"])
        ti_c = self.calculate_iec_ti(wind_speed, self.IEC_CATEGORIES["C"])
        
        if representative_ti > ti_a:
            return "A+"
        elif representative_ti > ti_b:
            return "A"
        elif representative_ti > ti_c:
            return "B"
        else:
            return "C"
            
    def calculate_by_wind_speed(
        self,
        ti_df: pl.DataFrame,
        wind_speed_bins: list[float]
    ) -> pl.DataFrame:
        """
        Calculate TI statistics for each wind speed bin.
        
        For each bin [min, max):
        - Filter data where min ≤ ws_avg < max
        - Calculate mean TI, std TI
        - Calculate representative TI (P90) = mean + 1.28*std
        - Determine IEC category using bin center speed
        """
        
    def calculate_by_sector(
        self,
        ti_df: pl.DataFrame
    ) -> pl.DataFrame:
        """
        Calculate TI statistics by direction sector.
        
        Groups by 16 sectors (N, NNE, NE, ...)
        """
        
    def calculate(
        self,
        input: TurbulenceInput
    ) -> AnalysisResult[TurbulenceSchema]:
        """
        Main analysis method.
        
        For each target height:
        1. Find wind speed avg and sd sensors
        2. Find matching direction sensor
        3. Calculate TI time series
        4. Calculate statistics by wind speed bin
        5. Calculate statistics by sector
        6. Determine IEC categories
        """
```

---

## Analysis → Atom Conversion

```python
class TurbulenceAnalysisToAtoms:
    """Converts Turbulence AnalysisResult to ReportAtoms."""
    
    def convert(
        self,
        result: AnalysisResult[TurbulenceSchema],
        mast_name: str
    ) -> list[ReportAtom]:
        """Create atoms from analysis result."""
        atoms = []
        
        heights = result.data["height"].unique()
        
        for height in heights:
            height_data = result.data.filter(pl.col("height") == height)
            
            # 1. TI by wind speed (with IEC bands)
            ti_ws_atom = SingleMastTurbulenceIntensityAtom.create(
                schema=TurbulenceSchema,
                df=height_data,
                meta=SingleMastMeta(
                    mast_name=mast_name,
                    caption=f"{height}m湍流强度分析"
                ),
            )
            ti_ws_atom.height = height
            atoms.append(ti_ws_atom)
            
            # 2. Sector-wise analysis
            sector_data = self._get_sector_data(result, height)
            sector_atom = SingleMastTurbulenceSectorAtom.create(
                schema=TurbulenceSectorSchema,
                df=sector_data,
                meta=SingleMastMeta(
                    mast_name=mast_name,
                    caption=f"{height}m各扇区湍流强度"
                ),
            )
            sector_atom.height = height
            atoms.append(sector_atom)
        
        # 3. Multi-height combined plot (heights >= 100m)
        high_data = result.data.filter(pl.col("height") >= 100)
        if len(high_data) > 0:
            multi_atom = SingleMastTurbulenceMultiHeightAtom.create(
                schema=TurbulenceSchema,
                df=result.data,
                meta=SingleMastMeta(
                    mast_name=mast_name,
                    caption="各高度湍流强度与IEC标准对比"
                ),
            )
            atoms.append(multi_atom)
        
        # 4. Summary table (all heights, all wind speed ranges)
        summary_data = self._create_summary_data(result)
        summary_atom = SingleMastTurbulenceSummaryAtom.create(
            schema=TurbulenceSchema,
            df=summary_data,
            meta=SingleMastMeta(
                mast_name=mast_name,
                caption="湍流强度汇总统计"
            ),
        )
        atoms.append(summary_atom)
        
        return atoms
```

---

## Visualization Specifications

### TI vs Wind Speed with IEC Bands

```python
# IEC band data
wind_speeds = np.arange(1.0, 30.0, 0.1)
ti_a = [calc_iec_ti(ws, 0.16) for ws in wind_speeds]
ti_b = [calc_iec_ti(ws, 0.14) for ws in wind_speeds]
ti_c = [calc_iec_ti(ws, 0.12) for ws in wind_speeds]

# Create bands
iec_band_data = pl.DataFrame({
    "wind_speed": list(wind_speeds) * 3,
    "lower": ti_b + ti_c + [0.0]*len(wind_speeds),
    "upper": ti_a + ti_b + ti_c,
    "category": ["A"]*len(wind_speeds) + ["B"]*len(wind_speeds) + ["C"]*len(wind_speeds),
})

# Measurement data
meas_data = result.data.select(["wind_speed_center", "representative_ti", "height"])

# Altair chart
iec_bands = alt.Chart(iec_band_data).mark_area(opacity=0.3).encode(
    x="wind_speed:Q",
    y="lower:Q",
    y2="upper:Q",
    color="category:N",
)

meas_lines = alt.Chart(meas_data).mark_line(strokeWidth=2).encode(
    x="wind_speed_center:Q",
    y="representative_ti:Q",
    color="height:N",
)

chart = (iec_bands + meas_lines).properties(
    width=800,
    height=600,
    title=f"Turbulence Intensity - {mast_name}",
)
```

---

## Key Formulas

### Turbulence Intensity

```
TI = σ / max(μ, 1.0)
```

Where:
- `σ` = standard deviation of wind speed (m/s)
- `μ` = mean wind speed (m/s)
- Min denominator = 1.0 m/s to avoid division by zero

### Representative Turbulence Intensity (P90)

```
TI_rep = mean(TI) + 1.28 * std(TI)
```

Assumes normal distribution; 90th percentile.

### IEC Reference TI

```
TI_IEC = I_ref * (0.75 + 5.6/V)
```

Where:
- `I_ref` = reference turbulence intensity (0.16, 0.14, or 0.12)
- `V` = wind speed (m/s)

---

## Testing Strategy

```python
class TestTurbulenceCalculator:
    def test_ti_calculation(self):
        """Test TI formula."""
        # σ=2, μ=10 => TI=0.2
        
    def test_iec_ti(self):
        """Test IEC TI formula."""
        # At V=10 m/s, I_ref=0.16:
        # TI = 0.16 * (0.75 + 5.6/10) = 0.16 * 1.31 = 0.2096
        
    def test_iec_category(self):
        """Test IEC category determination."""
        # TI > TI_A => A+
        # TI_B < TI ≤ TI_A => A
        
    def test_representative_ti(self):
        """Test P90 calculation."""
        # mean + 1.28*std
```

---

## Migration Checklist

- [ ] Create `TurbulenceSchema` and `TurbulenceSectorSchema`
- [ ] Implement `TurbulenceCalculator` domain service
- [ ] Implement TI calculation formula
- [ ] Implement IEC category classification
- [ ] Implement wind speed binning logic
- [ ] Create `SingleMastTurbulenceIntensityAtom`
- [ ] Create `SingleMastTurbulenceSectorAtom`
- [ ] Create `SingleMastTurbulenceMultiHeightAtom`
- [ ] Create `SingleMastTurbulenceSummaryAtom`
- [ ] Implement IEC band visualization
- [ ] Create analysis → atom converter
- [ ] Write unit tests
- [ ] Write integration tests
