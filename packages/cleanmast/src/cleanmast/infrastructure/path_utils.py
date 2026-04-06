"""Path utilities for cross-platform path handling.

ADR-GUARDRAILS: platform-001-cross-platform-paths
Compliance: Cross-platform paths ✓
Description: Utility functions for consistent path string representation
"""

from pathlib import Path
from typing import Union

__all__ = ["to_posix_path"]


def to_posix_path(path: Union[str, Path]) -> str:
    """Convert a path to posix format (forward slashes).
    
    On Windows, str(Path) produces backslashes. This function ensures
    forward slashes are used consistently across all platforms.
    
    Args:
        path: A string path or Path object
        
    Returns:
        String path with forward slashes
        
    Examples:
        >>> to_posix_path("C:\\Users\\test")
        'C:/Users/test'
        >>> to_posix_path(Path("/home/user"))
        '/home/user'
    """
    if isinstance(path, str):
        path = Path(path)
    return path.as_posix()
