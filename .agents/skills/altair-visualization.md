# Skill: Altair Visualization for CleanMast Reports

## Overview

Use Altair for declarative statistical visualizations in CleanMast Python report generation. Altair provides a grammar-of-graphics approach that is ideal for wind energy data analysis and can be exported to PNG via `vl-convert`.

## When to Use

- ✅ Report generation with statistical charts
- ✅ Multi-series line charts (wind speed by height)
- ✅ Polar charts (wind roses)
- ✅ Faceted subplots (multi-height comparisons)
- ❌ Complex 3D visualizations (use matplotlib instead)
- ❌ Real-time interactive dashboards (use Plotly instead)

## Core Principles

### 1. Declarative Grammar

```python
# ❌ Wrong: Imperative matplotlib
fig, ax = plt.subplots()
for height in heights:
    ax.plot(df['month'], df[f'ws_{height}m'])

# ✅ Right: Declarative Altair
import altair as alt

chart = alt.Chart(df).mark_line().encode(
    x='month:O',
    y='wind_speed:Q',
    color='height:N'
)
```

### 2. Long-Format Data

Altair requires tidy (long-format) data:

```python
# ❌ Wide format - doesn't work well
# month | ws_100m | ws_125m

# ✅ Long format - correct
# month | height | wind_speed
```

### 3. Chinese Text Support

```python
chart = alt.Chart(df).mark_line().encode(
    x=alt.X('month:O', title='月份'),
    y=alt.Y('wind_speed:Q', title='风速(m/s)'),
).configure_title(
    font='Source Han Serif SC'
).configure_axis(
    labelFont='Source Han Serif SC',
    titleFont='Source Han Serif SC'
)
```

## Common Patterns

### Multi-Height Line Chart

```python
chart = alt.Chart(df).mark_line(strokeWidth=2).encode(
    x=alt.X('month:O', title='月份'),
    y=alt.Y('wind_speed:Q', title='风速(m/s)'),
    color=alt.Color(
        'height:N',
        title='高度',
        legend=alt.Legend(labelExpr="datum.label + 'm'")
    ),
    tooltip=['month', 'height', 'wind_speed']
).properties(
    title='月平均风速',
    width=600,
    height=400
)

# Export
import vl_convert as vlc
vlc.vegalite_to_png(chart.to_dict(), scale=2.0, output_file='monthly_wind.png')
```

### Wind Rose (Polar Polyline)

Use polyline (line mark) instead of bar for wind roses to show distribution shape:

```python
chart = alt.Chart(df).mark_line().encode(
    theta=alt.Theta('sector:O', sort=None, title='方向'),
    radius=alt.Radius('frequency:Q', title='频率'),
    color=alt.Color('month:N', title='月份')
).properties(
    title='风向频率玫瑰图',
    width=400,
    height=400
)
```

### Faceted Subplots

```python
chart = alt.Chart(df).mark_line().encode(
    x='month:O',
    y='wind_power_density:Q',
    color='month:N'
).facet(
    column=alt.Column('height:N', title='高度')
).properties(
    title='各高度风功率密度'
)
```

## Export Options

### PNG Export (Recommended)

```python
import vl_convert as vlc

# High-resolution PNG
vlc.vegalite_to_png(
    chart.to_dict(),
    scale=2.0,  # 2x for high DPI
    output_file='chart.png'
)

# Get bytes for testing
png_bytes = vlc.vegalite_to_png(chart.to_dict(), scale=2.0)
```

## Best Practices

1. **Data Format**: Always use long-format data with explicit type annotations (`:O` for ordinal, `:Q` for quantitative, `:N` for nominal)

2. **Fonts**: Set Chinese-compatible fonts for all text elements

3. **Tooltips**: Always add tooltips for better data exploration

4. **Scaling**: Use `scale=2.0` in vl-convert for publication-quality images

5. **Faceting**: Use `facet()` instead of manual subplot creation

6. **Color**: Use meaningful color schemes and always include legends

## Example: Complete Report Atom

```python
import altair as alt
import vl_convert as vlc
import polars as pl
from pathlib import Path

def render_monthly_wind_chart(df: pl.DataFrame, output_path: Path) -> Path:
    """Render multi-height monthly wind speed chart."""
    
    chart = alt.Chart(df).mark_line(strokeWidth=2).encode(
        x=alt.X('month:O', title='月份'),
        y=alt.Y('wind_speed_mean:Q', title='平均风速(m/s)'),
        color=alt.Color(
            'height_display:N',
            title='高度',
            legend=alt.Legend(orient='right')
        ),
        tooltip=['month', 'height_display', 'wind_speed_mean']
    ).properties(
        title=f'月平均风速',
        width=600,
        height=400
    ).configure_title(
        font='Source Han Serif SC'
    ).configure_axis(
        labelFont='Source Han Serif SC',
        titleFont='Source Han Serif SC'
    )
    
    # Export
    vlc.vegalite_to_png(
        chart.to_dict(),
        scale=2.0,
        output_file=str(output_path)
    )
    
    return output_path
```

## Checklist

- [ ] Data is in long format
- [ ] Chinese fonts configured
- [ ] Chart has title and axis labels
- [ ] Legend is present and meaningful
- [ ] Tooltips added for interactivity
- [ ] Export uses vl-convert with scale=2.0
- [ ] Output file extension is .png

## Related

- Polars documentation for data preparation
- CleanMast report module structure
- vl-convert documentation for export options

---

**Note**: This is a DRAFT skill document. During implementation, move to:
`.agents/skills/altair-visualization.md`
