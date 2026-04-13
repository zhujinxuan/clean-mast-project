from __future__ import annotations

import pytest
from typst_ir.polish.config import (
    PolishConfig,
    RenumberConfig,
    StyleConfig,
    load_config,
)


class TestLoadConfig:
    def test_valid_config_loads_correctly(self, tmp_path):
        toml = tmp_path / "polish.toml"
        toml.write_text(
            '\n'
            '[styles."Heading 1"]\n'
            'font_name = "Arial"\n'
            'font_size = 16.0\n'
            '\n'
            '[styles."Normal"]\n'
            'font_name = "Times New Roman"\n'
            'font_name_chinese = "SimSun"\n'
            'line_spacing_before = 6.0\n'
            'line_spacing_after = 6.0\n'
            '\n'
            '[renumber]\n'
            'headings = true\n'
            'figures = false\n'
            'tables = true\n',
            encoding="utf-8",
        )

        cfg = load_config(toml)

        assert isinstance(cfg, PolishConfig)
        assert set(cfg.styles.keys()) == {"Heading 1", "Normal"}

        h1 = cfg.styles["Heading 1"]
        assert isinstance(h1, StyleConfig)
        assert h1.font_name == "Arial"
        assert h1.font_size == 16.0
        assert h1.font_name_chinese is None

        normal = cfg.styles["Normal"]
        assert normal.font_name == "Times New Roman"
        assert normal.font_name_chinese == "SimSun"
        assert normal.line_spacing_before == 6.0
        assert normal.line_spacing_after == 6.0

        assert isinstance(cfg.renumber, RenumberConfig)
        assert cfg.renumber.headings is True
        assert cfg.renumber.figures is False
        assert cfg.renumber.tables is True

    def test_unknown_top_level_key_raises(self, tmp_path):
        toml = tmp_path / "polish.toml"
        toml.write_text(
            '\n'
            '[styles."Heading 1"]\n'
            'font_name = "Arial"\n'
            '\n'
            '[renumber]\n'
            'headings = true\n'
            '\n'
            '[unknown_section]\n'
            'key = "value"\n',
            encoding="utf-8",
        )

        with pytest.raises(ValueError) as exc_info:
            load_config(toml)

        assert "unknown_section" in str(exc_info.value)

    def test_unknown_style_key_raises(self, tmp_path):
        toml = tmp_path / "polish.toml"
        toml.write_text(
            '\n'
            '[styles."Heading 1"]\n'
            'font_name = "Arial"\n'
            'unknown_key = 123\n'
            '\n'
            '[renumber]\n'
            'headings = true\n',
            encoding="utf-8",
        )

        with pytest.raises(ValueError) as exc_info:
            load_config(toml)

        assert "unknown_key" in str(exc_info.value)

    def test_missing_file_raises(self, tmp_path):
        missing = tmp_path / "does_not_exist.toml"

        with pytest.raises(ValueError) as exc_info:
            load_config(missing)

        assert str(missing) in str(exc_info.value)

    def test_line_spacing_parses_correctly(self, tmp_path):
        toml = tmp_path / "polish.toml"
        toml.write_text(
            '\n'
            '[styles."Normal"]\n'
            'font_name = "Times New Roman"\n'
            'line_spacing = 1.15\n'
            '\n'
            '[renumber]\n'
            'headings = true\n',
            encoding="utf-8",
        )

        cfg = load_config(toml)
        normal = cfg.styles["Normal"]
        assert normal.line_spacing == 1.15
