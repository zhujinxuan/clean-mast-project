# 03 — temporal_heights discovery: 120–160 band-when-available

**What to build:** Change `_discover_temporal_heights` in `configuration/services/recommend_report.py` from "all WS avg heights" to band-when-available: 120–160m WS avg heights when any exist, else all WS avg heights. Today lidar projects get 13-column temporal tables (40–200m in kp) dominated by heights nobody reads; but a pure band rule yields an empty list on short masts, and `WindTemporalSection` hard-fails on empty.

**Blocked by:** None — can start immediately (shared files with 01/02, see spec.md)

**Status:** ready-for-agent

## Scope

- `configuration/services/recommend_report.py`: `_discover_temporal_heights` gains the 120–160 filter with unfiltered fallback.
- `WindTemporalSection` itself is unchanged — it already consumes config faithfully.
- Regenerate affected test-data configs; the kp report's temporal section shrinks from 13 heights to 4 (120/125/140/160). DVC-tracked expected outputs referencing temporal content need a refresh.

## Acceptance

- [ ] Recommend emits 120–160 WS avg heights when available, all WS avg heights otherwise
- [ ] A synthetic short-mast input (no 120–160 sensors) still produces a non-empty `temporal_heights`
- [ ] kp-202603-report verify passes with the trimmed temporal section
- [ ] `configuration/spec.md` documents the band-when-available rule and its short-mast rationale
- [ ] Tests cover band, fallback, and empty-sensor edge cases
- [ ] `uv run python scripts/verify_baseline.py --package cleanmast` is green

## Comments

- Decided 2026-08-25 (grilling round): band-when-available, not band-only. Fallback preserves report generation for met masts below 120m.
- Users who want other temporal height sets trim `temporal_heights` by hand — note: `just verify` regenerates the config via recommend, so hand trims survive only in the manifest (`verify.toml`) path, not the just-mode path. That divergence is tracked in `.scratch/dev-tools-split/issues/01-verify-command-migration.md`.
