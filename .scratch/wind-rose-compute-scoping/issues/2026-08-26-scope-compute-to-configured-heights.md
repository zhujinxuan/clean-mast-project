# 2026-08-26 — wind_rose: scope compute to configured heights, warn only on configured-height pair loss

**What to build:** `WindRoseSection` currently runs `calculate_wind_rose` over
**all** WS avg sensors and filters the result to configured
`wind_rose_heights` afterwards (section.py `from_time_series`). Every WS avg
sensor without a same-height WD avg sensor logs a "Skipping WindSpeed avg
sensor …" warning in compute — 10 lines in kp-202603 (2 masts × 5 heights),
all about heights nobody configured and whose computed output is immediately
discarded. Change compute to only touch configured heights, and keep exactly
one sharpened warning: a **configured** height that lost its WD pair.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

## Agreed semantics (user decision 2026-08-26)

| Case | Behavior |
|---|---|
| Unconfigured height lacks WD pair | **Silent** — recommend never vetted it, report never shows it |
| Configured `wind_rose_heights` entry lacks WD pair | **Warn loudly** — config/data drift (hand-edited heights or dataset changed since `cleanmast recommend`); a configured height must never vanish silently from a financing-grade report |

Rationale: `_discover_wind_rose_heights` (recommend_report.py) already
recommends only exact WS+WD paired heights — the recommend output is fully
vetted, so report-time pairing warnings for unconfigured sensors are pure
noise and the pairing skip is a leftover from when compute owned the pairing
policy. A general "mast has WS without WD at height X" inventory belongs to
the future `cleanmast doctor` diagnostics command, not report generation.

## Scope

- `reporting/subdomains/wind_rose/compute.py`: `calculate_wind_rose` gains a
  heights scope (parameter or pre-filtered `TimeSeriesData`); the blanket
  pairing warning fires only for in-scope heights.
- `reporting/subdomains/wind_rose/section.py`: pass configured
  `wind_rose_heights` into compute instead of filtering after.
- Side benefit to keep: no wasted sector×month aggregation on discarded
  heights (5 heights/mast in kp-202603).
- `reporting/spec.md` wind_rose bullet: rewrite "未配对的 WS 高度在 compute
  阶段跳过并记录 warning" to the new semantics (compute is scoped to
  configured heights; only configured-height pair loss warns).
- Behavior delta: kp-202603 report logs lose the 10 skip lines; report.typ
  content unchanged (filtered-out heights never reached atoms).

## Acceptance

- [ ] Report generation emits no pairing warning for unconfigured heights
- [ ] A configured height missing its WD pair still warns (test: hand-built
      input with an unpairable configured height)
- [ ] kp-202603-report regenerates byte-identical report.typ (modulo
      image-hash lines)
- [ ] `reporting/spec.md` updated to the new semantics
- [ ] `uv run python scripts/verify_baseline.py --package cleanmast` is green

## Comments

- Surfaced 2026-08-26 while diagnosing turbulence report output; user
  reviewed the design table above and approved ("reporting shall not warn"
  for unconfigured heights, keep the configured-height warning).
