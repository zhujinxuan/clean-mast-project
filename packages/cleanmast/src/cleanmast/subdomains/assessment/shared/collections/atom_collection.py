"""AtomCollection for report atoms.
 
ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-002-entities-value-objects
Compliance: Subdomain layout ✓ | Value Object ✓ | Collection Pattern ✓
"""
 
from __future__ import annotations
 
from dataclasses import dataclass, field
from typing import TypeVar, cast
 
from cleanmast.subdomains.assessment.shared.protocols.report_atom import ReportAtom
 
T = TypeVar("T", bound=ReportAtom)
 
 
@dataclass(frozen=True)
class AtomCollection:
    """Immutable collection of ReportAtoms with efficient indexing.
 
    Atoms are organized by mast name and can be retrieved by type.
    The collection maintains insertion order for masts.
 
    Attributes:
        _by_mast: Dict mapping mast names to their atoms in order
        _by_key: Dict mapping (mast, atom_type) tuples to atoms
    """
 
    _by_mast: dict[str, list[ReportAtom]] = field(default_factory=dict)
    _by_key: dict[tuple[str, type[ReportAtom]], list[ReportAtom]] = field(
        default_factory=dict
    )
 
    @classmethod
    def from_dict(cls, data: dict[str, list[ReportAtom]]) -> AtomCollection:
        """Create collection from mast->atoms mapping.
 
        Args:
            data: Dict mapping mast names to lists of ReportAtoms
 
        Returns:
            New frozen AtomCollection instance
        """
        by_mast = dict(data)
        by_key: dict[tuple[str, type[ReportAtom]], list[ReportAtom]] = {}
 
        for mast, atoms in by_mast.items():
            for atom in atoms:
                atom_type = type(atom)
                by_key.setdefault((mast, atom_type), []).append(atom)
 
        return cls(_by_mast=by_mast, _by_key=by_key)
 
    @property
    def masts(self) -> list[str]:
        """Return list of mast names in insertion order."""
        return list(self._by_mast.keys())
 
    def get(self, mast: str, atom_type: type[T]) -> T | None:
        """Get atom by mast and type.
 
        Args:
            mast: Mast name to look up
            atom_type: Concrete atom class to retrieve
 
        Returns:
            The first atom if found and matches type, None otherwise
        """
        atoms = self._by_key.get((mast, atom_type))
        if not atoms:
            return None
        atom = atoms[0]
        if not isinstance(atom, atom_type):
            return None
        return cast(T, atom)
 
    def get_all_by_type(self, atom_type: type[T]) -> list[T]:
        """Get all atoms of specific type, in mast order.
 
        Args:
            atom_type: Concrete atom class to filter by
 
        Returns:
            List of atoms of the specified type, ordered by mast
        """
        result: list[T] = []
        for mast in self.masts:
            atoms = self._by_key.get((mast, atom_type), [])
            for atom in atoms:
                if isinstance(atom, atom_type):
                    result.append(cast(T, atom))
        return result
 
    def get_by_mast(self, mast: str) -> list[ReportAtom]:
        """Get all atoms for a specific mast.
 
        Args:
            mast: Mast name to look up
 
        Returns:
            List of atoms for the mast, empty if mast not found
        """
        return list(self._by_mast.get(mast, []))
 
    def __len__(self) -> int:
        """Return total number of atoms in collection."""
        return sum(len(atoms) for atoms in self._by_mast.values())
 
    def __iter__(self):
        """Iterate over all atoms in mast order."""
        for mast in self.masts:
            yield from self._by_mast[mast]
 
    def __contains__(self, item: ReportAtom) -> bool:
        """Check if atom exists in collection.
 
        Args:
            item: ReportAtom to check for
 
        Returns:
            True if atom is in collection, False otherwise
        """
        mast = getattr(item.meta, "mast_name", None)
        if mast is None:
            return False
        key = (mast, type(item))
        return key in self._by_key and any(atom is item for atom in self._by_key[key])
