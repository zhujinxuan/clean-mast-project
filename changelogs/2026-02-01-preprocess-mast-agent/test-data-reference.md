# Test Data Reference

This document catalogs real-world test files and projects for validating the Preprocess Mast Agent.

---

## Purpose

- Collect examples of real wind measurement data files
- Document edge cases and variations encountered in practice
- Provide test fixtures for development and validation
- Track which files/projects have been tested

---

## Test File Categories

### 1. Encoding Variations

| File/Source | Original Encoding | Notes |
|-------------|-------------------|-------|
| *To be determined* | GB2312/GBK | Common in Chinese wind farms |
| *To be determined* | Latin-1 | European sites |
| *To be determined* | UTF-8 with BOM | Windows-generated files |
| *To be determined* | Windows-1252 | Legacy equipment |

### 2. Header Patterns

| Source | Header Lines | Pattern Type | Notes |
|--------|--------------|--------------|-------|
| *To be determined* | 1-2 lines | Simple CSV | Standard export format |
| *To be determined* | 3-5 lines | NRG-style | Equipment metadata + column names |
| *To be determined* | 5-10 lines | Lidar | Complex header with attributes |
| *To be determined* | Variable | Mixed | Multiple file formats in same mast |

### 3. Timestamp Formats

| Format | Example | Common In |
|--------|---------|-----------|
| ISO 8601 | `2024-01-15 14:30:00` | Standard |
| Date only | `2024/01/15` | Daily summaries |
| Custom | `15-Jan-2024 14:30` | Legacy systems |
| Excel | `45276.6041667` | Excel exports |
| Unix | `1705330200` | Unix timestamp |

### 4. Coordinate Formats

| Format | Example | Region |
|--------|---------|--------|
| WGS84 decimal | `39.9042, 116.4074` | Global standard |
| WGS84 DMS | `39°54'15.12"N, 116°24'26.64"E` | Legacy reports |
| CGCS2000 3-degree | Zone 39, X=123456.78, Y=876543.21 | China |
| Local grid | EX=1000.0, EY=2000.0 | Project-specific |
| Geohash | `wx4g0b9c` | Compact encoding |

### 5. Edge Cases

| Case | Description | Test Priority |
|------|-------------|---------------|
| Binary files | `.dat`, `.bin` files mixed with CSV | High |
| Empty files | Zero-byte files | Medium |
| Corrupted data | Truncated files, bad encoding | Medium |
| Duplicate columns | Same column name appears twice | Medium |
| Missing timestamps | No recognizable time column | High |
| Multiple locations | Header vs footer have different coords | Low |
| Equipment change | Same mast, different sensor configs | High |
| Gap in data | Missing time periods | Medium |
| Overlapping periods | Duplicate timestamps | High |

---

## Test Projects

### Project Registry

| Project ID | Location | Mast Count | Status | Notes |
|------------|----------|------------|--------|-------|
| *To be determined* | - | - | Not tested | - |

### Project Structure Template

```
projects/{project-id}/
├── pre-masts/
│   ├── {mast-1}/
│   │   ├── raw files...
│   │   └── expected output...
│   ├── {mast-2}/
│   └── ...
└── documentation/
    ├── site-info.md
    ├── equipment-specs.md
    └── known-issues.md
```

---

## Test Scenarios

See [plan.md](plan.md) for the 7-phase workflow definition. Test scenarios below map to workflow phases:

### Basic Functionality (Workflow Phases 1-3)

- [ ] Single mast, single file, UTF-8, standard CSV
- [ ] Single mast, multiple files, same format
- [ ] Single mast, multiple files, different formats

### Encoding & Edge Cases (Workflow Phase 2)

- [ ] Mixed encoding files in same mast
- [ ] Binary files mixed with text
- [ ] Empty or corrupted files
- [ ] Files with no detectable data range

### Complex Grouping (Workflow Phases 4-6)

- [ ] Equipment replacement (different sensor configs)
- [ ] Multiple time periods with gaps
- [ ] Overlapping timestamps
- [ ] Files from different locations mixed

### Scale & Performance (All Workflow Phases)

- [ ] Large mast (>100 files)
- [ ] Multiple masts in parallel
- [ ] Long time series (>5 years)

---

## File Inventory

### Files to Test (Pending Selection)

| File Path | Source Project | Category | Selected For Testing |
|-----------|----------------|----------|---------------------|
| *To be determined* | - | - | ⏳ Pending |

---

## Testing Checklist

For each selected test file/project:

- [ ] Document file characteristics (encoding, format, size)
- [ ] Record expected behavior (success/warning/error)
- [ ] Run through agent workflow
- [ ] Compare output with expected results
- [ ] Document any issues or unexpected behavior
- [ ] Add to regression test suite

---

## Notes

- This document will be populated as we identify specific test files and projects
- Test data should be anonymized if containing sensitive location information
- Prioritize files that represent common real-world scenarios
