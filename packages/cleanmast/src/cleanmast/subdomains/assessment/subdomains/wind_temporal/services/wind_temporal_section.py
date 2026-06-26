"""Wind temporal analysis subsection.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

from cleanmast.subdomains.assessment.subdomains.wind_temporal.entities.daily_pattern_atom import (
    SingleMastDailyPatternAtom,
)
from cleanmast.subdomains.assessment.subdomains.wind_temporal.entities.daily_power_pattern_atom import (
    SingleMastDailyPowerPatternAtom,
)
from cleanmast.subdomains.assessment.subdomains.wind_temporal.entities.monthly_daily_power_atom import (
    SingleMastMonthlyDailyPowerAtom,
)
from cleanmast.subdomains.assessment.subdomains.wind_temporal.entities.monthly_daily_wind_atom import (
    SingleMastMonthlyDailyWindAtom,
)
from cleanmast.subdomains.assessment.subdomains.wind_temporal.entities.monthly_pattern_atom import (
    SingleMastMonthlyPatternAtom,
)
from cleanmast.subdomains.assessment.subdomains.wind_temporal.entities.monthly_power_pattern_atom import (
    SingleMastMonthlyPowerPatternAtom,
)
from cleanmast.subdomains.assessment.shared.utils.subsection_renderer import (
    render_subsection_content,
)
from cleanmast.subdomains.assessment.shared.ir_types import (
    TypstHeading,
    TypstSection,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.assessment.shared.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.subdomains.wind_temporal.services._calculator import (
    WindTemporalAnalyzer,
)
from cleanmast.subdomains.assessment.subdomains.wind_temporal.services._builder import (
    WindTemporalSectionBuilder,
)
from cleanmast.subdomains.assessment.shared.protocols.report_atom import (
    ReportAtom,
)
from cleanmast.subdomains.assessment.shared.collections.atom_collection import (
    AtomCollection,
)


@dataclass(frozen=True)
class WindTemporalService:
    """Service for wind temporal (timeseries) analysis.

    Renders 6 temporal atoms for each mast:
    1. SingleMastMonthlyPatternAtom - Monthly wind pattern
    2. SingleMastMonthlyPowerPatternAtom - Monthly power density pattern
    3. SingleMastDailyPatternAtom - Daily (24h) wind pattern
    4. SingleMastDailyPowerPatternAtom - Daily (24h) power density pattern
    5. SingleMastMonthlyDailyWindAtom - Monthly-daily combined wind pattern
    6. SingleMastMonthlyDailyPowerAtom - Monthly-daily combined power pattern
    """

    atoms: AtomCollection
    title: str = "风速时序分析"

    @classmethod
    def generate(
        cls,
        items: list[tuple[SingleMastAnalysisInput, SingleMastMeta]],
    ) -> "WindTemporalService":
        """Generate wind temporal analysis section.

        Performs all 3 analysis methods (daily, monthly, monthly_daily)
        and builds the 6 temporal pattern atoms for each mast.

        Args:
            items: List of (input_data, meta) tuples for multi-mast aggregation.

        Returns:
            WindTemporalService containing temporal pattern analysis
        """
        collection_dict: dict[str, list[ReportAtom]] = {}
        for input_data, item_meta in items:
            analyzer = WindTemporalAnalyzer()
            daily_result = analyzer.analyze_daily_pattern(input_data)
            monthly_result = analyzer.analyze_monthly_pattern(input_data)
            monthly_daily_result = analyzer.analyze_monthly_daily(input_data)
            builder = WindTemporalSectionBuilder()
            atoms = builder.build(
                mast_name=item_meta.mast_name,
                time_series_result=daily_result,
                daily_result=daily_result,
                monthly_result=monthly_result,
                monthly_daily_result=monthly_daily_result,
            )
            collection_dict[item_meta.mast_name] = atoms
        collection = AtomCollection.from_dict(collection_dict)
        return cls(atoms=collection)

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section to IR nodes."""
        atom_configs = [
            (SingleMastMonthlyPatternAtom, True),
            (SingleMastMonthlyPowerPatternAtom, True),
            (SingleMastDailyPatternAtom, True),
            (SingleMastDailyPowerPatternAtom, True),
            (SingleMastMonthlyDailyWindAtom, False),
            (SingleMastMonthlyDailyPowerAtom, False),
        ]

        body = render_subsection_content(self.atoms, atom_configs, images_dir)
        return TypstSection(
            heading=TypstHeading(text=self.title),
            body=body,
            subsections=[],
        )


# Backward compatibility alias
WindTemporalSubsection = WindTemporalService
