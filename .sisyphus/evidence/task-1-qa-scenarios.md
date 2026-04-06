> **说明**
> 本文档记录任务 1 的 QA 验证结果。

## QA Scenario 1: Regular column returns empty string

```bash
uv run python -c "
import sys; sys.path.insert(0, 'packages/cleanmast/src')
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn
s = SensorColumn(column_name='WindSpeed_100m_avg [m/s]', sensor_type='WindSpeed', sensor_direction='', height=100.0, stat_type='avg', unit='m/s')
result = s.detect_interpolation_marker()
assert result == '', f'Expected empty string, got {result!r}'
print('PASS: regular column returns empty string')
" 2>&1 | tee .sisyphus/evidence/task-1-regular-column.txt
```

**预期输出:**
```
PASS: regular column returns empty string
```

---

## QA Scenario 2: Interpolated column returns "内插"

```bash
uv run python -c "
import sys; sys.path.insert(0, 'packages/cleanmast/src')
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn
s = SensorColumn(column_name='WS_125m_fill:interpolated', sensor_type='WindSpeed', sensor_direction='', height=125.0, stat_type='avg', unit='m/s')
result = s.detect_interpolation_marker()
assert result == '内插', f'Expected 内插, got {result!r}'
print('PASS: interpolated column returns 内插')
" 2>&1 | tee .sisyphus/evidence/task-1-interpolated-column.txt
```

**预期输出:**
```
PASS: interpolated column returns 内插
```

---

## QA Scenario 3: Extrapolated column returns "外推"

```bash
uv run python -c "
import sys; sys.path.insert(0, 'packages/cleanmast/src')
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn
s = SensorColumn(column_name='WS_200m_fill:extrapolated', sensor_type='WindSpeed', sensor_direction='', height=200.0, stat_type='avg', unit='m/s')
result = s.detect_interpolation_marker()
assert result == '外推', f'Expected 外推, got {result!r}'
print('PASS: extrapolated column returns 外推')
" 2>&1 | tee .sisyphus/evidence/task-1-extrapolated-column.txt
```

**预期输出:**
```
PASS: extrapolated column returns 外推
```

---

## QA Scenario 4: Field removed check

```bash
uv run python -c "
import sys; sys.path.insert(0, 'packages/cleanmast/src')
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn
s = SensorColumn(column_name='test', sensor_type='WindSpeed', sensor_direction='', height=100.0, stat_type='avg', unit='m/s')
assert not hasattr(s, 'interpolation_marker'), f'SensorColumn still has interpolation_marker field'
print('PASS: interpolation_marker field removed')
" 2>&1 | tee .sisyphus/evidence/task-1-field-removed.txt
```

**预期输出:**
```
PASS: interpolation_marker field removed
```
