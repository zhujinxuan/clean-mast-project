# Spec Template

Every `spec.md` has exactly two top-level sections: **Code rules** and **业务说明 (Business description)**.

| Section | Contents |
|---------|----------|
| **Code rules → Purpose** | One sentence: what this context or capability is for. Scope boundary. |
| **Code rules → Rules** | Concrete, enforceable rules. Each must be verifiable. If a rule cannot be checked by import-linter, ast-grep, or an LLM walkthrough, it is too vague. |
| **Code rules → Anti-patterns** | What agents must not do. Actionable: "never do X", not "careful with X". |
| **Code rules → When in doubt** | Default decision rule for ambiguity. One sentence each. |
| **业务说明 → Domain context** | How this module fits into the wind energy assessment pipeline. |
| **业务说明 → Key concepts** | Domain concepts this module models or operates on. |
| **业务说明 → Business constraints** | Real-world or industry constraints that drive the code design. |

## Code rules

<!-- Enforceable, mechanically verifiable rules that agents and tools must follow.
Rules here must be checkable by import-linter, ast-grep, or an LLM walkthrough. -->

### Purpose
<!-- One-sentence scope boundary -->

### Rules
- Rule 1
- Rule 2

### Anti-patterns
- Anti-pattern 1

### When in doubt
- Default decision 1

### What Makes a Rule Spec-Worthy?

A rule belongs in `spec.md` only if it can be enforced, either mechanically or by judgment.

- ❌ "Use good naming" is unenforceable and subjective.
- ❌ "Keep functions small" has no clear threshold.
- ✅ "No IO in compute/" is mechanically checkable with ast-grep.
- ✅ "Pydantic models default to `frozen=True`" is mechanically checkable with ast-grep.
- ✅ "Contexts never import from sibling contexts" is mechanically checkable with import-linter.

A rule that cannot be enforced by at least one of the three tiers is not a rule. It is a wish.

## 业务说明 (Business description)

<!-- Domain knowledge that agents and humans need to understand WHY the code works
this way. NOT mechanically enforceable — this is the "why" behind the rules above.
Business rules here are timeless: they should survive structural refactors
unchanged. -->

### Domain context
<!-- How this module/context fits into the wind energy assessment pipeline -->

### Key concepts
<!-- Wind energy domain concepts this module models or operates on -->

### Business constraints
<!-- Real-world or industry constraints that drive the code design -->

### What Makes Good 业务 Content

Business content records WHY, not HOW. Test: if you renamed every module and moved every file,
would this text still be true and useful? If yes, it's 业务. If no, it belongs in Code rules.

-   Business concept (e.g., "wind shear follows a power law")
-   Domain constraint (e.g., "IEC 61400 defines turbulence categories")
-   Pipeline meaning (e.g., "reconstruct-meso produces gap-filled timeseries from
    mesoscale model correlation")
-   Industry convention (e.g., "target heights 125/140/160 m are typical hub heights
    for modern turbines")

## Example: Pass

```markdown
## Code rules

### Purpose
Math-only computation for wind resource statistics.

### Rules
- Pure functions only. No IO, no side effects.
- Input: DataFrame/Series. Output: DataFrame/Series or scalar.
- Must have type annotations on all public functions.

### Anti-patterns
- Reading config files inside compute.
- Logging or print statements.
- Mutable global state.

### When in doubt
- If it touches a file, it belongs in render, not compute.

## 业务说明 (Business description)

### Domain context
统计计算模块负责风资源评估中的数学运算: 威布尔参数拟合、
风速频率统计、风玫瑰聚合。

### Key concepts
- **WeibullFitter**: 无状态模块级函数，从风速序列拟合形状参数 k 和尺度参数 A。
- **WindRose**: 16 扇区风向频率和平均风速的聚合结构。

### Business constraints
- 拟合方法 (最大似然) 遵循 IEC 61400-12 建议。
- 所有统计计算必须可重现: 相同输入 → 相同输出。
```

**Verification result:** `uv run lint-imports` passes because compute imports only from protocols/model. `ast-grep scan` passes because the no-io-in-compute rule returns zero findings. The LLM walkthrough confirms all functions are pure and annotated. 业务 section is identical after structural rename — domain integrity preserved. ✅ PASS.

## Example: Fail

```markdown
## Code rules

### Purpose
Report rendering pipeline.

### Rules
- Assemble atoms before rendering.
- Use pathlib.Path for all file paths.

### Anti-patterns
- Raw string paths.

### When in doubt
- If it renders a file, use the render module, not assemble.
```

**Verification result:** Missing `## 业务说明` section — every spec.md MUST have both Code rules and 业务说明. ast-grep finds `str(path)` in `render/chart_builder.py:47`. Import-linter catches `render/chart_builder.py` importing `cleanmast.subdomains.assessment`, which is a cross-context violation. The LLM walkthrough finds `open("output.json", "w")` in `compute/stats.py`, but the compute spec says compute must be pure. ❌ FAIL (4 violations: missing 业务 section + 3 code violations).
