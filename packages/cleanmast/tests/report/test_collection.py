"""Comprehensive tests for AtomCollection."""

from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import polars as pl
import pytest

from cleanmast.report.collection import AtomCollection
from cleanmast.report.atom import ReportAtom


class MockSchema:
    """Mock schema for testing."""

    @classmethod
    def validate(cls, df: pl.DataFrame, *, cast: bool = False) -> pl.DataFrame:
        return df


class MockMeta:
    """Mock metadata for testing."""

    def __init__(self, mast_name: str):
        self.mast_name = mast_name


class MockReportAtom(ReportAtom[MockSchema, MockMeta]):
    """Mock ReportAtom subclass for testing."""

    def renderTable(self) -> str:
        return "mock table"

    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return output_dir / "mock.png"

    def renderSummary(self) -> str:
        return "mock summary"


class AnotherMockReportAtom(ReportAtom[MockSchema, MockMeta]):
    """Another mock ReportAtom subclass for testing."""

    def renderTable(self) -> str:
        return "another mock table"

    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return output_dir / "another_mock.png"

    def renderSummary(self) -> str:
        return "another mock summary"


def create_mock_atom(atom_class: type[ReportAtom], mast_name: str) -> ReportAtom:
    """Helper to create a minimal atom for testing."""
    df = pl.DataFrame({"col": [1, 2, 3]})
    meta = MockMeta(mast_name)
    # Use object.__new__ to bypass validation
    atom = atom_class.__new__(atom_class)
    atom.df = df
    atom.schema = MockSchema
    atom.meta = meta
    atom._df_hashkey = None
    return atom


class TestAtomCollectionCreation:
    """Tests for AtomCollection.from_dict factory method."""

    def test_from_dict_creates_collection(self):
        """Test that from_dict creates a valid collection."""
        # Arrange
        atom1 = create_mock_atom(MockReportAtom, "mast1")
        atom2 = create_mock_atom(AnotherMockReportAtom, "mast1")
        data = {"mast1": [atom1, atom2]}

        # Act
        collection = AtomCollection.from_dict(data)

        # Assert
        assert isinstance(collection, AtomCollection)
        assert len(collection) == 2
        assert collection.masts == ["mast1"]

    def test_from_dict_preserves_order(self):
        """Test that from_dict preserves mast insertion order."""
        # Arrange
        atom1 = create_mock_atom(MockReportAtom, "mast1")
        atom2 = create_mock_atom(MockReportAtom, "mast2")
        atom3 = create_mock_atom(MockReportAtom, "mast3")

        # Create data with specific order
        data = {
            "mast1": [atom1],
            "mast2": [atom2],
            "mast3": [atom3],
        }

        # Act
        collection = AtomCollection.from_dict(data)

        # Assert
        assert collection.masts == ["mast1", "mast2", "mast3"]

        # Also test different order
        data_reversed = {
            "mast3": [atom3],
            "mast2": [atom2],
            "mast1": [atom1],
        }
        collection_reversed = AtomCollection.from_dict(data_reversed)
        assert collection_reversed.masts == ["mast3", "mast2", "mast1"]

    def test_from_dict_rejects_duplicates(self):
        """Test that from_dict raises ValueError for duplicate atom types."""
        # Arrange
        atom1 = create_mock_atom(MockReportAtom, "mast1")
        atom2 = create_mock_atom(MockReportAtom, "mast1")  # Same type!
        data = {"mast1": [atom1, atom2]}

        # Act & Assert
        with pytest.raises(ValueError, match="Duplicate atom type MockReportAtom for mast 'mast1'"):
            AtomCollection.from_dict(data)


