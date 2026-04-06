# Work Plan: Implement Weibull Atoms

## TL;DR

Implement Weibull distribution fitting atoms: parameter tables, distribution plots, and multi-height comparisons.

**Dependencies**: PRD created (`.sisyphus/notepads/prds/weibull-analysis-migration.md`)

---

## Context

Weibull analysis fits probability distributions to wind speed data:
- Maximum Likelihood Estimation (MLE) for shape (k) and scale (c)
- Histogram + fitted PDF visualization
- Parameter tables
- Multi-height comparisons

Atoms:
1. SingleMastWeibullParametersAtom - Table of k, c by height
2. SingleMastWeibullDistributionAtom - Histogram + PDF per height
3. SingleMastWeibullMultiHeightAtom - Combined distribution plot

---

## Work Objectives

### Deliverables
1. WeibullSchema
2. WeibullFitter domain service
3. 3 ReportAtoms
4. Converter
5. Tests

---

## Execution Strategy

### Wave 1: Foundation
- Task 1: WeibullSchema
- Task 2: WeibullFitter (MLE + Method of Moments fallback)

### Wave 2: Atoms (Parallel)
- Task 3: SingleMastWeibullParametersAtom
- Task 4: SingleMastWeibullDistributionAtom
- Task 5: SingleMastWeibullMultiHeightAtom

### Wave 3: Integration
- Task 6: WeibullAnalysisToAtoms converter
- Task 7: Tests

---

## TODOs

- [ ] 1. WeibullSchema
  **Files**: `value_objects/schemas/weibull.py`
  **Fields**: height, shape_k, scale_c, mean_speed, bin_centers, observed_density, fitted_density

- [ ] 2. WeibullFitter
  **Files**: `services/weibull_fitter.py`
  **Methods**: fit(), calculate_pdf(), _neg_log_likelihood(), _method_of_moments()
  **Dependencies**: scipy.optimize, scipy.stats.weibull_min

- [ ] 3. SingleMastWeibullParametersAtom
  **Files**: `value_objects/single_mast/weibull_parameters.py`
  **Renders**: Typst table (height | k | c)

- [ ] 4. SingleMastWeibullDistributionAtom
  **Files**: `value_objects/single_mast/weibull_distribution.py`
  **Renders**: Altair layered chart (histogram bars + PDF line)

- [ ] 5. SingleMastWeibullMultiHeightAtom
  **Files**: `value_objects/single_mast/weibull_multi.py`
  **Renders**: Multi-line chart of PDFs for all heights

- [ ] 6. WeibullAnalysisToAtoms
  **Files**: `services/weibull_converter.py`

- [ ] 7. Tests
  **Files**: `tests/analysis/test_weibull_fitter.py`, `tests/report/test_weibull_atoms.py`

---

## Key Algorithms

### MLE Fitting
```python
# Negative log-likelihood
def neg_log_likelihood(params, data):
    k, c = params
    n = len(data)
    return -n*log(k) + n*k*log(c) - k*sum(log(x)) + sum(x**k)/c**k

# Optimize
result = minimize(neg_log_likelihood, [2.0, mean(data)/gamma(1+1/2)], method='L-BFGS-B')
```

### Method of Moments Fallback
```python
k = (0.9874 / (std/mean)) ** 1.0983
c = mean / gamma(1 + 1/k)
```

---

## Success Criteria

- [ ] MLE fitting converges for typical data
- [ ] Fallback to MoM when MLE fails
- [ ] Histogram + PDF overlay renders correctly
- [ ] All 3 atoms functional
- [ ] Tests pass with >80% coverage
