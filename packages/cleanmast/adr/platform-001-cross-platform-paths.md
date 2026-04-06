---
id: platform-001-cross-platform-paths
name: cross-platform-paths
description: Cross-platform path handling using POSIX format
tags: [platform, path, windows, cross-platform]
applies_when:
  - serializing paths to strings
  - displaying paths in logs/output
  - storing paths in configuration files
  - working with Path objects
---

# PLATFORM-001: Cross-Platform Path Handling

## Constraint (MUST)
1. **Always use `path.as_posix()`** for converting Path objects to strings
2. **Use `cleanmast.infrastructure.path_utils.to_posix_path()`** as the utility wrapper
3. **Forward slashes (`/`)** are the standard for all path string representations
4. **Never use `str(path)`** for display, config, serialization, or logging
5. **Windows paths** in `str(Path)` produce backslashes (`\\`) which cause issues

## Rationale (WHY)

On Windows, `str(Path)` produces backslashes (`\\`) which causes multiple problems:
- Config files with backslashes break cross-platform compatibility
- Logs and output with backslashes are confusing and inconsistent
- Error messages have inconsistent formatting across platforms
- Backslashes in strings require escaping, leading to readability issues

POSIX paths (`/`) work consistently on all platforms. Python's Pathlib handles the actual OS operations correctly; the POSIX format is purely for string representation.

## Anti-Pattern (AVOID)

```python
# ❌ Using str(path) for display/config
config["output_path"] = str(output_path)  # NEVER - produces backslashes on Windows

# ❌ Using str(path) for logging
logger.info(f"Processing {str(file_path)}")  # NEVER - inconsistent formatting

# ❌ Using str(path) for serialization
json.dumps({"path": str(data_path)})  # NEVER - breaks cross-platform compatibility
```

## Correct Pattern (USE)

```python
from cleanmast.infrastructure.path_utils import to_posix_path

# ✅ Using the utility function
config["output_path"] = to_posix_path(output_path)

# ✅ Using path.as_posix() directly
logger.info(f"Processing {file_path.as_posix()}")

# ✅ Consistent serialization
json.dumps({"path": data_path.as_posix()})
```

## Phase Links
| Phase | File |
|-------|------|
| Plan | [on-plan.md](./phases/platform-001-cross-platform-paths/on-plan.md) |
| Review Plan | [review-plan.md](./phases/platform-001-cross-platform-paths/review-plan.md) |
| Code | [code.md](./phases/platform-001-cross-platform-paths/code.md) |
| Review | [review-implementation.md](./phases/platform-001-cross-platform-paths/review-implementation.md) |

## References
- Utility: `packages/cleanmast/src/cleanmast/infrastructure/path_utils.py`
