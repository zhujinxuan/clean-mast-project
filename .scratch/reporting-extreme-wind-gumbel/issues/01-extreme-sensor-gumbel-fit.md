# 01 — Extreme-sensor Gumbel fit for extreme-wind QQ plot

**What to build:** Reporting currently fits Gumbel only on avg (sustained) sensors; the max-sensor (extreme) Gumbel fit is missing, so the extreme-wind QQ plot always renders empty. Fit Gumbel on max sensors too, so the extreme QQ plot shows data.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Gumbel fit is computed for max (extreme) sensors, not only avg sensors
- [ ] Extreme-wind QQ plot renders with data
- [ ] `uv run python scripts/verify_baseline.py --package cleanmast` is green

## Comments

- Converted 2026-08-10 from reporting `drift-log.md` entry #8 (2026-06-26, nature CONTENT) during the drift-log → ticket migration. Original refs: `section.py:287`, `compute/__init__.py:371` — line numbers are from 2026-06, verify before trusting them.
- Investigation 2026-08-10 (scout, verified against code): **not fixed, but the fit is already computed and discarded.** `extreme_wind/section.py` (~line 413) runs `calculate_method2` on max-sensor five-day maxima and appends the result only to `m2_wind_rows`; no param rows are added for the extreme variant (comment "No Q-Q params for extreme variant", ~line 433). `Method2QQExtremeAtom.renderImage` (model/method2_atom.py:210-252) filters `wind_speed_type=='extreme'`, finds zero rows, returns `Path()`. Max-sensor data is already in the inputs (`max_sensor_by_height`, section.py:303-307); `SensorColumn.stat_type` distinguishes avg/max; schemas already accept `wind_speed_type='extreme'`. Fix = one file + one test: (1) in the extreme branch, also append a `GumbelParamRow` with `wind_speed_type='extreme'` (mu, beta, sample_count, sample_mean, sample_std, sample_data) from the existing result, and remove the comment; (2) extend `TestMaxSensorExtreme` in `tests/reporting/extreme_wind/test_section.py` to assert the extreme param row has non-null `sample_data` and the QQ atom returns a real path. Atoms/assemble/schemas need no changes.
