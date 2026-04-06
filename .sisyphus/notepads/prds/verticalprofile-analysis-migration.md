# PRD: Vertical Profile Analysis Migration (Julia → Python)

## Overview

Migrate the Julia `Vertical.jl` module to Python using the Analysis → Atom pattern.

**Source**: `CleanMastProject/src/ReportTimeSeries/Vertical.jl` (354 lines)

---

## Analysis Purpose

Analyze vertical wind speed profile using power law fitting:
- Fit power law exponent (α) to measured wind speeds
- Calculate wind shear between height pairs
- Create wind shear exponent tables

**Power Law Formula**:
```
v = v_ref * (h / h_ref)^α
```

Where:
- `v` = wind speed at height `h`
- `v_ref` = wind speed at reference height `h_ref`
- `α` = power law exponent (wind shear exponent)

---

## Input Requirements

```python
@dataclass
class VerticalProfileInput:
    """Input for vertical profile analysis."""
    mast_name: str
    timeseries_data: pl.DataFrame
    sensors: list[SensorColumn]  # WindSpeed avg sensors
```

### Sensor Requirements

| Sensor Type | Stat Type | Purpose |
|-------------|-----------|---------|
| WindSpeed | avg | Wind speed at multiple heights |

**Note**: Requires at least 2 sensors at different heights.

---

## Output Schema

### VerticalProfileSchema (dataframely)

```python
class VerticalProfileSchema(dy.Schema):
    """Schema for vertical profile analysis results."""
    mast_name: dy.String()
    
    # Profile data
    height: dy.Float64() = dy.Field(ge=0)
    mean_wind_speed: dy.Float64() = dy.Field(ge=0)
    
    # Power law fit
    power_law_alpha: dy.Float64()
    r_squared: dy.Float64() = dy.Field(ge=0, le=1)
    reference_height: dy.Float64()
    reference_speed: dy.Float64()
```

### WindShearSchema (for shear analysis)

```python
class WindShearSchema(dy.Schema):
    """Schema for wind shear between height pairs."""
    height_pair: dy.String()  # "80m-100m"
    lower_height: dy.Float64()
    upper_height: dy.Float64()
    mean_alpha: dy.Float64()
    std_alpha: dy.Float64()
    min_alpha: dy.Float64()
    max_alpha: dy.Float64()
    count: dy.Int64()
```

---

## Atom Types Produced

### 1. SingleMastVerticalProfileAtom

```python
@dataclass
class SingleMastVerticalProfileAtom(
    ReportAtom[VerticalProfileSchema, SingleMastMeta]
):
    """Vertical wind profile with power law fit."""
    
    def renderImage(self, output_dir: Path) -> Path:
        """Generate scatter + line plot:
        
        - X-axis: Wind Speed (m/s)
        - Y-axis: Height (m), logarithmic scale
        - Blue dots: Measured mean wind speeds
        - Red line: Power law fit
        - Title: "Vertical Wind Speed Profile (α = {alpha:.3f}, R² = {r2:.3f})"
        """
        
    def renderTable(self) -> str:
        """Typst table:
        
        | 高度(m) | 平均风速(m/s) |
        |---------|---------------|
        | 160     | 8.52          |
        | 140     | 8.31          |
        ...
        """
        
    def renderSummary(self) -> str:
        """Chinese narrative:
        "测风塔M01的垂直风切变指数为0.143，拟合优度R²=0.998，
         表明幂律模型能很好地描述风速随高度的变化。"
        """
```

### 2. SingleMastWindShearTableAtom

```python
@dataclass
class SingleMastWindShearTableAtom(
    ReportAtom[WindShearSchema, SingleMastMeta]
):
    """Wind shear analysis between consecutive height pairs."""
    
    def renderTable(self) -> str:
        """Typst table:
        
        | 高度层对 | 平均α | α标准差 | α最小值 | α最大值 | 数据点数 |
        |----------|-------|---------|---------|---------|----------|
        | 80m-100m | 0.145 | 0.032   | 0.089   | 0.201   | 8760     |
        ...
        """
```

### 3. SingleMastWindShearExponentAtom

