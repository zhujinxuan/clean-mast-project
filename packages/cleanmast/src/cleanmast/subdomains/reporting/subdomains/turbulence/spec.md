## Purpose

Single-mast turbulence intensity analysis for wind resource reports.

## Rules

- Inherits all rules from `reporting/spec.md` (which inherits `subdomains/spec.md`).
- IEC categories are module-level constants (not mutable instance state).

## Anti-patterns

- Stateful class with mutable `self.iec_categories` dict.

## 业务说明 (Business description)

### Domain context

湍流强度 TI = σ / v_mean，是风机疲劳载荷评估的关键参数。按 IEC 61400-1 标准分级: A+/A/B/C (A+ 最高湍流)。

### Key concepts

TI 按风速 bin 分段计算 (bin-by-bin)，典型 bin 宽度 1 m/s。

### Business constraints

IEC 标准定义了 TI 参考曲线 (TI_ref = I_ref * (0.75 + 5.6/v))，实际 TI 必须低于参考曲线对应的类别阈值。
