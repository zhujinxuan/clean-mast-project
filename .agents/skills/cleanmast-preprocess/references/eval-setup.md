# Setting Up a New Evaluation Experiment

This guide explains how to add a new dataset evaluation to the `cleanmast-preprocess` skill.

## Directory layout convention

```
evals/
├── data/
│   └── extracted/
│       └── M{experiment}/          # raw logger files (expensive to re-extract)
├── outputs/
│   └── M{experiment}/              # all eval outputs for this dataset
│       ├── M{experiment}_merged.csv
│       ├── M{experiment}_normalized.csv
│       ├── M{experiment}_final.csv
│       ├── M{experiment}_pipeline.csv
│       └── evidence.md
└── pipeline/
    ├── 01_csv_merge.toml
    ├── 02_col_normalizer.toml
    └── 03_type_normalizer.toml
```

## Step-by-step checklist

1. **Archive and DVC-track the raw data**
   - Create `evals/data/m{experiment}_pre_masts.tar.zst`
   - Run `dvc add evals/data/m{experiment}_pre_masts.tar.zst`
   - Commit the `.dvc` pointer file and push to the DVC remote

2. **Add a Justfile bootstrap target**
   ```just
   bootstrap-M{experiment}:
       cd ../../../.. && dvc pull .agents/skills/cleanmast-preprocess/evals/data/m{experiment}_pre_masts.tar.zst.dvc
       mkdir -p data/extracted
       tar --zstd -xf data/m{experiment}_pre_masts.tar.zst -C data/extracted
       mkdir -p outputs/M{experiment}
   ```

3. **Create per-experiment pipeline configs**
   - Copy the three TOML files from `pipeline/`
   - Update paths to point to `../outputs/M{experiment}/`
   - Adjust column mappings to match the new dataset

4. **Write reference evidence.md**
   - Document channel mappings, height sources, and dropped columns
   - Store it under `evals/outputs/M{experiment}/evidence.md` as the expected reference

5. **Update `evals/evals.json`**
   - Add new eval entries with `target` paths under `evals/outputs/M{experiment}/`
   - Include assertions for:
     - File existence
     - Expected column names
     - Minimum row counts
     - Column-mismatch handling (where applicable)
     - `evidence.md` existence

6. **Clean up between runs**
   ```bash
   just clean-outputs-M{experiment}   # keep raw data
   just clean-all                     # wipe everything
   ```

## Reference M4941 setup

The M4941 evaluation is the canonical example. Use its files (`evals.json`, `Justfile`, `pipeline/*.toml`) as templates when adding a new experiment.
