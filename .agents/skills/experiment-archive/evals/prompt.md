# Test prompt for experiment-archive skill

## Prompt

Archive the experiment at `temp/archive-skill-test/source-experiment/` using
the experiment-archive skill.

## Expected result

- An archive directory at `./experiments-archived/{today}-source-experiment/`.
- `ARCHIVE.md` populated with source, date, policy, DVC archives, DVC
  individual files, git-tracked files (incl. `justfile.archive`, `deploy.py`,
  `formats/**`), and Deploy instructions.
- Plaintext DVC directories compressed into `.tar.zst` archives with
  directory-prefixed entries.
- Parquet files kept as individual DVC files.
- `.dvc` files for every `.tar.zst` and `.parquet` file.
- `justfile.archive`: byte-identical copy of the source Justfile (no
  `PROJECT`/`ROOT` rewrites, no added recipes); `deploy.py` at archive root,
  identical to `references/deploy.py`.
- `.gitignore` allow-lists `!**/justfile.archive`.
- `git add` stages the archive directory cleanly.
- Deploy works: `uv run python <archive>/deploy.py projects/e2e-archive-test`
  exits 0 with no warnings and satisfies every Phase B check in
  `references/e2e-test-criteria.md`.

## Actual result

See `./2026-07-13-source-experiment/` for the successful reference fixture.

## Regenerating the fixture

The fixture is a filtered snapshot of the real archive
(`experiments-archived/2026-07-13-松原/`). After any archive-design change,
re-snapshot instead of hand-editing:

```cmd
robocopy "experiments-archived\2026-07-13-松原" ^
         ".agents\skills\experiment-archive\evals\2026-07-13-source-experiment" ^
         /MIR /COPY:DAT /R:0 /W:0 /XF *.parquet *.tar.zst *.csv *.txt
```

`/MIR` mirrors additions and deletions; `/XF` excludes the DVC payload classes
(parquet, tar.zst, csv, txt) so the fixture keeps only git-tracked files and
`.dvc` pointers. Then verify against `references/e2e-test-criteria.md` Phase A.
