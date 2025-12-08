"""Placeholder test for cleanmast."""

import cleanmast
from cleanmast import cli


def test_cleanmast_import():
    """Test that the package can be imported."""
    assert cleanmast.__version__ == "0.1.0"


def test_cleanmast_cli_import():
    """Test that CLI can be imported."""
    assert cli.main is not None
