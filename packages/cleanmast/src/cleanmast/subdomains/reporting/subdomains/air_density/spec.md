## Purpose

Multi-mast air density calculation for wind resource reports.

## Rules

- Inherits all rules from `reporting/spec.md` (which inherits `subdomains/spec.md`).

## 业务说明 (Business description)

### Domain context

空气密度影响风功率计算: P = 0.5 ρ A v³。密度由温度、气压、海拔决定 (理想气体定律)。

### Key concepts

标准空气密度 1.225 kg/m³ (15°C, 海平面)；实际密度因站点海拔和季节变化偏离标准值。
