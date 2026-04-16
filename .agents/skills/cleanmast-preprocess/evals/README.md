# CleanMast Preprocess Skill Evaluation

This directory contains the evaluation data and instructions for the `cleanmast-preprocess` skill.

## Evaluation Data

The full M4941 NRG logger dataset is stored as a zstd-compressed tar archive and tracked by DVC:

- `data/m4941_pre_masts.tar.zst` — The archive (not in git)
- `data/m4941_pre_masts.tar.zst.dvc` — DVC pointer file (in git)

The data is pushed to the default DVC remote `qiniu`.

## Bootstrapping Evaluation Data

```bash
just bootstrap
```

This pulls the DVC-tracked archive and extracts it to `data/extracted/M4941/`.

The evaluation is designed for an agent to read `SKILL.md` and the `references/`, then execute the preprocessing steps independently. The `evals.json` test cases assert that the correct outputs are produced.

## Cleaning Up Extracted Data

```bash
just clean
```

## Test Cases

See `evals.json` for the formal test prompts and assertions used to grade the skill.

| Eval | Name | What it tests |
|------|------|---------------|
| 1 | merge-nrg-sdr-files | Merging raw NRG .txt files with column mismatch handling |
| 2 | normalize-columns-and-types | Column renaming and type conversion |
| 3 | full-preprocessing-pipeline | End-to-end preprocessing workflow |
