# PRD: Weibull Analysis Migration (Julia → Python)

## Overview

Migrate the Julia `Weibull.jl` module to Python using the Analysis → Atom pattern.

**Source**: `CleanMastProject/src/ReportTimeSeries/Weibull.jl` (337 lines)

---

## Analysis Purpose

Fit Weibull distributions to wind speed data at each height to characterize the wind speed probability distribution.

**Use Cases**:
- Wind resource assessment
- Wind turbine power curve analysis
- Annual energy production (AEP) estimation

---

## Input Requirements

```python
@dataclass
class WeibullInput:
    """Input for Weibull distribution fitting."""
    mast_name: str
    timeseries_data: pl.DataFrame
    sensors: list[SensorColumn]  # WindSpeed sensors with statType="avg"
    heights_to_analyze: list[float]  # All available heights
```

### Sensor Requirements

| Sensor Type | Stat Type | Purpose |
|-------------|-----------|---------|
| WindSpeed | avg | Wind speed measurements for fitting |

**Note**: Only sensors with at least 10 valid data points are analyzed.

---

## Output Schema

### WeibullSchema (dataframely)

```python
class WeibullSchema(dy.Schema):
    """Schema for Weibull distribution fitting results."""
    height: dy.Float64() = dy.Field(ge=0)
    interpolation_marker: dy.String() | None
    
    # Weibull parameters
    shape_k: dy.Float64() = dy.Field(ge=0)  # Shape parameter (dimensionless)
    scale_c: dy.Float64() = dy.Field(ge=0)  # Scale parameter (m/s)
    
    # Statistics
    mean_speed: dy.Float64() = dy.Field(ge=0)
    min_speed: dy.Float64() = dy.Field(ge=0)
    max_speed: dy.Float64() = dy.Field(ge=0)
    
    # Histogram data (for plotting)
    bin_centers: dy.List(dy.Float64())  # Speed values at bin centers
    observed_density: dy.List(dy.Float64())  # Normalized histogram
    fitted_density: dy.List(dy.Float64())   # Weibull PDF at bin centers
```

---

## Atom Types Produced

### 1. SingleMastWeibullParametersAtom

```python
@dataclass
class SingleMastWeibullParametersAtom(
    ReportAtom[WeibullSchema, SingleMastMeta]
):
    """Table of Weibull parameters for all heights."""
    
    def renderTable(self) -> str:
        """Typst table:
        
        | 高度(m) | 形状参数(k) | 尺度参数(c) |
        |---------|-------------|-------------|
        | 160m    | 2.15        | 8.52        |
        | 140m    | 2.08        | 8.31        |
        ...
        """
        
    def renderImage(self, output_dir: Path) -> Path:
        """No standalone image - parameters are tabular data."""
        return output_dir / f"weibull_params_{self.meta.mast_name}.png"
        
    def renderSummary(self) -> str:
        """Chinese narrative:
        "测风塔M01各高度Weibull分布拟合结果显示，
         形状参数k在2.0-2.2之间，表明风速分布接近瑞利分布。"
        """
```

### 2. SingleMastWeibullDistributionAtom

```python
@dataclass
class SingleMastWeibullDistributionAtom(
    ReportAtom[WeibullSchema, SingleMastMeta]
):
    """Histogram + fitted Weibull PDF for one height."""
    
    height: float  # Specific height for this chart
    
    def renderImage(self, output_dir: Path) -> Path:
        """Generate histogram with fitted Weibull overlay.
        
        Chart spec:
        - X-axis: Wind Speed (m/s), bins 1 m/s wide
        - Y-axis: Probability Density
        - Blue bars: Observed histogram (normalized)
        - Red line: Fitted Weibull PDF
        - Title: "Wind Speed Distribution at {height}m\nWeibull: k={k:.2f}, c={c:.2f} m/s"
        """
        # Use Altair: mark_bar for histogram, mark_line for PDF
        
    def renderTable(self) -> str:
        """Typst table for this height's bin data."""
        
    def renderSummary(self) -> str:
        """Height-specific summary."""
```

### 3. SingleMastWeibullMultiHeightAtom (NEW)

```python
@dataclass
class SingleMastWeibullMultiHeightAtom(
    ReportAtom[WeibullSchema, SingleMastMeta]
):
    """Combined plot showing Weibull distributions for all heights >= 100m."""
    
    def renderImage(self, output_dir: Path) -> Path:
        """Multi-line chart:
        
        - X-axis: Wind Speed (m/s)
        - Y-axis: Probability Density
        - Each line = one height (>=100m)
        - Legend showing height labels
        """
```

