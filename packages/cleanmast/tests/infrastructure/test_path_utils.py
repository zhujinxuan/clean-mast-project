"""Tests for path_utils module."""

from pathlib import Path

from cleanmast.infrastructure.path_utils import to_posix_path


def test_to_posix_path_with_windows_string():
    """Test converting Windows string path with backslashes."""
    result = to_posix_path("C:\\Users\\test")
    assert result == "C:/Users/test"


def test_to_posix_path_with_unix_string():
    """Test converting Unix string path."""
    result = to_posix_path("/home/user")
    assert result == "/home/user"


def test_to_posix_path_with_path_object():
    """Test converting Path object."""
    result = to_posix_path(Path("C:/Users/test"))
    assert result == "C:/Users/test"


def test_to_posix_path_with_relative_path():
    """Test converting relative path."""
    result = to_posix_path("./relative/path")
    assert result == "relative/path"


def test_to_posix_path_with_relative_backslashes():
    """Test converting relative path with backslashes."""
    result = to_posix_path(".\\relative\\path")
    assert result == "relative/path"


def test_to_posix_path_with_single_component():
    """Test converting single path component."""
    result = to_posix_path("filename.txt")
    assert result == "filename.txt"


def test_to_posix_path_with_deep_nesting():
    """Test converting deeply nested path."""
    result = to_posix_path("a\\b\\c\\d\\e\\f")
    assert result == "a/b/c/d/e/f"


def test_to_posix_path_preserves_trailing_slash_info():
    """Test that path normalization handles trailing separators appropriately."""
    # Path objects normalize away trailing slashes
    result = to_posix_path("/home/user/")
    assert result == "/home/user"


def test_to_posix_path_with_mixed_separators():
    """Test path with mixed forward and back slashes."""
    result = to_posix_path("C:/Users\\test/path")
    assert result == "C:/Users/test/path"


def test_to_posix_path_idempotent():
    """Test that applying to_posix_path twice gives same result."""
    first = to_posix_path("C:\\Users\\test")
    second = to_posix_path(first)
    assert first == second
