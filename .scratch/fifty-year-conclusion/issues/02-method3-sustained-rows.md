# 02 — Method3 (EWM): restore sustained rows, fix empty narrative

**What to build:** `build_method3_atom` passes only the extreme DataFrame, so
the 极端风速模型法 tables show only 极端风速 rows and the sustained narrative
renders empty ("各高度结果如下：。" — visible in the songyuan report). The
sustained EWM values are computed but dropped at assembly.

Pass both sustained and extreme rows through (mirroring Method1/Method2
rendering) and repair the narrative so it never emits an empty list
sentence.

**Blocked by:** None — can start immediately

**Status:** done

## Scope

- `extreme_wind/assemble/__init__.py::build_method3_atom`: wire the sustained
  DataFrame alongside the extreme one.
- `extreme_wind/model/method3_atom.py`: render both wind_speed_type rows;
  narrative handles present/absent sustained rows without the dangling "：。"
  artifact.
- Tests for the sustained-row rendering and the narrative.

## Acceptance

- Songyuan 2.6.4 EWM tables show 持续风速 + 极端风速 rows per mast; no empty
  "各高度结果如下：。" anywhere in report.typ.
- `uv run python scripts/verify_baseline.py --package cleanmast` is green