---

## Domain Service: WeibullFitter

```python
class WeibullFitter:
    """Domain service for Weibull distribution fitting."""
    
    MIN_DATA_POINTS: int = 10
    BIN_WIDTH: float = 1.0  # m/s
    
    def fit(
        self, 
        wind_speeds: pl.Series
    ) -> tuple[float, float] | None:
        """
        Fit Weibull distribution using Maximum Likelihood Estimation (MLE).
        
        Algorithm:
        1. Filter out missing values and non-positive values
        2. If < 10 points: return None (insufficient data)
        3. Initial guess: k=2.0, c=mean/gamma(1+1/k)
        4. Optimize negative log-likelihood using LBFGS
        5. If optimization fails: fallback to Method of Moments
        
        Returns:
            (shape_k, scale_c) or None if fitting fails
        """
        
    def _neg_log_likelihood(
        self, 
        params: np.ndarray,
        data: np.ndarray
    ) -> float:
        """Negative log-likelihood for Weibull distribution.
        
        Formula:
        -n*log(k) + n*k*log(c) - k*sum(log(x)) + sum(x^k)/c^k
        """
        
    def _method_of_moments(
        self, 
        data: np.ndarray
    ) -> tuple[float, float]:
        """Fallback method when MLE fails.
        
        Uses coefficient of variation approximation.
        """
        mean_val = np.mean(data)
        std_val = np.std(data)
        coef_var = std_val / mean_val
        
        k = (0.9874 / coef_var) ** 1.0983  # Approximation
        c = mean_val / gamma(1 + 1/k)
        
        return k, c
        
    def calculate_pdf(
        self,
        k: float,
        c: float,
        x: np.ndarray
    ) -> np.ndarray:
        """Calculate Weibull PDF at given points."""
        # pdf = (k/c) * (x/c)^(k-1) * exp(-(x/c)^k)
        from scipy.stats import weibull_min
        return weibull_min.pdf(x, k, scale=c)
        
    def calculate_histogram(
        self,
        wind_speeds: pl.Series,
        bin_width: float = 1.0
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Create normalized histogram.
        
        Returns:
            (bin_centers, bin_density)
        """
        
    def calculate(
        self,
        input: WeibullInput
    ) -> AnalysisResult[WeibullSchema]:
        """
        Main analysis method.
        
        For each height:
        1. Extract wind speed data
        2. Fit Weibull distribution
        3. Create histogram
        4. Calculate fitted PDF at bin centers
        5. Compile results
        """
```

---

## Analysis → Atom Conversion

```python
class WeibullAnalysisToAtoms:
    """Converts Weibull AnalysisResult to ReportAtoms."""
    
    def convert(
        self,
        result: AnalysisResult[WeibullSchema],
        mast_name: str
    ) -> list[ReportAtom]:
        """Create atoms from analysis result.
        
        Returns:
        - SingleMastWeibullParametersAtom (summary table)
        - SingleMastWeibullDistributionAtom (one per height)
        - SingleMastWeibullMultiHeightAtom (combined view)
        """
        atoms = []
        
        # 1. Parameters table atom (all heights in one table)
        params_atom = SingleMastWeibullParametersAtom.create(
            schema=WeibullSchema,
            df=result.data.select(["height", "shape_k", "scale_c", "mean_speed"]),
            meta=SingleMastMeta(
                mast_name=mast_name,
                caption="Weibull分布参数"
            ),
        )
        atoms.append(params_atom)
        
        # 2. Individual distribution plots (one per height)
        for height in result.data["height"].unique():
            height_data = result.data.filter(pl.col("height") == height)
            
            dist_atom = SingleMastWeibullDistributionAtom.create(
                schema=WeibullSchema,
                df=height_data,
                meta=SingleMastMeta(
                    mast_name=mast_name,
                    caption=f"{height}m高度风速分布"
                ),
            )
            dist_atom.height = height
            atoms.append(dist_atom)
        
        # 3. Multi-height combined plot (heights >= 100m)
        high_height_data = result.data.filter(pl.col("height") >= 100)
        if high_height_data.height > 0:
            multi_atom = SingleMastWeibullMultiHeightAtom.create(
                schema=WeibullSchema,
                df=result.data,
                meta=SingleMastMeta(
                    mast_name=mast_name,
                    caption="各高度风速分布对比"
                ),
            )
            atoms.append(multi_atom)
        
        return atoms
```

---

## Visualization Specifications

### Individual Height Plot (Altair)

