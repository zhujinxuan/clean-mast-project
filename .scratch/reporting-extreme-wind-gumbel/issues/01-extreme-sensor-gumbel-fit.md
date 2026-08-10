# 01 — Extreme-sensor Gumbel fit for extreme-wind QQ plot

**What to build:** Reporting currently fits Gumbel only on avg (sustained) sensors; the max-sensor (extreme) Gumbel fit is missing, so the extreme-wind QQ plot always renders empty. Fit Gumbel on max sensors too, so the extreme QQ plot shows data.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Gumbel fit is computed for max (extreme) sensors, not only avg sensors
- [ ] Extreme-wind QQ plot renders with data
- [ ] `uv run python scripts/verify_baseline.py --package cleanmast` is green

## Comments

- Converted 2026-08-10 from reporting `drift-log.md` entry #8 (2026-06-26, nature CONTENT) during the drift-log → ticket migration. Original refs: `section.py:287`, `compute/__init__.py:371` — line numbers are from 2026-06, verify before trusting them.
