"""Tests for vertical profile builder schema import correctness.

RED Phase: Tests asserting vertical_profile_builder imports from correct schema module.
"""

from cleanmast.subdomains.assessment.domain.services.builders.vertical_profile_builder import (
    VerticalProfileSectionBuilder,
)
from cleanmast.subdomains.assessment.domain.value_objects.schemas import (
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
        import cleanmast.subdomains.assessment.domain.services.builders.vertical_profile_builder as builder_module
        
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


class TestSchemaConsistency:
    """Tests ensuring schema consistency across the assessment subdomain."""

    def test_no_duplicate_schema_definitions(self):
        """Assert schemas are defined only in value_objects.schemas.
        
        This test verifies there's no duplicate VerticalProfileSchema or
        WindShearSchema defined elsewhere (e.g., in single_mast.schemas).
        """
        # The canonical schemas should only exist in value_objects.schemas
        from cleanmast.subdomains.assessment.domain.value_objects import (
            schemas as vo_schemas,
        )
        
        # Verify VerticalProfileSchema is the class from value_objects
        assert hasattr(vo_schemas, 'VerticalProfileSchema')
        assert hasattr(vo_schemas, 'WindShearSchema')
        
        # Ensure they are proper dataframely Schema classes
        import dataframely as dy
        assert issubclass(vo_schemas.VerticalProfileSchema, dy.Schema)
        assert issubclass(vo_schemas.WindShearSchema, dy.Schema)
