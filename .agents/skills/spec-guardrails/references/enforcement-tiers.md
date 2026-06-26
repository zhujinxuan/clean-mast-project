# Enforcement Tiers

Three enforcement tiers run in sequence. Any tier failure means REJECT.

## Tier 1: Import Linter

**What it checks:** Who imports from whom. Pipeline direction, cross-context boundaries, and capability independence.

**Config:** `.importlinter` at workspace root. Supported contract types:

- `layers`: enforces left-to-right pipeline direction.
- `forbidden`: blocks specific source modules from importing specific forbidden modules.
- `independence`: ensures a set of modules do not import each other.

```ini
# Layers contract
[importlinter:contract:my-pipeline]
type = layers
layers = (api) (render) (assemble) (compute) (protocols) (model)

# Forbidden contract
[importlinter:contract:no-cross-context]
type = forbidden
source_modules = cleanmast.subdomains.reporting
forbidden_modules = cleanmast.subdomains.assessment

# Independence contract
[importlinter:contract:no-cross-capability]
type = independence
modules = cleanmast.subdomains.reporting.subdomains.*
```

**Run:** `uv run lint-imports`

**Pass condition:** Zero contract violations.

## Tier 2: ast-grep

**What it checks:** Code shape, including decorators, function calls, type annotations, and comments.

**Rule files:** `.ast-grep/rules/*.yml`. Each rule has `id`, `language`, `severity`, `message`, `files` (glob), and `rule` (AST pattern).

Example `frozen-model.yml`:

```yaml
id: frozen-model
language: python
severity: error
message: Model dataclasses must use frozen=True
files:
  - packages/cleanmast/src/cleanmast/subdomains/reporting/**/model/**
rule:
  pattern: "@dataclass"
  kind: decorator
  not:
    has:
      pattern: frozen=True
```

**Run:** `ast-grep scan --rules .ast-grep/rules/`

**Pass condition:** Zero findings.

## Tier 3: LLM + Checklist

**What it checks:** Rules that require reasoning, such as design intent and spec-to-code alignment.

**Walkthrough process:**

1. Read the `spec.md` under review and list every rule in the Rules section.
2. For each rule not already covered by import-linter or ast-grep, read the relevant source files and answer the yes/no question encoded in the rule.
3. For each anti-pattern, scan the code for violations. A function in `compute/` that reads files is a violation even if no ast-grep rule catches it.
4. Verdict: any violation means FAIL, with a file:line reference.

**Example checklist for `subdomains/spec.md`:**

| Rule | Check | Verdict |
|------|-------|---------|
| "Compute never does IO" | Read `compute.py` and `compute/*.py`. Grep for `open(`, `Path.read_text()`, `requests.get()`. | PASS if none found |
| "Entities frozen=True" | Read `model.py` and `model/*.py`. Every Pydantic class must have `model_config = ConfigDict(frozen=True)` unless it has `# mutable: <reason>`. | PASS if all justified |
| "api.py is sole public interface" | Read `__init__.py`. Does it export anything beyond model types and api functions? | PASS if clean |
| "No infrastructure types in `__init__.py`" | Read `__init__.py`. Are any SqlAlchemy, FastAPI, or config objects exported? | FAIL if found |

## General vs Domain-Specific Enforcement

| Tier | General (same for every context) | Domain-Specific (varies per spec.md) |
|------|------|------|
| Import linter | Pipeline direction (`layers` contract) is universal for any DDD pipeline. | "Context A never imports context B" is per-workspace. |
| ast-grep | Rules like `no-type-ignore` and `no-any-type` apply everywhere. | Rules like `no-io-in-compute` and `frozen-model` target specific directories. |
| LLM checklist | The walkthrough process is universal: read spec, check each rule, return verdict. | The questions come from each context's `spec.md` Rules section. |

When adding enforcement for a new context, write the rules into that context's `spec.md` first. Then add import-linter contracts and ast-grep rules only for the rules the mechanical tiers can check.
