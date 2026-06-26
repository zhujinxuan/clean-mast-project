"""Extreme wind service implementation.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass, replace
from pathlib import Path

from cleanmast.subdomains.assessment.subdomains.extreme_wind.services.iec_standards_subsection import (
    FiftyYearMaxWindIECStandardsSubsection,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.services.method1_subsection import (
    Method1Subsection,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.services.method2_subsection import (
    Method2Subsection,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.services.method3_subsection import (
    Method3Subsection,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.services.summary_subsection import (
    SummarySubsection,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.services._calculator_method1 import (
    Method1Calculator,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.services._calculator_method2 import (
    Method2Calculator,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.services._calculator_method3 import (
    Method3Calculator,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.services._builder_method1 import (
    Method1Builder,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.services._builder_method2 import (
    Method2Builder,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.services._builder_method3 import (
    Method3Builder,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.services._builder_summary import (
    SummaryBuilder,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.entities.iec_standards_atom import (
    IEC_STANDARDS_DATA,
    NoMastIECStandardsAtom,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.value_objects.schemas import (
    IECStandardsSchema,
)
from cleanmast.subdomains.assessment.shared.protocols.report_atom import (
    ReportAtom,
)
from cleanmast.subdomains.assessment.shared.collections.atom_collection import (
    AtomCollection,
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
from cleanmast.subdomains.assessment.subdomains.extreme_wind.value_objects.report_meta import (
    NoMastMeta,
)


def _filter_fifty_year_heights(
    input_data: SingleMastAnalysisInput,
) -> list[float]:
    """Filter heights for fifty-year max wind analysis.

    Keeps heights between 120m and 160m (inclusive) where the corresponding
    avg WindSpeed sensor is not marked as interpolated (内插).

    Args:
        input_data: Analysis input with sensors and parameters.

    Returns:
        List of filtered heights.
    """
    filtered: list[float] = []
    for h in input_data.parameters.heights:
        if not (120.0 <= h <= 160.0):
            continue
        sensor = next(
            (
                s
                for s in input_data.time_series.sensors
                if s.sensor_type == "WindSpeed"
                and s.stat_type == "avg"
                and s.height == h
            ),
            None,
        )
        if sensor is not None and sensor.detect_interpolation_marker() != "内插":
            filtered.append(h)
    return filtered


@dataclass(frozen=True)
class ExtremeWindService:
    """Service for extreme wind (fifty-year max wind) analysis."""

    iec_standards: FiftyYearMaxWindIECStandardsSubsection
    method1: Method1Subsection
    method2: Method2Subsection
    method3: Method3Subsection
    summary: SummarySubsection
    title: str = "五十年一遇最大风速"

    @classmethod
    def generate(
        cls,
        items: list[tuple[SingleMastAnalysisInput, SingleMastMeta]],
    ) -> "ExtremeWindService":
        """Generate extreme wind (fifty-year max wind) section from items.

        Orchestrates all 4 methods (Method 1/2/3 + Summary) using
        per-method calculators and builders, then assembles results
        into subsections.

        Args:
            items: List of (input_data, meta) tuples for multi-mast aggregation.

        Returns:
            ExtremeWindService with populated subsections.
        """
        method1_dict: dict[str, list[ReportAtom]] = {}
        method2_dict: dict[str, list[ReportAtom]] = {}
        method3_dict: dict[str, list[ReportAtom]] = {}
        summary_dict: dict[str, list[ReportAtom]] = {}

        m1_calc = Method1Calculator()
        m2_calc = Method2Calculator()
        m3_calc = Method3Calculator()
        m1_builder = Method1Builder()
        m2_builder = Method2Builder()
        m3_builder = Method3Builder()
        summary_builder = SummaryBuilder()

        for input_data, meta in items:
            filtered_heights = _filter_fifty_year_heights(input_data)
            if not filtered_heights:
                continue

            modified_input = replace(
                input_data,
                parameters=replace(
                    input_data.parameters, heights=filtered_heights
                ),
            )

            # Method 1
            method1_result = m1_calc.calculate(modified_input)
            method1_atoms = m1_builder.build(
                mast_name=meta.mast_name,
                result=method1_result,
            )

            # Method 2
            method2_sustained, method2_sustained_params = (
                m2_calc.calculate_sustained(modified_input)
            )
            method2_extreme, method2_extreme_params = (
                m2_calc.calculate_extreme(
                    modified_input, method2_sustained
                )
            )
            method2_atoms = m2_builder.build(
                mast_name=meta.mast_name,
                sustained_wind=method2_sustained,
                sustained_params=method2_sustained_params,
                extreme_wind=method2_extreme,
                extreme_params=method2_extreme_params,
                qq_output_dir=Path("."),
            )

            # Method 3
            method3_sustained = m3_calc.calculate_sustained(modified_input)
            method3_extreme = m3_calc.calculate_extreme(
                modified_input, method3_sustained
            )
            method3_atoms = m3_builder.build(
                mast_name=meta.mast_name,
                sustained_result=method3_sustained,
                extreme_result=method3_extreme,
            )

            # Summary
            summary_atoms = summary_builder.build(
                mast_name=meta.mast_name,
                method1_result=method1_result,
                method2_sustained=method2_sustained,
                method2_extreme=method2_extreme,
                method3_sustained=method3_sustained,
                method3_extreme=method3_extreme,
            )

            method1_dict[meta.mast_name] = method1_atoms
            method2_dict[meta.mast_name] = method2_atoms
            method3_dict[meta.mast_name] = method3_atoms
            summary_dict[meta.mast_name] = summary_atoms

        # IEC standards reference table (not mast-specific)
        iec_atom = NoMastIECStandardsAtom.create(
            schema=IECStandardsSchema,
            df=IEC_STANDARDS_DATA,
            meta=NoMastMeta(),
        )

        return cls(
            iec_standards=FiftyYearMaxWindIECStandardsSubsection(
                atoms=AtomCollection.from_dict(
                    {"_no_mast": [iec_atom]}
                )
            ),
            method1=Method1Subsection(
                atoms=AtomCollection.from_dict(method1_dict)
            ),
            method2=Method2Subsection(
                atoms=AtomCollection.from_dict(method2_dict)
            ),
            method3=Method3Subsection(
                atoms=AtomCollection.from_dict(method3_dict)
            ),
            summary=SummarySubsection(
                atoms=AtomCollection.from_dict(summary_dict)
            ),
        )

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section as IR nodes for type-safe document assembly.

        Args:
            images_dir: Directory where images should be saved

        Returns:
            TypstSection with heading, body, and nested subsections
        """
        return TypstSection(
            heading=TypstHeading(text=self.title),
            body=[],
            subsections=[
                self.iec_standards.render_ir(images_dir),
                self.method1.render_ir(images_dir),
                self.method2.render_ir(images_dir),
                self.method3.render_ir(images_dir),
                self.summary.render_ir(images_dir),
            ],
        )


# Backward compatibility alias
FiftyYearMaxWindSection = ExtremeWindService