```python
# Histogram data
hist_df = pl.DataFrame({
    "speed": bin_centers,
    "observed": hist_density,
})

# Fitted PDF
fit_df = pl.DataFrame({
    "speed": x_range,
    "fitted": weibull_pdf,
})

# Layered chart
hist_layer = alt.Chart(hist_df).mark_bar(opacity=0.7, color="steelblue").encode(
    x=alt.X("speed", title="Wind Speed (m/s)"),
    y=alt.Y("observed", title="Probability Density"),
)

fit_layer = alt.Chart(fit_df).mark_line(color="red", strokeWidth=2).encode(
    x="speed",
    y="fitted",
)

chart = (hist_layer + fit_layer).properties(
    title=f"Wind Speed Distribution at {height}m\nWeibull: k={k:.2f}, c={c:.2f} m/s",
    width=600,
    height=400,
)
```

### Multi-Height Plot

```python
# Filter to heights >= 100m, sort descending
heights = sorted([h for h in df["height"].unique() if h >= 100], reverse=True)

# Create line for each height
lines = []
for i, height in enumerate(heights):
    height_df = df.filter(pl.col("height") == height)
    line = alt.Chart(height_df).mark_line(strokeWidth=2).encode(
        x="speed",
        y="fitted_density",
        color=alt.ColorValue(colors[i]),
    )
    lines.append(line)

combined = alt.layer(*lines).properties(
    title=f"Wind Speed Distributions - {mast_name}",
    width=800,
    height=600,
)
```

---

## Report Sections (Future)

```python
@dataclass
class WeibullSection:
    """Section for Weibull distribution analysis."""
    atoms: AtomCollection
    title: str = "Weibull分布拟合"
    level: int = 1
    
    def render(self, images_dir: Path) -> str:
        """Render order:
        1. Weibull parameters table (all heights)
        2. Individual distribution plots (per height)
        3. Multi-height combined plot (if multiple heights >=100m)
        """
```

---

## Testing Strategy

### Unit Tests

```python
class TestWeibullFitter:
    def test_mle_fitting(self):
        """Test MLE fitting on known data."""
        # Generate known Weibull data
        # Fit
        # Assert k, c close to expected
        
    def test_method_of_moments_fallback(self):
        """Test MoM when MLE fails."""
        
    def test_insufficient_data(self):
        """Test handling of < 10 data points."""
        
    def test_pdf_calculation(self):
        """Test Weibull PDF calculation."""
        # scipy.stats.weibull_min should match our implementation
```

### Integration Tests

```python
class TestWeibullAtoms:
    def test_parameters_atom(self):
        """Test parameter table generation."""
        
    def test_distribution_atom(self, tmp_path):
        """Test chart rendering."""
        
    def test_multi_height_atom(self):
        """Test combined plot."""
```

---

## Dependencies

```toml
[tool.poetry.dependencies]
scipy = "^1.11"          # Weibull fitting, optimization
altair = "^5.0"
numpy = "^1.24"
```

### Julia → Python Mapping

| Julia | Python |
|-------|--------|
| Distributions.Weibull | scipy.stats.weibull_min |
| Optim.LBFGS | scipy.optimize.minimize |
| fit(Histogram) | numpy.histogram |
| gamma (Γ) | scipy.special.gamma |
| AlgebraOfGraphics | Altair |

---

## Key Formulas

### Weibull PDF

```
f(x; k, c) = (k/c) * (x/c)^(k-1) * exp(-(x/c)^k)
```

Where:
- `k` = shape parameter (dimensionless)
- `c` = scale parameter (same units as x, i.e., m/s)
- `x` = wind speed

### Log-Likelihood

```
L(k, c) = n*log(k) - n*k*log(c) + (k-1)*sum(log(x)) - sum((x/c)^k)
```

We minimize the negative log-likelihood.

### Method of Moments

```
k ≈ (0.9874 / CV)^1.0983  where CV = σ/μ
c = μ / Γ(1 + 1/k)
```

---

## Migration Checklist

- [ ] Create `WeibullSchema` with dataframely
- [ ] Implement `WeibullFitter` domain service
- [ ] Implement MLE fitting with scipy.optimize
- [ ] Implement Method of Moments fallback
- [ ] Create `SingleMastWeibullParametersAtom`
- [ ] Create `SingleMastWeibullDistributionAtom`
- [ ] Create `SingleMastWeibullMultiHeightAtom`
- [ ] Implement histogram + PDF overlay charts
- [ ] Create analysis → atom converter
- [ ] Write unit tests for fitting algorithms
- [ ] Write integration tests for atoms
- [ ] Document key formulas and assumptions