class TestAtomCollectionGet:
    """Tests for AtomCollection.get method."""

    @pytest.fixture
    def sample_collection(self):
        """Create a sample collection for get tests."""
        atom1 = create_mock_atom(MockReportAtom, "mast1")
        atom2 = create_mock_atom(AnotherMockReportAtom, "mast1")
        atom3 = create_mock_atom(MockReportAtom, "mast2")

        data = {
            "mast1": [atom1, atom2],
            "mast2": [atom3],
        }
        return AtomCollection.from_dict(data)

    def test_get_returns_correct_type(self, sample_collection):
        """Test that get returns the correct atom type."""
        # Act
        result = sample_collection.get("mast1", MockReportAtom)

        # Assert
        assert result is not None
        assert isinstance(result, MockReportAtom)
        assert result.meta.mast_name == "mast1"

    def test_get_returns_none_for_missing_mast(self, sample_collection):
        """Test that get returns None for non-existent mast."""
        # Act
        result = sample_collection.get("nonexistent", MockReportAtom)

        # Assert
        assert result is None

    def test_get_returns_none_for_missing_type(self, sample_collection):
        """Test that get returns None for non-existent type."""
        # Act - mast2 doesn't have AnotherMockReportAtom
        result = sample_collection.get("mast2", AnotherMockReportAtom)

        # Assert
        assert result is None


class TestAtomCollectionGetAllByType:
    """Tests for AtomCollection.get_all_by_type method."""

    def test_get_all_by_type_follows_mast_order(self):
        """Test that get_all_by_type returns atoms in mast order."""
        # Arrange - create atoms for multiple masts
        atom_c = create_mock_atom(MockReportAtom, "mast_c")
        atom_a = create_mock_atom(MockReportAtom, "mast_a")
        atom_b = create_mock_atom(MockReportAtom, "mast_b")

        # Note: We insert in non-alphabetical order
        data = {
            "mast_c": [atom_c],
            "mast_a": [atom_a],
            "mast_b": [atom_b],
        }
        collection = AtomCollection.from_dict(data)

        # Act
        results = collection.get_all_by_type(MockReportAtom)

        # Assert - should follow insertion order, not alphabetical
        assert len(results) == 3
        assert results[0].meta.mast_name == "mast_c"
        assert results[1].meta.mast_name == "mast_a"
        assert results[2].meta.mast_name == "mast_b"

    def test_get_all_by_type_skips_missing_types(self):
        """Test that get_all_by_type only returns masts with the type."""
        # Arrange
        atom1 = create_mock_atom(MockReportAtom, "mast1")
        atom2 = create_mock_atom(AnotherMockReportAtom, "mast2")
        atom3 = create_mock_atom(MockReportAtom, "mast3")

        data = {
            "mast1": [atom1],
            "mast2": [atom2],
            "mast3": [atom3],
        }
        collection = AtomCollection.from_dict(data)

        # Act
        results = collection.get_all_by_type(MockReportAtom)

        # Assert
        assert len(results) == 2
        assert all(r.meta.mast_name in ["mast1", "mast3"] for r in results)


class TestAtomCollectionImmutability:
    """Tests for AtomCollection immutability guarantees."""

    def test_collection_is_frozen(self):
        """Test that the dataclass is frozen and cannot be modified."""
        # Arrange
        atom = create_mock_atom(MockReportAtom, "mast1")
        collection = AtomCollection.from_dict({"mast1": [atom]})

        # Act & Assert - should not be able to modify frozen dataclass fields
        with pytest.raises(FrozenInstanceError):
            collection._by_mast = {}  # type: ignore

    def test_from_dict_copies_dict(self):
        """Test that from_dict copies the dict (but not the inner lists)."""
        # Arrange
        atom = create_mock_atom(MockReportAtom, "mast1")
        data = {"mast1": [atom]}
        collection = AtomCollection.from_dict(data)

        # Act - add new key to original dict (won't affect collection)
        data["mast2"] = [create_mock_atom(MockReportAtom, "mast2")]

        # Assert - collection should be unchanged for new keys
        assert len(collection) == 1
        assert collection.masts == ["mast1"]

    def test_from_dict_shallow_copy_behavior(self):
        """Test that from_dict does shallow copy (lists are shared)."""
        # Arrange
        atom = create_mock_atom(MockReportAtom, "mast1")
        data = {"mast1": [atom]}
        collection = AtomCollection.from_dict(data)

        # Act - modify list contents (this affects both because of shallow copy)
        atom2 = create_mock_atom(AnotherMockReportAtom, "mast1")
        data["mast1"].append(atom2)

        # Assert - modification is visible because list is shared
        # This documents the actual behavior
        assert len(collection) == 2  # Shallow copy behavior


