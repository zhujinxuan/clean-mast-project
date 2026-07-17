---
name: experiment-archive
description: |
  Archive a completed CleanMast experiment from `projects/` into DVC-tracked
  `experiments-archived/` for long-term storage, freeing the working `projects/`
  tree. Only core replay files are copied; generated artifacts are excluded.
  Plaintext DVC files are compressed into `.tar.zst` archives; parquet files
  stay as individual DVC-tracked files. Git-tracked configs and scripts remain
  as-is. Automatically spawns an explore subagent to detect edge cases before
  archiving. MUST USE this skill when the user says "archive experiment",
  "archive project", "freeze experiment", "move to experiments-archived", or
  similar.
---

# Experiment Archive Skill

Archives a completed CleanMast experiment by copying only the **core replay
payload** from `projects/` into the DVC-tracked `experiments-archived/` storage
area. The original `projects/` directory is left untouched — this is a **copy**,
not a move.

Acceptance criteria for a full archive → deploy cycle: see
`@references/e2e-test-criteria.md`. Run it after any change to this skill or
to `references/deploy.py`.

## File Classification

Every file in the experiment falls into exactly one category:

| Category | Rule | Storage |
|---|---|---|
| Git-tracked | Extension in `{.toml, .json, .yaml, .yml, .md, .py}` or filename is `Justfile` / `justfile.archive` | Committed directly to git |
| DVC parquet | Extension is `.parquet` | Individual DVC files, `dvc add`'d one-by-one |
| DVC plaintext | Everything else (e.g. `.csv`, `.txt`, `.png`, `.docx`, `.pdf`, `.dat`) | Tarred into `<dirname>.tar.zst`, one per directory, then `dvc add`'d |

**Rule of thumb:** git-tracked = code + config; `.parquet` = standalone DVC;
everything else = plaintext DVC (tarred).

## Prerequisites

- Repo root is your working directory.
- `dvc` remote is configured (check `dvc remote list`).
- `just`, `tar`, `zstd` are on `PATH`.
- The experiment is in `projects/<name>/` and has a `Justfile` at its root.

---

## Step 1: Explore for Edge Cases

**Before copying anything**, spawn an explore subagent to scan the experiment:

```
Explore projects/<experiment-name>/ recursively.
Apply the classification rule:
  - Git-tracked: .toml .json .yaml .yml .md .py, or filename "Justfile"
  - DVC parquet: .parquet
  - DVC plaintext: everything else

Report any files with unexpected or unknown extensions (not in the common set
of .csv .txt .png .docx .pdf .dat .wnd .html .svg .xlsx .jsonl .lock .ini .cfg
.jpeg .jpg .gif .bmp .tiff .webp .zip .gz .bz2 .xz .7z .rar .zst). Also report
zero-byte files, symbolic links, and files >500 MB. For each: path, size,
extension, and a one-line note.
```

If the explorer finds anything unexpected, **pause and inform the user**
before continuing. The user may need to decide whether to include, exclude,
or reclassify those files.

---

## Step 2: Compute Archive Destination

The archive destination is `experiments-archived/<archive-date>-<experiment-name>/`:

- `<archive-date>` = today's date in `yyyy-mm-dd` format (e.g. `2026-07-13`).
- `<experiment-name>` = the experiment source directory basename with its own
  `yyyy-mm-dd-` prefix stripped off. Example: `projects/2026-07-02-松原/` →
  experiment-name = `松原`, destination = `experiments-archived/2026-07-13-松原/`.

### Collision Handling

If the destination already exists, append `-2`, `-3`, … in `cmd`:

```cmd
set DEST=experiments-archived\%ARCHIVE_DATE%-%EXPERIMENT_NAME%
set N=2
:loop
if exist "%DEST%\" (
    set DEST=experiments-archived\%ARCHIVE_DATE%-%EXPERIMENT_NAME%-%N%
    set /A N+=1
    goto loop
)
```

---

## Step 3: Copy the Core Replay Payload

Copy **only** the core replay payload — the minimal set of files needed to
re-run the experiment:

```cmd
robocopy projects\%EXPERIMENT_DIR% %DEST% /COPYALL /R:0 /W:0 ^
    Justfile ^
    parse-sensors.* ^
    pre-masts\ ^
    masts\ ^
    mesos\ ^
    raw\ ^
    just-override\ ^
    formats\
```

(`%EXPERIMENT_DIR%` = full source dir basename with date prefix, e.g. `2026-07-02-松原`.)

`formats/` holds the sensor/clean format configs (`formats/sensor/*.toml`,
`formats/clean/*.toml`). `parse-sensors.toml` and the generated
`process-clean.toml` reference them PROJECT-RELATIVE (e.g.
`formats/sensor/nrg.toml`), so the experiment cannot re-run without them.
All files inside are `.toml` → git-tracked by the classification rule; no
`.tar.zst` is needed for this directory.

