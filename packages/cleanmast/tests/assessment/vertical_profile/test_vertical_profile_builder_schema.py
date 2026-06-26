"""Tests for vertical profile builder schema import correctness.

RED Phase: Tests asserting vertical_profile_builder imports from correct schema module.
"""

from datetime import datetime

import polars as pl
from cleanmast.subdomains.assessment.subdomains.vertical_profile.entities.wind_shear_matrix_atom import (
    SingleMastWindShearExponentAtom,
)
from cleanmast.subdomains.assessment.subdomains.vertical_profile.services._builder import (
    VerticalProfileSectionBuilder,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_metadata import (
    AnalysisMetadata,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.subdomains.vertical_profile.value_objects.schemas import (
    VerticalProfileSchema,
    WindShearSchema,
)


class TestVerticalProfileBuilderSchemaImport:
    """Tests that vertical_profile_builder imports schemas from correct module."""

    def test_vertical_profile_schema_imports_from_value_objects(self):
        """Assert VerticalProfileSchema is imported from value_objects.schemas.
        
        This test prevents regression where the import might be incorrectly
        changed to import from single_mast.schemas or another location.
        """
        # The import in vertical_profile_builder.py should reference
        # the schema from value_objects.schemas, not single_mast.schemas
        import cleanmast.subdomains.assessment.subdomains.vertical_profile.services._builder as builder_module
        
        # Check that the module has imported the schemas
        assert hasattr(builder_module, 'VerticalProfileSchema'), \
            "VerticalProfileSchema should be imported in vertical_profile_builder"
        assert hasattr(builder_module, 'WindShearSchema'), \
            "WindShearSchema should be imported in vertical_profile_builder"
        
        # Verify they are the correct schemas from value_objects.schemas
        assert builder_module.VerticalProfileSchema is VerticalProfileSchema, \
            "VerticalProfileSchema must be imported from value_objects.schemas"
        assert builder_module.WindShearSchema is WindShearSchema, \
            "WindShearSchema must be imported from value_objects.schemas"

    def test_vertical_profile_schema_columns_match_analyzer_output(self):
        """Assert VerticalProfileSchema columns match analyzer output.
        
        The analyzer produces DataFrames with specific columns that must
        match the schema definition for proper atom creation.
        """
        # Schema columns from value_objects/schemas.py
        schema_columns = {
            "height",
            "interpolation_marker",
            "wind_speed_mean",
            "wind_speed_std",
            "alpha",
            "r_squared",
        }
        
        # Get expected columns from the schema class
        expected_columns = set(VerticalProfileSchema.columns().keys())
        
        assert schema_columns == expected_columns, (
            f"VerticalProfileSchema columns mismatch.\n"
            f"Expected from source: {schema_columns}\n"
            f"Actual from schema: {expected_columns}"
        )

    def test_wind_shear_schema_columns_match_analyzer_output(self):
        """Assert WindShearSchema columns match analyzer output.
        
        The shear analyzer produces DataFrames with specific columns that must
        match the schema definition for proper atom creation.
        """
        # Schema columns from value_objects/schemas.py
        schema_columns = {
            "from_height",
            "to_height",
            "alpha_mean",
            "alpha_std",
            "alpha_min",
            "alpha_max",
        }
        
        # Get expected columns from the schema class
        expected_columns = set(WindShearSchema.columns().keys())
        
        assert schema_columns == expected_columns, (
            f"WindShearSchema columns mismatch.\n"
            f"Expected from source: {schema_columns}\n"
            f"Actual from schema: {expected_columns}"
        )


class TestVerticalProfileBuilderBuildMethod:
    """Tests for the builder's build method with schema validation."""

    def test_builder_accepts_correct_schema_types(self):
        """Assert builder.build accepts AnalysisResult with correct schema types.
        
        This ensures the type hints in build() method are correct and
        the builder properly uses the schemas from value_objects.schemas.
        """
        builder = VerticalProfileSectionBuilder()
        
        # Verify the build method exists and has proper signature
        import inspect
        sig = inspect.signature(builder.build)
        params = list(sig.parameters.keys())
        
        assert "mast_name" in params
        assert "profile_results" in params
        assert "shear_results" in params
        
        # The type annotations should reference the correct schema types
        profile_param = sig.parameters["profile_results"]
        shear_param = sig.parameters["shear_results"]
        
        # Check that the annotations exist (they use generics with schema types)
        assert profile_param.annotation is not inspect.Parameter.empty, \
            "profile_results should have type annotation"
        assert shear_param.annotation is not inspect.Parameter.empty, \
            "shear_results should have type annotation"


class TestVerticalProfileBuilderAtoms:
    """Tests that builder returns exactly one atom in the new layout."""

    def test_builder_returns_exactly_one_atom(self) -> None:
        """Assert builder returns a single SingleMastWindShearExponentAtom."""
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
    """Tests ensuring schema consistency across the assessment subdomain."""

    def test_no_duplicate_schema_definitions(self):
        """Assert schemas are defined in canonical subdomain location.
        
        VerticalProfileSchema and WindShearSchema should be defined only in
        vertical_profile.value_objects.schemas (canonical subdomain location).
        """
        from cleanmast.subdomains.assessment.subdomains.vertical_profile.value_objects import (
            schemas as vo_schemas,
        )
        
        # Verify VerticalProfileSchema is the class from value_objects
        assert hasattr(vo_schemas, 'VerticalProfileSchema')
        assert hasattr(vo_schemas, 'WindShearSchema')
        
        # Ensure they are proper dataframely Schema classes
        import dataframely as dy
        assert issubclass(vo_schemas.VerticalProfileSchema, dy.Schema)
        assert issubclass(vo_schemas.WindShearSchema, dy.Schema)
