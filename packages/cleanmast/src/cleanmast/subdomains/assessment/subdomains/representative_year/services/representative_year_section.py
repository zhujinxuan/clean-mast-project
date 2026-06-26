"""Representative year calibration subsection implementation.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

from cleanmast.subdomains.assessment.subdomains.representative_year.entities.representative_year_atom import (
    MultiMastRepYearCalibrationAtom,
)
from cleanmast.subdomains.assessment.subdomains.representative_year.services._calculator import (
    analyze_representative_year_calibration,
)
from cleanmast.subdomains.assessment.subdomains.representative_year.value_objects.report_meta import (
    RepresentativeYearMeta,
)
from cleanmast.subdomains.assessment.subdomains.representative_year.value_objects.schemas import (
    MultiMastRepYearCalibrationSchema,
)
from cleanmast.subdomains.assessment.shared.utils.subsection_renderer import (
    render_subsection_content,
)
from cleanmast.subdomains.assessment.shared.ir_types import (
    TypstHeading,
    TypstSection,
)
from cleanmast.subdomains.assessment.shared.collections.atom_collection import (
    AtomCollection,
)


@dataclass(frozen=True)
class RepresentativeYearService:
    """Service for representative year calibration section."""

    atoms: AtomCollection
    title: str = "代表年订正"

    @classmethod
    def generate(
        cls,
        analysis_inputs,
        project_dir: Path,
    ) -> "RepresentativeYearService":
        """Generate representative year calibration section from project directory."""
        if project_dir is None:
            raise ValueError("project_dir is required for representative year calibration section")
        df = analyze_representative_year_calibration(project_dir)
        mast_names = df["mast_name"].to_list()
        atom = MultiMastRepYearCalibrationAtom.create(
            MultiMastRepYearCalibrationSchema,
            df,
            RepresentativeYearMeta(mast_names=mast_names),
        )
        collection = AtomCollection.from_dict({"_all_masts": [atom]})
        return cls(atoms=collection)

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section to IR nodes."""
        atom_configs = [
            (MultiMastRepYearCalibrationAtom, True),
        ]

        body = render_subsection_content(self.atoms, atom_configs, images_dir)
        return TypstSection(
            heading=TypstHeading(text=self.title),
            body=body,
            subsections=[],
        )


# Backward compatibility alias
RepresentativeYearCalibrationSubsection = RepresentativeYearService
