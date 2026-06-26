# Spec Template

Every `spec.md` has exactly four sections.

| Section | Contents |
|---------|----------|
| **Purpose** | One sentence: what this context or capability is for. Scope boundary. |
| **Rules** | Concrete, enforceable rules. Each must be verifiable. If a rule cannot be checked by import-linter, ast-grep, or an LLM walkthrough, it is too vague. |
| **Anti-patterns** | What agents must not do. Actionable: "never do X", not "careful with X". |
| **When in doubt** | Default decision rule for ambiguity. One sentence each. |

## What Makes a Rule Spec-Worthy?

A rule belongs in `spec.md` only if it can be enforced, either mechanically or by judgment.

- ❌ "Use good naming" is unenforceable and subjective.
- ❌ "Keep functions small" has no clear threshold.
- ✅ "No IO in compute/" is mechanically checkable with ast-grep.
- ✅ "Pydantic models default to `frozen=True`" is mechanically checkable with ast-grep.
- ✅ "Contexts never import from sibling contexts" is mechanically checkable with import-linter.

A rule that cannot be enforced by at least one of the three tiers is not a rule. It is a wish.

## Example: Pass

```markdown
## Purpose
Math-only computation for wind resource statistics.

## Rules
- Pure functions only. No IO, no side effects.
- Input: DataFrame/Series. Output: DataFrame/Series or scalar.
- Must have type annotations on all public functions.

## Anti-patterns
- Reading config files inside compute.
- Logging or print statements.
- Mutable global state.

## When in doubt
- If it touches a file, it belongs in render, not compute.
```

**Verification result:** `uv run lint-imports` passes because compute imports only from protocols/model. `ast-grep scan` passes because the no-io-in-compute rule returns zero findings. The LLM walkthrough confirms all functions are pure and annotated. ✅ PASS.

## Example: Fail

```markdown
## Purpose
Report rendering pipeline.

## Rules
- Assemble atoms before rendering.
- Use pathlib.Path for all file paths.

## Anti-patterns
- Raw string paths.
```

**Verification result:** ast-grep finds `str(path)` in `render/chart_builder.py:47`. Import-linter catches `render/chart_builder.py` importing `cleanmast.subdomains.assessment`, which is a cross-context violation. The LLM walkthrough finds `open("output.json", "w")` in `compute/stats.py`, but the compute spec says compute must be pure. ❌ FAIL (3 violations).
