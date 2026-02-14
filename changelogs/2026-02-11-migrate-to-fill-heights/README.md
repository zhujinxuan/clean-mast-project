# Migration: extrapolate → fill_heights

**Date:** 2026-02-11  
**Type:** Breaking Change  
**Scope:** packages/cleanmast

## Overview

The old `extrapolate` module has been replaced with the new, more comprehensive `fill_heights` module. This migration provides better architecture, more features, and improved code quality.

## Key Changes

### New Features
- **Configurable deg_diff_limit**: `--deg-diff-limit` option (default 1.125 deg/m)
- **Default heights**: Changed to 125, 140, 160m
- **Separate output directories**: 
  - `reconstruct-meso-fill-heights/`
  - `representative-year-fill-heights/`
- **WS filtering**: Filter timestamps by wind speed > 2.5 m/s for reliable WD
- **Base height constraint**: Forces fit through (0,0) for physical correctness
- **Polars-native**: Expression-based implementations throughout

### Removed
- `extrapolate` module and CLI commands
- `--output-dir` option (replaced by automatic separate dirs)

## Architecture Decision Records

See individual ADR files for detailed rationale:
- [ADR-001: fill-heights Architecture](ADR-001-fill-heights-architecture.md)
- [ADR-002: WS Filtering](ADR-002-ws-filtering.md)
- [ADR-003: Base Height Constraint](ADR-003-base-constraint.md)
- [ADR-004: Polars-Native Implementation](ADR-004-polars-native.md)

## Migration Guide

See [MIGRATION-GUIDE.md](MIGRATION-GUIDE.md) for detailed migration instructions.

## Statistics
- **Tests:** 104 passing (fill_heights module)
- **Type Errors:** 0
- **Files Changed:** 50+
- **Lines Changed:** +2000/-1500
