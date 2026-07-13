# Test prompt for experiment-archive skill

## Prompt

Archive the experiment at `temp/archive-skill-test/source-experiment/` using
the experiment-archive skill.

## Expected result

- An archive directory at `./experiments-archived/{today}-source-experiment/`.
- `ARCHIVE.md` populated with source, date, policy, DVC archives, DVC
  individual files, git-tracked files, and pull instructions.
- Plaintext DVC directories compressed into `.tar.zst` archives with
  directory-prefixed entries.
- Parquet files kept as individual DVC files.
- `.dvc` files for every `.tar.zst` and `.parquet` file.
- Archived `Justfile` with corrected `PROJECT`/`ROOT` and an inline `pull`
  recipe that runs `dvc pull -R {{PROJECT}}` followed by one extraction line
  per archive.
- `git add` stages the archive directory cleanly.
- `just pull` restores all plaintext files to their original directories.

## Actual result

See `./2026-07-13-source-experiment/` for the successful reference fixture.
