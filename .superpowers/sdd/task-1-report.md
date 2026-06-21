# Task 1 Report: ANOVA Test Failures (TDD Red Phase)

## Status: DONE

## Commits Made

- `29360cf` — `test: add ANOVA + residuals assertions to DOE analysis tests`

## Test Results

### New Tests (all FAIL — expected TDD red phase)

| Test | Result | Failure Reason |
|------|--------|----------------|
| `test_fit_linear_returns_anova` | FAIL | `AssertionError: assert 'anova' in model` — `fit_linear()` does not yet return `anova`, `residuals`, `lack_of_fit_p`, `n_obs`, or `n_params` keys |
| `test_fit_linear_anova_values_perfect_fit` | FAIL | `KeyError: 'anova'` — same root cause; accessing `model["anova"]` before it exists |
| `test_fit_rsm_returns_anova` | FAIL | `AssertionError: assert 'anova' in model` — `fit_rsm()` also lacks `anova` and `residuals` keys |

Each test fails on the very first new assertion (`"anova" in model`), confirming the implementation in `doe/analysis.py` has not yet been extended with the new return keys.

### Existing Tests (all PASS — backward compat confirmed)

All 13 pre-existing tests continue to pass with no regressions:

- `test_fit_linear_perfect_model`
- `test_fit_linear_with_interaction`
- `test_fit_linear_noisy_data`
- `test_fit_rsm_with_curvature`
- `test_has_curvature_true`
- `test_has_curvature_false`
- `test_fit_linear_missing_response`
- `test_fit_linear_nan_in_response`
- `test_fit_linear_overparameterized`
- `test_fit_linear_merges_on_run`
- `test_predict_from_model_linear`
- `test_predict_from_model_rsm`
- `test_is_center_row`

## Concerns

None. The brief's test code was appended verbatim, all new tests fail as expected, and no existing tests were broken. Ready for the implementation phase (adding ANOVA tables, residuals, and lack-of-fit to `fit_linear` and `fit_rsm` in `doe/analysis.py`).

---

## Fix Round 2: Review Findings Applied

### What was fixed

1. **Critical fix -- `test_fit_linear_returns_anova`:** Changed `assert model["rmse"] > 0` to `assert model["rmse"] == 0.0` because the test data (8 runs, 4 unique points, 4 parameters) is a saturated model with perfect fit, yielding RMSE = 0. The old assertion would always fail.

2. **Spec gap 1:** Added `assert "model_type" in model` after the existing key checks, and `assert model["model_type"] == "linear"` at the end of the function, to confirm the key exists and has the correct value.

3. **Spec gap 2:** Added `assert 0 <= model["r_squared_adj"] <= 1.0` after the `r_squared` check, ensuring the adjusted R-squared is validated as a proper proportion.

4. **Spec gap 3:** In `test_fit_rsm_returns_anova`, added thorough sub-key validation for both `residuals` and `anova` dictionaries to match the level of scrutiny in the linear test.

### Test results

Command: `python -m pytest tests/test_doe_analysis.py -v`

```
tests/test_doe_analysis.py::test_fit_linear_perfect_model PASSED
tests/test_doe_analysis.py::test_fit_linear_with_interaction PASSED
tests/test_doe_analysis.py::test_fit_linear_noisy_data PASSED
tests/test_doe_analysis.py::test_fit_rsm_with_curvature PASSED
tests/test_doe_analysis.py::test_has_curvature_true PASSED
tests/test_doe_analysis.py::test_has_curvature_false PASSED
tests/test_doe_analysis.py::test_fit_linear_missing_response PASSED
tests/test_doe_analysis.py::test_fit_linear_nan_in_response PASSED
tests/test_doe_analysis.py::test_fit_linear_overparameterized PASSED
tests/test_doe_analysis.py::test_fit_linear_merges_on_run PASSED
tests/test_doe_analysis.py::test_predict_from_model_linear PASSED
tests/test_doe_analysis.py::test_predict_from_model_rsm PASSED
tests/test_doe_analysis.py::test_is_center_row PASSED
tests/test_doe_analysis.py::test_fit_linear_returns_anova FAILED
tests/test_doe_analysis.py::test_fit_linear_anova_values_perfect_fit FAILED
tests/test_doe_analysis.py::test_fit_rsm_returns_anova FAILED
```

13 existing PASS, 3 new FAIL (as expected -- implementation not yet in place).
