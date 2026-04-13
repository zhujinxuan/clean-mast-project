from pathlib import Path

import pytest


@pytest.fixture
def fixture_docx_path():
    fixture_dir = Path(__file__).parent / "fixtures" / "docx"

    def _loader(name: str) -> Path:
        if not name.endswith(".docx"):
            name = f"{name}.docx"
        path = fixture_dir / name
        if not path.exists():
            raise FileNotFoundError(f"Fixture DOCX not found: {path}")
        return path

    return _loader
