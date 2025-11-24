# Contributing to Pre-processor Mast Data

This document provides guidelines for contributing to the pre-processor-mast-data project.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd pre-processor-mast-data
   ```

2. **Install dependencies**
   ```bash
   uv pip install -e .
   ```

3. **Verify installation**
   ```bash
   uv run type-normalizer --help
   uv run col-name-normalizer --help
   ```

## Project Structure

```
pre-processor-mast-data/
├── pre_processor_mast_data/    # Main package
│   ├── __init__.py
│   ├── type_normalizer.py      # Type normalization tool
│   └── col_name_normalizer.py  # Column name normalization tool
├── datas/by/                   # Sample data and configs
├── docs/                       # Documentation
├── pyproject.toml             # Project configuration
└── README.md                  # Main documentation
```

## Code Standards

### Python Code Requirements

- **Type Annotations**: All functions must have complete type annotations
- **Pydantic Models**: Use Pydantic for configuration validation
- **Click CLI**: Use Click for command-line interfaces
- **Error Handling**: Provide graceful error handling with informative messages
- **Function Size**: Keep functions short and focused (single responsibility)

### Example Function Structure

```python
from typing import List, Optional
from pathlib import Path
import pandas as pd
from pydantic import BaseModel

def process_data(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """Process dataframe by converting specified columns to float.
    
    Args:
        df: Input dataframe
        columns: List of column names to convert
        
    Returns:
        Processed dataframe with converted columns
        
    Raises:
        ValueError: If required columns are missing
    """
    # Implementation here
    pass
```

### Configuration Validation

All configuration should use Pydantic models:

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Union

class Config(BaseModel):
    """Configuration model with validation."""
    
    input_path: str = Field(..., description="Path to input file")
    output_path: str = Field(..., description="Path to output file")
    columns: List[str] = Field(..., description="List of columns to process")
```

## Adding New Features

### Adding a New Normalizer

1. **Create the module**: Add a new file in `pre_processor_mast_data/`
2. **Define configuration**: Create a Pydantic model for configuration
3. **Implement processing**: Write the main processing function
4. **Add CLI**: Use Click to create the command-line interface
5. **Update pyproject.toml**: Add the new script entry point
6. **Add tests**: Create test cases for the new functionality
7. **Update documentation**: Add command reference and examples

### Configuration File Guidelines

- Use TOML format for all configuration files
- Place config files in the same directory as data files
- Use relative paths from config file location
- Provide clear descriptions for all parameters
- Include example configurations

## Testing

### Manual Testing

Test with the sample data files:

```bash
# Test type normalizer
uv run type-normalizer datas/by/type-config-2501.toml

# Test column name normalizer
uv run col-name-normalizer datas/by/col-name-config-2501.toml
```

### Adding Test Data

When adding new test data:
1. Place data files in appropriate subdirectory under `datas/`
2. Create corresponding configuration files
3. Document the data source and format
4. Update examples in documentation

## Documentation

### Required Documentation

- **Command reference**: Document all CLI options and parameters
- **Configuration examples**: Provide complete, working examples
- **Format specifications**: Document expected input/output formats
- **Error handling**: Document common errors and solutions

### Documentation Structure

- `docs/commands.md` - Command-line tool reference
- `docs/nrg-format.md` - NRG format specification
- `docs/contributing.md` - This file
- `README.md` - Main project documentation

## Submitting Changes

1. **Test thoroughly**: Ensure all existing functionality still works
2. **Update documentation**: Update relevant documentation files
3. **Follow code standards**: Ensure code meets project standards
4. **Provide examples**: Include configuration examples for new features

## Common Issues and Solutions

### Path Resolution
- Always use `Path` objects for file operations
- Resolve paths relative to configuration file location
- Handle both absolute and relative paths gracefully

### Data Format Handling
- Support both CSV and DAT file formats
- Handle various header row configurations
- Provide clear error messages for unsupported formats

### Configuration Validation
- Use Pydantic for all configuration validation
- Provide helpful error messages for invalid configurations
- Support both simple and complex configuration patterns
