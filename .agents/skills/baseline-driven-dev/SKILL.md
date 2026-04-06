---
name: baseline-driven-dev
description: |
  Guides baseline-driven development using verify_baseline.py for Python packages.
  
  **When to use:**
  - Planning implementation tasks with verification requirements
  - Setting up waves that must pass baseline checks
  - Analyzing ty/ruff/pytest errors from baseline reports
  - Designing incremental improvements with measurable targets
  - User mentions "baseline", "verify_baseline", or verification workflow
  
  **Key principle:** Each wave must begin and end with baseline verification.
---

# Baseline-Driven Development

This skill provides structured workflow for using the `verify_baseline.py` script to drive development in measurable waves.

## Quick Commands

```bash
# Generate baseline
uv run python scripts/verify_baseline.py --package {package}

# Individual checks
uv run ty check packages/{package} --output-format full
uv run ruff check packages/{package}
uv run pytest packages/{package}/tests -v
```

## What is a Wave?

**A wave is a logical grouping of related work** with a clear theme/narrative:
- "Discovery and analysis"
- "Fix type errors in assessment domain"  
- "Refactor report builder"
- "Add windrose grid atom"
- "Cleanup orphaned directories"

Waves group tasks that:
- Belong to the same domain/subdomain
- Have similar complexity
- Can be verified together
- Make sense as a single commit or commit group

## The 4-Part Wave Structure

Every wave follows this pattern:

### 1. Start with Baseline (REQUIRED)
```bash
uv run python scripts/verify_baseline.py --package {package}
```
- Record the starting state
- This is your "before" measurement
- **Do this BEFORE any work in the wave**

### 2. Do the Work
- Complete all tasks in the wave's scope
- Group related changes together
- Examples: refactoring, feature work, bug fixes, type improvements

### 3. End with Baseline Verification (REQUIRED)
```bash
uv run python scripts/verify_baseline.py --package {package}
```
- Generate new baseline
- Compare to starting baseline
- **Do this AFTER all wave work is complete**

### 4. Analyze Results

**Compare the two baselines:**

| Check | Starting | Ending | Result |
|-------|----------|--------|--------|
| ty | N errors | M errors | Improved/Worsened/Same |
| ruff | N errors | M errors | Improved/Worsened/Same |
| pytest | N failed | M failed | Improved/Worsened/Same |

**Decision rules:**
- ✅ **Baseline improved** → Wave complete, commit and proceed
- ⚠️ **Baseline same** → Acceptable if:
  - Work was pure refactoring with no behavior changes
  - Adding new code that didn't affect existing checks
  - Intentionally keeping compatibility
- ❌ **Baseline worse** → **STOP** - Must fix before proceeding
  - If intentionally worse, document the reason in commit message
  - If unintentionally worse, you broke something - fix it now
  - **Never proceed to next wave with a worse baseline**

## The 4 Checks to Consider

For each wave, consider which checks are relevant:

### ty (Type Checking)
- **When to care:** Type signature changes, refactoring, adding types
- **Target:** Error count should decrease or stay same
- **Acceptable increase:** Only if adding strict types to previously untyped code

### ruff (Linting)
- **When to care:** Code style, imports, formatting
- **Target:** Should always pass (0 errors)
- **Acceptable increase:** Never - fix immediately

### pytest (Tests)
- **When to care:** Feature work, bug fixes, test additions
- **Target:** Failed tests should decrease or stay same
- **Acceptable increase:** Only if adding new tests that expose existing bugs (document this)

### dvc-verify (Data Verification)
- **When to care:** DVC-managed test data changes
- **Target:** Should always pass
- **Acceptable increase:** Never

## Example Waves

**Wave: "Discovery - analyze current codebase"**
1. Baseline: 66 ty errors, 0 ruff errors, 891 tests passing
2. Work: Run discovery tasks, inventory files, check imports
3. Verify: Same baseline (discovery doesn't change code)
4. Result: ✅ Same is acceptable for pure discovery

**Wave: "Fix type errors in assessment domain"**
1. Baseline: ty shows 50 errors in assessment/
2. Work: Add TypedDict, fix signatures, add type ignores where needed
3. Verify: ty shows 20 errors in assessment/
4. Result: ✅ Improved - commit and proceed

**Wave: "Refactor report builder without logic changes"**
1. Baseline: ty 0 errors, ruff 0 errors, pytest 100 passing
2. Work: Extract methods, rename variables, no logic changes
3. Verify: ty 0 errors, ruff 0 errors, pytest 100 passing
4. Result: ✅ Same is acceptable for pure refactoring

**Wave: "Add new feature with tests"**
1. Baseline: pytest 100 passing
2. Work: Add feature + tests
3. Verify: pytest 105 passing, 0 new failures
4. Result: ✅ Improved

## Output Files

- `packages/{package}/baseline-{timestamp}.md` — Summary markdown
- `packages/{package}/baseline-refs/{timestamp}-{tool}.json` — Large errors
- Error threshold: 500 chars (inline vs JSON reference)

## Key Principle

**"Every wave begins and ends with baseline verification. If the baseline is worse without a documented reason, the wave isn't done."**

Use baselines to:
- ✅ Validate wave completion objectively
- ✅ Catch regressions immediately  
- ✅ Track improvement over time
- ✅ Make data-driven decisions about when to proceed
- ✅ Prevent technical debt accumulation

## For Prometheus (Plan Building)

1. **Generate initial baseline** to understand current state
2. **Design waves as logical groupings:**
   - Group by domain/subdomain
   - Group by type of work (discovery, cleanup, refactoring, features)
   - Keep waves focused and verifiable
3. **Set baseline expectations for each wave:**
   - What should improve?
   - What can stay the same?
   - What must not get worse?

## For Atlas (Orchestration)

1. **Start wave:** Generate baseline → Do work → Generate baseline → Compare
2. **If baseline improved:** Commit and proceed to next wave
3. **If baseline same:** Accept if reasonable (document in commit if unclear)
4. **If baseline worse:** STOP and fix before proceeding
5. **Never skip baseline verification** - it's your safety net