```python
@dataclass
class SingleMastWindShearExponentAtom(
    ReportAtom[VerticalProfileSchema, SingleMastMeta]
):
    """Wind shear exponent matrix (all height pairs)."""
    
    def renderTable(self) -> str:
        """Typst matrix table:
        
        | 测风高度 | 风速 | 160m  | 140m  | 120m  | 100m  |
        |----------|------|-------|-------|-------|-------|
        | 160m     | 8.52 | ◦     | 0.123 | 0.145 | 0.167 |
        | 140m     | 8.31 | 0.123 | ◦     | 0.152 | 0.178 |
        | 120m     | 7.95 | 0.145 | 0.152 | ◦     | 0.189 |
        | 100m     | 7.52 | 0.167 | 0.178 | 0.189 | ◦     |
        
        Note: ◦ indicates same height (no shear calculated)
        """
```

---

## Domain Service: VerticalProfileAnalyzer

```python
class VerticalProfileAnalyzer:
    """Domain service for vertical wind profile analysis."""
    
    def fit_power_law(
        self,
        heights: np.ndarray,
        speeds: np.ndarray
    ) -> tuple[float, float, float]:
        """
        Fit power law using linear regression on log-transformed data.
        
        Power law: v = v_ref * (h / h_ref)^α
        
        Taking log: log(v) = log(v_ref) + α * log(h/h_ref)
                        = intercept + α * log(h)
        
        Steps:
        1. Transform: log_height = log(heights), log_speed = log(speeds)
        2. Linear regression: log_speed ~ log_height
        3. Extract: α = slope, v_ref = exp(intercept) at h_ref
        
        Returns:
            (alpha, r_squared, reference_speed)
        """
        import numpy as np
        from scipy import stats
        
        # Log transform
        log_heights = np.log(heights)
        log_speeds = np.log(speeds)
        
        # Linear regression
        slope, intercept, r_value, _, _ = stats.linregress(log_heights, log_speeds)
        
        alpha = slope
        r_squared = r_value ** 2
        
        # Reference values (tallest sensor)
        ref_idx = np.argmax(heights)
        reference_height = heights[ref_idx]
        reference_speed = speeds[ref_idx]
        
        return alpha, r_squared, reference_speed
        
    def calculate_wind_shear_per_timestamp(
        self,
        df: pl.DataFrame,
        lower_sensor: SensorColumn,
        upper_sensor: SensorColumn
    ) -> np.ndarray:
        """
        Calculate shear exponent for each timestamp.
        
        Formula: α = ln(v2/v1) / ln(h2/h1)
        
        Returns array of alpha values (filtered for v1 > 0, v2 > 0)
        """
        
    def calculate_shear_statistics(
        self,
        alphas: np.ndarray
    ) -> dict:
        """
        Calculate statistics for shear exponents.
        
        Returns:
            {
                "mean_alpha": float,
                "std_alpha": float,
                "min_alpha": float,
                "max_alpha": float,
                "count": int,
            }
        """
        
    def calculate_shear_exponent_matrix(
        self,
        heights: list[float],
        speeds: list[float]
    ) -> pl.DataFrame:
        """
        Calculate shear exponent between all height pairs.
        
        For each pair (i, j):
        α_ij = ln(v_i/v_j) / ln(h_i/h_j)
        
        Returns DataFrame with:
        - Rows: source heights
        - Columns: target heights
        - Values: α values ("◦" for same height)
        """
        
    def analyze_vertical_profile(
        self,
        input: VerticalProfileInput
    ) -> AnalysisResult[VerticalProfileSchema]:
        """
        Main analysis for vertical profile.
        
        Steps:
        1. Calculate mean wind speed at each height
        2. Fit power law
        3. Generate fitted curve
        """
        
    def analyze_wind_shear(
        self,
        input: VerticalProfileInput
    ) -> AnalysisResult[WindShearSchema]:
        """
        Main analysis for wind shear between height pairs.
        
        For each consecutive height pair:
        1. Calculate alpha for each timestamp
        2. Calculate statistics (mean, std, min, max)
        """
        
    def calculate(
        self,
        input: VerticalProfileInput
    ) -> tuple[AnalysisResult[VerticalProfileSchema], AnalysisResult[WindShearSchema]]:
        """
        Run all vertical analyses.
        
        Returns both profile and shear results.
        """
```

