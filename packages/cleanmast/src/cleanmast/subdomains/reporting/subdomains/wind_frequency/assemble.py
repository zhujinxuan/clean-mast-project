"""Assembly functions for wind frequency atoms.

Pure functions only — NO IO, no side effects.
Takes computed DataFrames and wraps them in the 4 wind frequency report atoms.
"""

import polars as pl

from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.wind_frequency.model.report_meta import (
    WindFrequencyAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.wind_frequency.model.schemas import (
    WindFrequencySchema,
)
from cleanmast.subdomains.reporting.subdomains.wind_frequency.model.wind_distribution_subgrid_atom import (
    SingleMastWindDistributionSubgridAtom,
)
from cleanmast.subdomains.reporting.subdomains.wind_frequency.model.wind_frequency_hours_atom import (
    SingleMastWindFrequencyHoursAtom,
)
from cleanmast.subdomains.reporting.subdomains.wind_frequency.model.wind_power_hours_atom import (
    SingleMastWindPowerHoursAtom,
)
from cleanmast.subdomains.reporting.subdomains.wind_frequency.model.wind_productive_range_atom import (
    SingleMastWindProductiveRangeAtom,
)


def build_wind_frequency_atoms(
    mast_data: list[tuple[str, pl.DataFrame]],
) -> list[ReportAtom]:
    """Build wind frequency report atoms from computed per-mast DataFrames.

    Args:
        mast_data: List of (mast_name, wind_frequency_df) tuples.

    Returns:
        List of report atoms in order: frequency hours, power hours,
        productive range, distribution chart. One group per mast.
    """
    atoms: list[ReportAtom] = []
    for mast_name, df in mast_data:
        meta = WindFrequencyAtomMeta(mast_name=mast_name)
        atoms.append(
            SingleMastWindFrequencyHoursAtom.create(WindFrequencySchema, df, meta)
        )
        atoms.append(
            SingleMastWindPowerHoursAtom.create(WindFrequencySchema, df, meta)
        )
        atoms.append(
            SingleMastWindProductiveRangeAtom.create(WindFrequencySchema, df, meta)
        )
        atoms.append(
            SingleMastWindDistributionSubgridAtom.create(WindFrequencySchema, df, meta)
        )
    return atoms
