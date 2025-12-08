# Project Compression Tool - Requirements

## Problem Statement

The `projects/` directory grows continuously as more wind measurement projects
are processed. Most projects are "done and archived" after completion, but
their intermediate CSV files (created in multiple processing steps) continue
to occupy significant disk space.

## User Requirements

### What to Compress
- Entire project directories under `projects/`
- Projects are mostly done and archived (not actively worked on)
- CSV files created in multiple processing steps are the main disk consumers

### Compression Criteria
- **Age-based**: Compress projects older than a certain threshold
- **Age calculation**: Based on last modification time of ANY file within the
  project directory
- **Default threshold**: 30 days

### Compression Format
- **7z format** for optimal compression ratio on CSV files

### Archive Storage
- **Separate archive directory** (not mixed with active projects)
- **Configurable** via `.env` file
- **Default location**: `./old-projects/`

### Usage Pattern
- **Manual trigger**: User runs the script when needed
- Can specify specific project(s) to compress OR compress all qualifying projects
- Manual decompression is acceptable when old projects need to be accessed

### Tooling Preferences
- **Python implementation** (not Bash/PowerShell - easier to maintain)
- Will be implemented as a **uv project** under the repository root

### Safety & Usability
- Dry-run mode to preview what will be compressed
- Verify archive integrity before deleting original files
- Analysis mode to understand current disk usage by project age

## Future Implementation

This will be developed as a separate Python project managed by `uv` in the
repository root. Implementation details and architecture will be discussed
when ready to start development.
