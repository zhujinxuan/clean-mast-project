# Test Data

DVC-managed real-world test datasets for CleanMast.

## Structure

Test data is organized by package: `test-data/{packagename}/{dataset}-{command}/`

- `cleanmast/kp-202603-report/`: Test dataset for report timeseries command
  - Filled-height results from kp-202603 project
  - Two masts: L32261, M245228

## Usage

```bash
# Pull test data
dvc pull

# Run report generation
uv run cleanmast report timeseries test-data/cleanmast/kp-202603-report/rep-ts-report.toml
```

## Adding New Datasets

1. Create directory: `test-data/{packagename}/{dataset}-{command}/`
2. Copy necessary files preserving structure
3. `dvc add` each data file
4. Update this README
