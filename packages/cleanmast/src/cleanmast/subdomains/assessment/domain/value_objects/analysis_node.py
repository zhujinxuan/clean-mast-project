from dataclasses import dataclass
from typing import Any

from .hash_utils import compute_node_id, hash_dataframe


@dataclass
class AnalysisNode:
    """Entity representing a node in the analysis DAG.
    
    Content-addressable: same inputs + same params = same node_id
    """
    input_hash: str              # Hash of input data
    params_hash: str             # Hash of parameters
    upstream_hashes: list[str]   # Parent node hashes (for DAG edges)
    _output_hash: str | None = None  # Lazy cache for output hash
    
    @property
    def node_id(self) -> str:
        """Composite hash for DAG node identity."""
        return compute_node_id(self.input_hash, self.params_hash)
    
    def compute_output_hash(self, output_df: Any) -> str:
        """Compute and cache output hash."""
        if self._output_hash is None:
            self._output_hash = hash_dataframe(output_df)
        return self._output_hash
