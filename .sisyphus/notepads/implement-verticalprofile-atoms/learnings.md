## LEARNINGS: VerticalProfile Atoms Implementation

### Key Formulas

#### Power Law
```
v = v_ref * (h / h_ref)^α
```

#### Log-Linear Regression (for fitting α)
```
log(v) = intercept + α * log(h)
```
Use scipy.stats.linregress

#### Wind Shear (per timestamp)
```
α = ln(v2/v1) / ln(h2/h1)
```

#### Shear Matrix
```
α_ij = ln(v_i/v_j) / ln(h_i/h_j)
```

### Typical Alpha Values
- Smooth (water): 0.10-0.12
- Open (grassland): 0.12-0.16
- Rough (suburban): 0.16-0.25
- Very rough (urban): 0.25-0.40

### Chart Pattern (Log-Log)
- X-axis: log(height)
- Y-axis: log(wind_speed)
- Scatter: measured data points
- Line: power law fit
- Title shows α and R²

### Matrix Table Pattern
- Rows: from height
- Columns: to height
- Diagonal: "◦" (no shear)
- Values: symmetric (α_ij = -α_ji)
