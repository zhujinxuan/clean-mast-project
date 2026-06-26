"""Wind frequency section.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

from cleanmast.subdomains.assessment.shared.value_objects.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.assessment.shared.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.shared.protocols.report_atom import ReportAtom
from cleanmast.subdomains.assessment.subdomains.wind_frequency.services._builder import (
    WindFrequencySectionBuilder,
)
from cleanmast.subdomains.assessment.subdomains.wind_frequency.services._calculator import (
    WindFrequencyCalculator,
)
from ..entities.wind_distribution_subgrid import (
    SingleMastWindDistributionSubgridAtom,
)
from ..entities.wind_frequency_hours_atom import (
    SingleMastWindFrequencyHoursAtom,
)
from ..entities.wind_power_hours_atom import (
    SingleMastWindPowerHoursAtom,
)
from ..entities.wind_productive_range_atom import (
    SingleMastWindProductiveRangeAtom,
)
from ....shared.utils.subsection_renderer import (
    render_subsection_content,
)
from ....shared.ir_types import (
    TypstHeading,
    TypstSection,
)
from ....shared.collections.atom_collection import (
    AtomCollection,
)


@dataclass(frozen=True)
class WindFrequencyService:
    """Specialized service for wind frequency analysis."""

    atoms: AtomCollection
    title: str = "风速频率分析"

    @classmethod
    def generate(
        cls,
        items: list[tuple[SingleMastAnalysisInput, SingleMastMeta]],
    ) -> "WindFrequencyService":
        """Generate wind frequency distribution section.

        Args:
            items: List of (input_data, meta) tuples for multi-mast aggregation.

        Returns:
            WindFrequencyService containing wind frequency analysis
        """
        collection_dict: dict[str, list[ReportAtom]] = {}
        for input_data, item_meta in items:
            calculator = WindFrequencyCalculator()
            result = calculator.analyze_by_height(input_data)
            builder = WindFrequencySectionBuilder()
            atoms = builder.build(
                mast_name=item_meta.mast_name,
                results=[result],
            )
            collection_dict[item_meta.mast_name] = atoms
        collection = AtomCollection.from_dict(collection_dict)
        return cls(atoms=collection)

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section to IR nodes."""
        atom_configs = [
            (SingleMastWindFrequencyHoursAtom, True),
            (SingleMastWindPowerHoursAtom, True),
            (SingleMastWindDistributionSubgridAtom, True),
            (SingleMastWindProductiveRangeAtom, True),
        ]
        body = render_subsection_content(self.atoms, atom_configs, images_dir)
        return TypstSection(
            heading=TypstHeading(text=self.title),
            body=body,
            subsections=[],
        )


# Backward compatibility alias
WindFrequencySubsection = WindFrequencyService