**Do NOT copy** generated/derived artifacts such as `meso-models/`,
`reconstruct-*/`, `representative-year/`, `rep-ts/`, `investigation/`,
`logs/`, or any other output directories. The archive is for replay, not
results.

`robocopy /E` (`/E` = include subdirs even empty) is implicit when copying
(`robocopy` fails because a directory is missing (some
experiments lack e.g. `just-override/`), add `/NDL /NFL` to suppress errors
or skip that line.

### Archive-Root `.gitignore`

Create `%DEST%\.gitignore` so git tracks **only** the intended files.
Everything else is ignored by default:

```text
*
!**/
!**/*.py
!**/*.md
!**/*.toml
!**/*.json
!**/*.yaml
!**/*.yml
!**/Justfile
!**/justfile.archive
!.gitignore
!**/*.dvc
```

In `cmd`:

```cmd
(
echo *
echo !**/
echo !**/*.py
echo !**/*.md
echo !**/*.toml
echo !**/*.json
echo !**/*.yaml
echo !**/*.yml
echo !**/Justfile
echo !**/justfile.archive
echo !.gitignore
echo !**/*.dvc
) > %DEST%\.gitignore
```

DVC will later append its own entries to this file; they are redundant but
harmless because the allow-list already ignores `.tar.zst` and `.parquet`
files.

---

## Step 4: Identify DVC Plaintext Directories

Walk the destination tree. For every directory that contains **at least one
DVC plaintext file** (non-`.parquet`, non-git-tracked), that directory needs
a `.tar.zst` archive.

Use this Python helper:

```python
import os, sys

archive_root = sys.argv[1]
GIT_EXTS = {'.toml', '.json', '.yaml', '.yml', '.md', '.py'}
GIT_NAMES = {'Justfile'}

plaintext_dirs = set()

for dirpath, dirnames, filenames in os.walk(archive_root):
    for f in filenames:
        ext = os.path.splitext(f)[1].lower()
        if ext == '.parquet':
            continue
        if ext in GIT_EXTS or f in GIT_NAMES:
            continue
        plaintext_dirs.add(dirpath)
        break

for d in sorted(plaintext_dirs):
    print(d)
```

Save as a temp file and run against the archive destination. Output = list of
directories needing `.tar.zst` archives.

---

## Step 5: Create `.tar.zst` Archives

For each plaintext directory from Step 4, run `tar` from the **parent**
of that directory and include the directory prefix in the archive entries:

```cmd
cd /D <archive-destination>\<parent-of-relative-dir>
tar cf - <relative-dir>/<file1> <relative-dir>/<file2> ... | zstd -T0 > <dirname>.tar.zst
```

Then delete the original plaintext files from the archive copy:

```cmd
del /Q <each-plaintext-file>
```

### Example: Top-Level Directory

For `masts/` containing `M5057.csv`, `M1664.csv`, `M5972.csv`, `M3142.csv`,
and a git-tracked `README.md`:

```cmd
cd /D experiments-archived\2026-07-13-松原
tar cf - masts/M5057.csv masts/M1664.csv masts/M5972.csv masts/M3142.csv | zstd -T0 > masts.tar.zst
del /Q masts\M5057.csv masts\M1664.csv masts\M5972.csv masts\M3142.csv
```

After this, `masts/` still contains `README.md` (git-tracked) and the
`.tar.zst` lives at the experiment root alongside the `masts/` directory.
During `pull`, extraction at the experiment root restores `masts/M1664.csv`, etc.

### Example: Nested Directory

For a nested plaintext directory like `pre-masts/preprocessed/M1664/`, the
`.tar.zst` is placed **sibling** to the directory:

```cmd
cd /D experiments-archived\2026-07-13-松原\pre-masts
tar cf - preprocessed/M1664/final.csv preprocessed/M1664/merged.csv ... | zstd -T0 > preprocessed\M1664.tar.zst
del /Q preprocessed\M1664\final.csv preprocessed\M1664\merged.csv ...
```

During `pull`, extraction from `pre-masts/` restores `preprocessed/M1664/...`.

- `-T0` uses all CPU cores. On memory-constrained systems, omit it or use `-T1`.

---

## Step 6: Create `ARCHIVE.md`

Create `ARCHIVE.md` in the archive root:

```markdown
# Archive: <experiment-name>

- **Source experiment**: `projects/<original-dir-name>/`
- **Archive date**: <yyyy-mm-dd>
- **Archive policy**: DVC plaintext files compressed into `.tar.zst` per
  directory. Parquet files tracked individually. Git-tracked files (.toml,
  .json, .yaml, .yml, .md, .py, Justfile) committed directly.

## DVC-Tracked Archives

| Archive File | Original Directory | Contents |
|---|---|---|
| `<name>.tar.zst` | `<relative/path/>` | One-line description |

## DVC-Tracked Individual Files

| File | Size | Description |
|---|---|---|
| `<path/to/file.parquet>` | `<size>` | Description |

## Git-Tracked Files

- `justfile.archive`
- `deploy.py`
- `<path/to/config.toml>`
- ...

## Deploy (Restore for Replay)

```bash
# From the repository root. Restores DVC data, extracts archives, copies
# the payload to the target, renames justfile.archive -> Justfile, and
# strips read-only attributes so pipeline steps can rewrite raw/*.parquet.
# The deployed directory is NOT DVC-tracked.
uv run python experiments-archived/<archive-dir-name>/deploy.py projects/<new-project-name>
```

For raw data access without deploying: `dvc pull -R
experiments-archived/<archive-dir-name>/`, then extract each `.tar.zst`
from the directory containing it.
```

Fill in every table row with actual content from the archive.

---

## Step 7: Pristine `justfile.archive` + Deploy Script

The copied `Justfile` is NEVER modified. Rename it and add the deploy script:

```cmd
ren %DEST%\Justfile justfile.archive
copy /Y <skill-dir>\references\deploy.py %DEST%\deploy.py
```

**Rules:**
- `justfile.archive` is a PRISTINE byte-copy of the original project's
  Justfile. No `PROJECT`/`ROOT` rewrites, no added recipes — mutation causes
  drift (bug fixes would have to be re-applied inside every archive copy).
  It works unmodified when deployed under `projects/<name>/` because
  `PROJECT_NAME` derives from the directory name at runtime.
- `deploy.py` (see `@references/deploy.py`) is the ONLY supported restore
  path. It runs `dvc pull -R <archive>`, extracts every `.tar.zst` from the
  directory containing it, copies the payload to the target excluding DVC
  metadata (`*.dvc`, `*.tar.zst`, `.gitignore`, `ARCHIVE.md`, `deploy.py`),
  renames `justfile.archive` → `Justfile`, strips read-only attributes, and
  sanity-checks the result.
- The deployed target is NOT DVC-tracked — pipeline steps may rewrite
  `raw/*.parquet` and other files freely. NEVER run the pipeline inside
  `experiments-archived/`: DVC-pulled files may be read-only hardlinks, and
  rewriting them can corrupt the shared DVC cache.
- Why the read-only strip matters: DVC-pulled files carry the read-only
  attribute, `robocopy /COPY:DAT` preserves it, and Julia then fails with
  `SystemError: opening file ... Permission denied` when rewriting outputs.

---

## Step 8: Register with DVC

Run `dvc add` explicitly for **every** `.tar.zst` and **every** `.parquet` file.
Do NOT use `dvc add -R` or glob patterns — each file gets its own invocation:

```cmd
dvc add experiments-archived\%ARCHIVE_DIR%\masts.tar.zst
dvc add experiments-archived\%ARCHIVE_DIR%\mesos.tar.zst
dvc add experiments-archived\%ARCHIVE_DIR%\raw\site_data.parquet
dvc add experiments-archived\%ARCHIVE_DIR%\raw\meso_data.parquet
... (one per .tar.zst and .parquet file)
```

Each `dvc add` creates a `.dvc` file and adds the original to `.gitignore`.
Both must be committed.

Confirm:
```cmd
dvc status -R experiments-archived\%ARCHIVE_DIR%\
```

---

## Step 9: Stage Everything in Git

```cmd
git add experiments-archived\%ARCHIVE_DIR%\
```

This stages `ARCHIVE.md`, the updated `Justfile`, all `.dvc` files, all
git-tracked files, and DVC-generated `.gitignore` entries.

Verify:
```cmd
git status experiments-archived\%ARCHIVE_DIR%\
```

---

## Step 10: Report Summary

Emit a summary:

- Archive location
- Number of `.tar.zst` archives created
- Number of `.parquet` files tracked
- Number of git-tracked files
- Total archive size (approximate)
- Next steps:
  - `git commit -m "archive: <description>"`
  - `dvc push` to upload to remote storage
  - Optional: `dvc gc` to clean the local cache

---

## Error Handling

### `zstd` or `tar` Not Found

Windows 10 build 17063+ ships `tar`. `zstd` must be installed separately
(`winget install zstd` or `scoop install zstd`). Verify:

```cmd
where tar
where zstd
```

If either is missing, report it and stop.

### `dvc add` Fails

If a file is already tracked (`.dvc` file exists), the warning is harmless —
skip it. If `dvc add` fails with a permission/lock error, ensure no other DVC
process is running (`tasklist | findstr dvc`) and retry.

### Archive Directory Already Exists

Handled by collision logic in Step 2. If all numbered variants are exhausted
(extremely unlikely), ask the user for a custom name.

### Large Files (> 500 MB)

The explore agent in Step 1 flags these. Parquet files stay as individual DVC
files. Plaintext files may be slow to compress — warn the user.
