"""Wind temporal section builder.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓ | Builder Pattern ✓
"""

from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
from cleanmast.subdomains.assessment.domain.entities.single_mast.daily_pattern import (
    SingleMastDailyPatternAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.daily_power_pattern import (
    SingleMastDailyPowerPatternAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.monthly_daily_power import (
    SingleMastMonthlyDailyPowerAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.monthly_daily_wind import (
    SingleMastMonthlyDailyWindAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.monthly_pattern import (
    SingleMastMonthlyPatternAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.monthly_power_pattern import (
    SingleMastMonthlyPowerPatternAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.timeseries import (
    SingleMastWindTimeseriesAtom,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    TemporalPatternSchema,
)


class WindTemporalSectionBuilder:
    """Builds wind temporal section from analysis results into report atoms.

    Bridges the analysis layer (WindTemporalAnalyzer) with the reporting layer,
    converting analysis results into the 7 temporal pattern atoms.
    """

    def build(
        self,
        mast_name: str,
        time_series_result: AnalysisResult[TemporalPatternSchema],
        daily_result: AnalysisResult[TemporalPatternSchema],
        monthly_result: AnalysisResult[TemporalPatternSchema],
        monthly_daily_result: AnalysisResult[TemporalPatternSchema],
    ) -> list[ReportAtom]:
        """Build temporal section from analysis results to report atoms.

        Args:
            mast_name: Name of the mast being analyzed
            time_series_result: Raw time series data
            daily_result: 24-hour pattern data
            monthly_result: 12-month pattern data
            monthly_daily_result: Monthly-daily combined pattern data

        Returns:
            List of 7 report atoms in order:
            1. SingleMastWindTimeseriesAtom
            2. SingleMastDailyPatternAtom
            3. SingleMastDailyPowerPatternAtom
            4. SingleMastMonthlyPatternAtom
            5. SingleMastMonthlyPowerPatternAtom
            6. SingleMastMonthlyDailyWindAtom
            7. SingleMastMonthlyDailyPowerAtom
        """
        meta = SingleMastMeta(mast_name=mast_name)

        atoms: list[ReportAtom] = [
            SingleMastWindTimeseriesAtom.create(
                schema=TemporalPatternSchema,
                df=time_series_result.data,
                meta=meta,
            ),
            SingleMastDailyPatternAtom.create(
                schema=TemporalPatternSchema,
                df=daily_result.data,
                meta=meta,
            ),
            SingleMastDailyPowerPatternAtom.create(
                schema=TemporalPatternSchema,
                df=daily_result.data,
                meta=meta,
            ),
            SingleMastMonthlyPatternAtom.create(
                schema=TemporalPatternSchema,
                df=monthly_result.data,
                meta=meta,
            ),
            SingleMastMonthlyPowerPatternAtom.create(
                schema=TemporalPatternSchema,
                df=monthly_result.data,
                meta=meta,
            ),
            SingleMastMonthlyDailyWindAtom.create(
                schema=TemporalPatternSchema,
                df=monthly_daily_result.data,
                meta=meta,
            ),
            SingleMastMonthlyDailyPowerAtom.create(
                schema=TemporalPatternSchema,
                df=monthly_daily_result.data,
                meta=meta,
            ),
        ]

        return atoms
