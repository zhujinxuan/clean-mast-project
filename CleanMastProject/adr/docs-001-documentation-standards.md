---
id: docs-001-documentation-standards
name: documentation-standards
description: Documentation writing standards for CleanMast. Documentation MUST be source-code constrained, fact-checked against struct definitions, use Chinese for user-facing docs, and follow minimal comments policy.
status: enforced
tags: [documentation, docs, writing, chinese, standards]
applies_when:
  - writing documentation
  - creating docs/*.md files
  - documenting configuration
  - writing code comments
---

# ADR-001: Documentation Standards

## Status
**Enforced**

## Constraint (MUST)

1. **Documentation MUST be source-code constrained** - only document what can be verified from actual code files
2. **Documentation MUST undergo fact-checking** before publication:
   - Verify parameters in Types/ struct definitions
   - Confirm examples match real config files
   - Only explain functionality documented in source comments
3. **User-facing documentation (docs/*) MUST use Chinese language**
4. **Code comments MUST be minimal** - prefer self-documenting code
5. **Docstrings MUST only be used for public API functions**
6. **When uncertain, documentation MUST omit details rather than guess**

## Rationale (WHY)

- **Source-code constrained approach**: Prevents hallucinated parameters and outdated information. Documentation based on actual code stays accurate as the codebase evolves.
- **Fact-checking process**: Creates a verifiable chain from struct definition to user documentation, ensuring users see accurate configuration options.
- **Chinese for user docs**: User-facing documentation uses Chinese to match project requirements. Source code and AGENTS.md use English for agent instructions.
- **Minimal comments**: Code should be readable through clear naming. Excessive comments become outdated and mislead developers.

## Pattern (HOW)

### Source-Code Constrained Documentation

Documentation is built from actual code, not general knowledge:

```julia
# From src/Types/ProcessCleanConfig.jl
struct RangeRuleConfig
    minValue::Union{Float64, Nothing}
    maxValue::Union{Float64, Nothing}
    enabled::Bool
end

# Documentation reflects EXACT struct fields
# - Document minValue, maxValue, enabled
# - Do NOT invent additional parameters
```

### Fact-Checking Process

Before writing documentation, verify each parameter:

1. **Verify in Types/**: Check struct definitions
   ```bash
   # Find the struct definition
   grep -r "struct RangeRuleConfig" src/Types/
   ```

2. **Confirm in Examples**: Use real config files
   ```bash
   # Check actual usage in reference projects
   cat projects/pn-masts/config/process-clean.toml
   ```

3. **Source Comments**: Only explain functionality in code comments
   ```julia
   # Only document what this comment explains:
   # "Wind speed range 0-50 m/s based on IEC 61400-12-1"
   ```

4. **When Uncertain**: Omit details rather than guess
   ```markdown
   <!-- Instead of guessing: -->
   <!-- The algorithm uses... [unsure details] -->

   <!-- Write: -->
   See src/Algorithms/RangeCheck.jl for implementation details.
   ```

### Chinese Language for User Documentation

All files under `docs/` use Chinese:

```markdown
<!-- docs/user/process-clean.md -->

# 数据清理配置

## 概述
ProcessCleanConfig 用于定义数据清理规则。

## 配置参数
- `minValue`: 最小值
- `maxValue`: 最大值
- `enabled`: 是否启用

## 完整配置示例
```toml
[range_rules.wind_speed_80m]
minValue = 0.0
maxValue = 50.0
enabled = true
```
```

Source code uses English:

```julia
# src/DataClean/ProcessRange.jl
"""
Apply range validation to sensor data.
"""
function apply_range_check(df::DataFrame, config::RangeRuleConfig)::DataFrame
    # implementation
end
```

### Documentation Structure for Config Files

Chinese documentation follows this structure:

```markdown
## 概述 (Overview)
简要描述配置文件的用途。

## 基本结构 (Basic Structure)
```toml
# TOML template showing required sections
[section]
key = "value"
```

## 配置参数 (Configuration Parameters)
仅文档化 struct 中定义的字段：
- `field_name`: 字段描述 (from struct definition)

## 完整配置示例 (Complete Example)
来自参考项目的实际配置。

## 配置生成 (Configuration Generation)
使用 `recommend` 命令生成初始配置：
```bash
julia bin/CleanMast.jl recommend process-clean
```
```

### Minimal Comments Policy

Prefer self-documenting code:

```julia
# ✅ CORRECT: Clear function name, minimal comment
"""
Apply range validation to wind speed data.
Throws ArgumentError if config is invalid.
"""
function apply_range_check(df::DataFrame, config::RangeRuleConfig)::DataFrame

# ❌ WRONG: Redundant comments
# This function applies range check
# It takes a DataFrame and config
# It returns a DataFrame
function apply_range_check(df::DataFrame, config::RangeRuleConfig)::DataFrame
```

Comment domain context for meteorological assumptions:

```julia
# ✅ CORRECT: Explain physical constraint
# Ice detection: temperature < 0°C AND wind speed < 2 m/s
# Threshold based on EN 61400-12-1 icing criteria
function detect_icing(df::DataFrame)::DataFrame
```

## Anti-Pattern (AVOID)

```markdown
<!-- ❌ WRONG: Speculative documentation -->
The algorithm uses a sophisticated machine learning approach
to predict missing values based on historical patterns...
<!-- NEVER - only document what's in the code -->

<!-- ❌ WRONG: Invented parameters -->
Additional parameters:
- `confidence_threshold`: Confidence level (0-1)
- `max_iterations`: Maximum iterations
<!-- NEVER - only document struct fields -->

<!-- ❌ WRONG: Detailed algorithm explanation without source -->
The range check works by first normalizing the data,
then applying a statistical filter...
<!-- NEVER - refer to source file instead -->
```

```julia
# ❌ WRONG: Excessive comments
# Get the wind speed
wind_speed = row.wind_speed
# Check if it's missing
if ismissing(wind_speed)
    # Return nothing if missing
    return nothing
end

# ❌ WRONG: Commented-out code
# old_algorithm()
# new_algorithm()
result = current_algorithm()
```

## Phase Links

This ADR uses phase-based documentation. Load the appropriate phase file for your role:

| Phase | File | When to Load |
|-------|------|--------------|
| **on-plan** | [`phases/docs-001-documentation-standards/on-plan.md`](phases/docs-001-documentation-standards/on-plan.md) | Designer: Documentation planning |
| **review-plan** | [`phases/docs-001-documentation-standards/review-plan.md`](phases/docs-001-documentation-standards/review-plan.md) | Reviewer: Validating documentation plans |
| **code** | [`phases/docs-001-documentation-standards/code.md`](phases/docs-001-documentation-standards/code.md) | Writer: Writing documentation |
| **review-implementation** | [`phases/docs-001-documentation-standards/review-implementation.md`](phases/docs-001-documentation-standards/review-implementation.md) | Reviewer: Documentation review |

### Quick Compliance Check

```bash
# Check for speculative language in docs
# Flag these AI-sounding phrases:
grep -rn "delve\|it's important to note\|leverage\|utilize\|in order to\|robust\|streamline\|facilitate" docs/ || echo "OK: No AI-sounding phrases"

# Verify Chinese language in docs/*.md (should NOT have English headers for user content)
head -20 docs/user/*.md | grep -E "^# " | grep -v "^# [一-龥]" && echo "WARNING: Non-Chinese headers found"

# Check for excessive comments in source
grep -rn "# This function\|# It takes\|# It returns" src/ | head -5
```

## References

- [AGENTS.md](../AGENTS.md) - Agent guidelines with documentation standards
- [Types/ directory](../src/Types/) - Struct definitions (source of truth)
- [docs/ directory](../docs/) - User-facing documentation (Chinese)
- Phase files location: [`./phases/docs-001-documentation-standards/`](./phases/docs-001-documentation-standards/)