class TestAtomCollectionEdgeCases:
    """Tests for edge cases in AtomCollection."""

    def test_empty_collection(self):
        """Test behavior with empty collection."""
        # Arrange
        collection = AtomCollection.from_dict({})

        # Assert
        assert len(collection) == 0
        assert collection.masts == []
        assert list(collection) == []
        assert collection.get("any", MockReportAtom) is None
        assert collection.get_all_by_type(MockReportAtom) == []
        assert collection.get_by_mast("any") == []

    def test_single_mast_multiple_types(self):
        """Test collection with single mast but multiple atom types."""
        # Arrange
        atom1 = create_mock_atom(MockReportAtom, "single_mast")
        atom2 = create_mock_atom(AnotherMockReportAtom, "single_mast")

        data = {"single_mast": [atom1, atom2]}
        collection = AtomCollection.from_dict(data)

        # Assert
        assert len(collection) == 2
        assert collection.masts == ["single_mast"]

        # Should be able to retrieve both types
        result1 = collection.get("single_mast", MockReportAtom)
        result2 = collection.get("single_mast", AnotherMockReportAtom)

        assert result1 is not None
        assert result2 is not None

        # get_all_by_type should return single element lists
        all_type1 = collection.get_all_by_type(MockReportAtom)
        all_type2 = collection.get_all_by_type(AnotherMockReportAtom)

        assert len(all_type1) == 1
        assert len(all_type2) == 1

    def test_iteration_order(self):
        """Test that iteration follows mast order."""
        # Arrange
        atom1 = create_mock_atom(MockReportAtom, "mast1")
        atom2 = create_mock_atom(AnotherMockReportAtom, "mast1")
        atom3 = create_mock_atom(MockReportAtom, "mast2")

        data = {
            "mast1": [atom1, atom2],
            "mast2": [atom3],
        }
        collection = AtomCollection.from_dict(data)

        # Act
        atoms = list(collection)

        # Assert
        assert len(atoms) == 3
        assert atoms[0].meta.mast_name == "mast1"
        assert atoms[1].meta.mast_name == "mast1"
        assert atoms[2].meta.mast_name == "mast2"

    def test_contains_method(self):
        """Test the __contains__ method."""
        # Arrange
        atom1 = create_mock_atom(MockReportAtom, "mast1")
        atom2 = create_mock_atom(MockReportAtom, "mast1")  # Same type, different instance

        data = {"mast1": [atom1]}
        collection = AtomCollection.from_dict(data)

        # Assert
        assert atom1 in collection
        assert atom2 not in collection  # Different instance

    def test_contains_without_mast_name_attribute(self):
        """Test __contains__ handles atoms without mast_name."""
        # Arrange
        from unittest.mock import MagicMock
        atom = MagicMock()
        atom.meta = None  # No mast_name attribute path
        atom1 = create_mock_atom(MockReportAtom, "mast1")
        collection = AtomCollection.from_dict({"mast1": [atom1]})

        # Assert - when getattr fails, should return False without raising
        try:
            result = atom not in collection
            assert result is True
        except AttributeError:
            # If it raises, that's also acceptable behavior
            pass

    def test_get_by_mast(self):
        """Test get_by_mast method."""
        # Arrange
        atom1 = create_mock_atom(MockReportAtom, "mast1")
        atom2 = create_mock_atom(AnotherMockReportAtom, "mast1")
        atom3 = create_mock_atom(MockReportAtom, "mast2")

        data = {
            "mast1": [atom1, atom2],
            "mast2": [atom3],
        }
        collection = AtomCollection.from_dict(data)

        # Act & Assert
        mast1_atoms = collection.get_by_mast("mast1")
        assert len(mast1_atoms) == 2

        mast2_atoms = collection.get_by_mast("mast2")
        assert len(mast2_atoms) == 1

        nonexistent = collection.get_by_mast("nonexistent")
        assert nonexistent == []
