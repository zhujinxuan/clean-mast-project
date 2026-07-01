"""Reporting domain — wind resource assessment report generation.

Public surface: api functions + model types only.
Infrastructure (render/), internal (compute/, assemble/, subdomains/) are private.
"""

from cleanmast.subdomains.reporting.api import ReportGenerationService
from cleanmast.subdomains.reporting.model.analysis_input import SingleMastAnalysisInput
from cleanmast.subdomains.reporting.model.analysis_metadata import AnalysisMetadata
from cleanmast.subdomains.reporting.model.analysis_parameters import AnalysisParameters
from cleanmast.subdomains.reporting.model.analysis_result import AnalysisResult

__all__ = [
    "ReportGenerationService",
    "AnalysisMetadata",
    "AnalysisParameters",
    "AnalysisResult",
    "SingleMastAnalysisInput",
]