---

## Analysis → Atom Conversion

```python
class VerticalProfileAnalysisToAtoms:
    """Converts Vertical Profile AnalysisResult to ReportAtoms."""
    
    def convert(
        self,
        profile_result: AnalysisResult[VerticalProfileSchema],
        shear_result: AnalysisResult[WindShearSchema],
        mast_name: str
    ) -> list[ReportAtom]:
        """Create atoms from analysis results."""
        atoms = []
        
        # 1. Vertical profile plot + table
        profile_atom = SingleMastVerticalProfileAtom.create(
            schema=VerticalProfileSchema,
            df=profile_result.data,
            meta=SingleMastMeta(
                mast_name=mast_name,
                caption="垂直风廓线"
            ),
        )
        atoms.append(profile_atom)
        
        # 2. Wind shear between pairs
        shear_table_atom = SingleMastWindShearTableAtom.create(
            schema=WindShearSchema,
            df=shear_result.data,
            meta=SingleMastMeta(
                mast_name=mast_name,
                caption="风切变分析"
            ),
        )
        atoms.append(shear_table_atom)
        
        # 3. Shear exponent matrix
        matrix_data = self._create_shear_matrix(shear_result)
        matrix_atom = SingleMastWindShearExponentAtom.create(
            schema=VerticalProfileSchema,
            df=matrix_data,
            meta=SingleMastMeta(
                mast_name=mast_name,
                caption="风切变指数表"
            ),
        )
        atoms.append(matrix_atom)
        
        return atoms
```

---

## Visualization Specifications

### Vertical Profile Plot

```python
# Measured points
points = alt.Chart(df).mark_point(color="blue", size=100).encode(
    x=alt.X("mean_wind_speed:Q", title="风速(m/s)"),
    y=alt.Y("height:Q", title="高度(m)", scale=alt.Scale(type="log")),
)

# Power law fit line
line = alt.Chart(fit_df).mark_line(color="red", strokeWidth=3).encode(
    x="fitted_speed:Q",
    y="height:Q",
)

chart = (points + line).properties(
    title=f"垂直风速剖面 - {mast_name} (α={alpha:.3f}, R²={r2:.3f})",
    width=600,
    height=500,
)
```

---

## Key Formulas

### Power Law

```
v = v_ref * (h / h_ref)^α
```

### Wind Shear Exponent (from time series)

```
α = ln(v2/v1) / ln(h2/h1)
```

### Log-Linear Regression

```
log(v) = intercept + α * log(h)
```

Where:
- `α` = slope of log-log regression
- `exp(intercept)` = speed at h=1m (extrapolated)

---

## Typical Alpha Values

| Terrain Type | Alpha Range |
|--------------|-------------|
| Smooth (water, ice) | 0.10 - 0.12 |
| Open (grassland) | 0.12 - 0.16 |
| Rough (suburban) | 0.16 - 0.25 |
| Very rough (urban, forest) | 0.25 - 0.40 |

---

## Testing Strategy

```python
class TestVerticalProfileAnalyzer:
    def test_power_law_fit(self):
        """Test power law fitting on known data."""
        # Create synthetic data with known alpha
        # Fit
        # Assert alpha close to expected
        
    def test_shear_calculation(self):
        """Test shear exponent calculation."""
        # h1=100, v1=8
        # h2=120, v2=8.5
        # α = ln(8.5/8) / ln(120/100) = 0.304
        
    def test_shear_matrix(self):
        """Test shear exponent matrix."""
        # Ensure diagonal is "◦"
        # Ensure α_ij = -α_ji (approximately)
```

---

## Migration Checklist

- [ ] Create `VerticalProfileSchema` and `WindShearSchema`
- [ ] Implement `VerticalProfileAnalyzer` domain service
- [ ] Implement power law fitting with log-linear regression
- [ ] Implement per-timestamp shear calculation
- [ ] Implement shear exponent matrix
- [ ] Create `SingleMastVerticalProfileAtom`
- [ ] Create `SingleMastWindShearTableAtom`
- [ ] Create `SingleMastWindShearExponentAtom`
- [ ] Implement scatter + line visualization
- [ ] Create analysis → atom converter
- [ ] Write unit tests
- [ ] Write integration tests
