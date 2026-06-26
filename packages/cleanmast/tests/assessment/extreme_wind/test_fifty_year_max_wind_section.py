"""Tests for FiftyYearMaxWindSection."""

from pathlib import Path

from cleanmast.subdomains.assessment.shared.collections.atom_collection import (
    AtomCollection,
)
from cleanmast.subdomains.assessment.shared.ir_types import TypstSection
from cleanmast.subdomains.assessment.subdomains.extreme_wind.entities.iec_standards_atom import (
    IEC_STANDARDS_DATA,
    NoMastIECStandardsAtom,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.services.fifty_year_max_wind_section import (
    FiftyYearMaxWindSection,
)
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
from cleanmast.subdomains.assessment.subdomains.extreme_wind.value_objects.report_meta import (
    NoMastMeta,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.value_objects.schemas import (
    IECStandardsSchema,
)


class TestFiftyYearMaxWindSection:
    """Tests for the parent fifty-year max wind section."""

    def test_render_ir_returns_typst_section_with_five_subsections(self) -> None:
        empty_collection = AtomCollection.from_dict({})
        method1 = Method1Subsection(atoms=empty_collection)
        method2 = Method2Subsection(atoms=empty_collection)
        method3 = Method3Subsection(atoms=empty_collection)
        summary = SummarySubsection(atoms=empty_collection)

        iec_standards_atom = NoMastIECStandardsAtom.create(
            schema=IECStandardsSchema,
            df=IEC_STANDARDS_DATA,
            meta=NoMastMeta(),
        )
        iec_standards = FiftyYearMaxWindIECStandardsSubsection(
            atoms=AtomCollection.from_dict({"_no_mast": [iec_standards_atom]})
        )

        section = FiftyYearMaxWindSection(
            iec_standards=iec_standards,
            method1=method1,
            method2=method2,
            method3=method3,
            summary=summary,
        )

        ir = section.render_ir(images_dir=Path("/tmp/images"))

        assert isinstance(ir, TypstSection)
        assert ir.heading.text == "五十年一遇最大风速"
        assert ir.body == []
        assert len(ir.subsections) == 5
