"""2.3.2 overview atoms — pipeline-flow intro paragraph and coverage table.

The flow intro states the processing chain and the standards each stage
follows (GB/T 37523-2019 cleaning, NB/T 31147-2018 tower shading); the
coverage atom renders the stats sentence and the per-mast × per-height
stage point-count table against the expected 10-minute grid.
"""

from pathlib import Path

from typing_extensions import override
from typst_ir import TypstParagraph, TypstTable

from cleanmast.subdomains.reporting.model import get_height_display_name
from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.cleaning.model.report_meta import (
    CleaningAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.model.schemas import (
    CleaningCoverageSchema,
    CleaningPlaceholderSchema,
)

MISSING_CELL = "—"

FLOW_INTRO_TEXT = (
    "数据处理按以下流程进行：数据清洗 → 塔影效应处理 → 同塔插补 → 异塔插补 → "
    "中尺度插补。数据清洗依据《风电场气象观测资料审核、插补与订正技术规范》"
    "（GB/T 37523-2019）对测风数据进行检验，不合理数据予以剔除；塔影效应处理依据"
    "《风电场工程风能资源测量与评估技术规范》（NB/T 31147-2018）对同高度双通道"
    "风速进行修正；清洗后的缺测数据依次采用同塔其他高度层、相关性合格的异塔及 "
    "ERA5 中尺度数据进行线性回归插补。"
)


class CleaningFlowIntroAtom(ReportAtom[CleaningPlaceholderSchema, CleaningAtomMeta]):
    """Renders the 2.3.2 opening paragraph describing the processing flow.

    Summary: the flow paragraph (``meta.text``). Table: none. Image: none.
    """

    @property
    @override
    def default_image_caption(self) -> str | None:
        return None

    @property
    @override
    def default_table_caption(self) -> str | None:
        return None

    @override
    def renderTable(self) -> TypstTable | None:
        return None

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        return [TypstParagraph(text=self.meta.text)]


class CleaningCoverageAtom(ReportAtom[CleaningCoverageSchema, CleaningAtomMeta]):
    """Renders the stage coverage stats sentence and point-count table.

    Summary: the stats sentence (``meta.text``, built by assemble from the
    per-mast analysis windows). Table: one row per mast × cleaning height
    with the per-stage valid-point counts, the cleaning delta
    (清洗剔除 in points and as a share of raw), and the post-cleaning
    availability (share of the expected 10-minute grid); a missing stage
    input renders as an em-dash, not a crash.
    """

    @property
    @override
    def default_image_caption(self) -> str | None:
        return None

    @property
    @override
    def default_table_caption(self) -> str | None:
        return "各塔主测风层风速数据清洗与插补各阶段数据点统计表"

    @override
    def renderTable(self) -> TypstTable | None:
        """Render as Typst table: mast × cleaning height stage coverage.

        Columns: 测风塔 | 高度(m) | 应有点数 | 原始点数 | 清洗后点数 |
        清洗剔除(点) | 清洗剔除(%) | 清洗后可用率(%) | 插补后点数 |
        插补后占比(%). 清洗剔除(点) = 原始 − 清洗后; 清洗剔除(%) is its
        share of 原始点数; 清洗后可用率 = 清洗后 ÷ 应有; 插补后占比 =
        插补后 ÷ 应有. Percentages carry one decimal; missing stages
        (null counts) render as —, as does 清洗剔除(%) when 原始 is 0.
        """
        rows: list[list[str]] = []
        for record in self.df.iter_rows(named=True):
            expected = int(record["expected_points"])
            raw = record["raw_points"]
            clean = record["clean_points"]
            rows.append([
                record["mast_name"],
                get_height_display_name(float(record["height"])),
                record["sensor_type"] if record["sensor_type"] else MISSING_CELL,
                str(expected),
                _count_cell(raw),
                _count_cell(clean),
                _removed_cell(raw, clean),
                _removed_pct_cell(raw, clean),
                _pct_cell(clean, expected),
                _count_cell(record["final_points"]),
                _pct_cell(record["final_points"], expected),
            ])
        return TypstTable(
            headers=[
                "测风塔",
                "高度(m)",
                "传感器类型",
                "应有点数",
                "原始点数",
                "清洗后点数",
                "清洗剔除(点)",
                "清洗剔除(%)",
                "清洗后可用率(%)",
                "插补后点数",
                "插补后占比(%)",
            ],
            data=rows,
            caption=self.default_table_caption,
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        return [TypstParagraph(text=self.meta.text)]


def _count_cell(points: int | None) -> str:
    """Render a point count; a missing stage (null) renders as an em-dash."""
    if points is None:
        return MISSING_CELL
    return str(int(points))


def _pct_cell(points: int | None, expected: int) -> str:
    """Render points/expected as a percentage with one decimal."""
    if points is None or expected <= 0:
        return MISSING_CELL
    return f"{points / expected * 100:.1f}"


def _removed_cell(raw: int | None, clean: int | None) -> str:
    """Render raw − clean (points removed by cleaning); — if a stage is missing."""
    if raw is None or clean is None:
        return MISSING_CELL
    return str(int(raw - clean))


def _removed_pct_cell(raw: int | None, clean: int | None) -> str:
    """Render (raw − clean) / raw with one decimal; — if a stage is missing or raw is 0."""
    if raw is None or clean is None or raw == 0:
        return MISSING_CELL
    return f"{(raw - clean) / raw * 100:.1f}"
