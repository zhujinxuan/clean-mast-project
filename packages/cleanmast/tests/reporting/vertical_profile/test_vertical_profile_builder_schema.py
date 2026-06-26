"""Tests for vertical profile builder schema imports — reporting domain.

Ported from tests/assessment/vertical_profile/test_vertical_profile_builder_schema.py.
Test logic preserved; only import paths updated.
"""

from datetime import datetime

import polars as pl
from cleanmast.subdomains.reporting.model.analysis_metadata import AnalysisMetadata
from cleanmast.subdomains.reporting.model.analysis_result import AnalysisResult
from cleanmast.subdomains.reporting.subdomains.vertical_profile.assemble import (
    VerticalProfileSectionBuilder,
)
from cleanmast.subdomains.reporting.subdomains.vertical_profile.model.schemas import (
    VerticalProfileSchema,
    WindShearSchema,
)
from cleanmast.subdomains.reporting.subdomains.vertical_profile.model.wind_shear_exponent_atom import (
    SingleMastWindShearExponentAtom,
)


class TestVerticalProfileBuilderSchemaImport:
    def test_vertical_profile_schema_imports_from_value_objects(self):
        import cleanmast.subdomains.reporting.subdomains.vertical_profile.assemble as builder_module
        assert hasattr(builder_module, 'VerticalProfileSchema')
        assert hasattr(builder_module, 'WindShearSchema')
        assert builder_module.VerticalProfileSchema is VerticalProfileSchema
        assert builder_module.WindShearSchema is WindShearSchema

    def test_vertical_profile_schema_columns_match_analyzer_output(self):
        schema_columns = {
            "height",
            "interpolation_marker",
            "wind_speed_mean",
            "wind_speed_std",
            "alpha",
            "r_squared",
        }
        expected_columns = set(VerticalProfileSchema.columns().keys())
        assert schema_columns == expected_columns

    def test_wind_shear_schema_columns_match_analyzer_output(self):
        schema_columns = {
            "from_height",
            "to_height",
            "alpha_mean",
            "alpha_std",
            "alpha_min",
            "alpha_max",
        }
        expected_columns = set(WindShearSchema.columns().keys())
        assert schema_columns == expected_columns


class TestVerticalProfileBuilderBuildMethod:
    def test_builder_accepts_correct_schema_types(self):
        builder = VerticalProfileSectionBuilder()
        import inspect
        sig = inspect.signature(builder.build)
        params = list(sig.parameters.keys())
        assert "mast_name" in params
        assert "profile_results" in params
        assert "shear_results" in params
        profile_param = sig.parameters["profile_results"]
        shear_param = sig.parameters["shear_results"]
        assert profile_param.annotation is not inspect.Parameter.empty
        assert shear_param.annotation is not inspect.Parameter.empty


class TestVerticalProfileBuilderAtoms:
    def test_builder_returns_exactly_one_atom(self) -> None:
        builder = VerticalProfileSectionBuilder()
        meta = AnalysisMetadata(
            mast_name="TestMast",
            time_range="2023-01-01 to 2023-12-31",
            created_at=datetime(2024, 1, 1),
        )
        profile_results = [
            AnalysisResult(
                data=pl.DataFrame({
                    "height": [50.0, 80.0, 100.0, 120.0],
                    "interpolation_marker": [None, None, None, "外推"],
                    "wind_speed_mean": [5.2, 6.1, 6.8, 7.2],
                    "wind_speed_std": [1.8, 2.0, 2.1, 2.2],
                    "alpha": [0.15, None, None, None],
                    "r_squared": [0.98, None, None, None],
                }),
                schema=VerticalProfileSchema,
                metadata=meta,
            )
        ]
        shear_results = [
            AnalysisResult(
                data=pl.DataFrame({
                    "from_height": [50.0, 80.0, 100.0],
                    "to_height": [80.0, 100.0, 120.0],
                    "alpha_mean": [0.15, 0.14, 0.13],
                    "alpha_std": [0.03, 0.025, 0.02],
                    "alpha_min": [0.08, 0.07, 0.06],
                    "alpha_max": [0.25, 0.22, 0.20],
                }),
                schema=WindShearSchema,
                metadata=meta,
            )
        ]
        atoms = builder.build("TestMast", profile_results, shear_results)
        assert len(atoms) == 1
        assert isinstance(atoms[0], SingleMastWindShearExponentAtom)


class TestSchemaConsistency:
    def test_no_duplicate_schema_definitions(self):
        from cleanmast.subdomains.reporting.subdomains.vertical_profile.model import (
            schemas as vo_schemas,
        )
        assert hasattr(vo_schemas, 'VerticalProfileSchema')
        assert hasattr(vo_schemas, 'WindShearSchema')
        import dataframely as dy
        assert issubclass(vo_schemas.VerticalProfileSchema, dy.Schema)
        assert issubclass(vo_schemas.WindShearSchema, dy.Schema)
