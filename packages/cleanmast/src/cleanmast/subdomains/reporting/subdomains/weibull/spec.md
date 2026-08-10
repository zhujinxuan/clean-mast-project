## Purpose

Weibull distribution fitting and visualization for wind resource reports.

## Rules

- Inherits all rules from `reporting/spec.md` (which inherits `subdomains/spec.md`).
- Weibull fitting is module-level functions in `compute.py` (`fit_weibull`);
  never introduce a stateful fitter class.

## Anti-patterns

- Stateful fitter class with config stored in `__init__`.

## 业务说明 (Business description)

### Domain context

威布尔分布是风资源评估的基础: 从风速时序数据拟合形状参数 k 和尺度参数 A，得到风速概率密度函数和风能密度曲线。

### Key concepts

k < 2 表示风速变化大 (典型内陆), k > 2 表示风速集中 (典型沿海/海上)。

### Business constraints

拟合方法 (最大似然/最小二乘/矩法) 影响评估结果，默认使用最大似然估计。
