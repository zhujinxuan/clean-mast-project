"""Hash utilities for content-addressable DAG node identity.

Provides deterministic hashing for DataFrames, parameters, and node IDs
to support content-addressable caching in the Analysis DAG pipeline.
"""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import asdict, is_dataclass
from typing import Any

import polars as pl


def hash_dataframe(df: pl.DataFrame) -> str:
    """Hash a DataFrame using Parquet serialization.

    Uses Parquet serialization to get deterministic bytes, then computes
    SHA256 hash. Returns first 12 characters of hex digest for brevity
    while maintaining sufficient uniqueness.

    Args:
        df: The DataFrame to hash

    Returns:
        12-character hex string representing the content hash

    Example:
        >>> df = pl.DataFrame({"a": [1, 2, 3]})
        >>> hash_dataframe(df)
        'a1b2c3d4e5f6'
    """
    buf = io.BytesIO()
    df.write_parquet(buf)
    return hashlib.sha256(buf.getvalue()).hexdigest()[:12]


def hash_parameters(params: Any) -> str:
    """Hash arbitrary parameters using JSON serialization.

    Supports dataclasses, dicts, lists, and primitive types.
    Converts to JSON for deterministic byte representation.

    Args:
        params: Parameters to hash (dataclass, dict, list, or primitive)

    Returns:
        12-character hex string representing the parameter hash

    Example:
        >>> hash_parameters({"threshold": 0.5, "method": "linear"})
        'a1b2c3d4e5f6'
    """
    if is_dataclass(params) and not isinstance(params, type):
        data = asdict(params)
    else:
        data = params

    # Use sort_keys for deterministic JSON output
    json_bytes = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()[:12]


def compute_node_id(input_hash: str, params_hash: str) -> str:
    """Compute composite hash for DAG node identity.

    Combines input data hash and parameters hash to create a unique
    identifier for a node in the DAG. This enables content-addressable
    caching - same inputs + same parameters = same node ID.

    Args:
        input_hash: Hash of input data (from hash_dataframe)
        params_hash: Hash of processing parameters (from hash_parameters)

    Returns:
        12-character hex string representing the node identity

    Example:
        >>> compute_node_id("a1b2c3d4e5f6", "f6e5d4c3b2a1")
        '7d8e9f0a1b2c'
    """
    combined = f"{input_hash}:{params_hash}".encode("utf-8")
    return hashlib.sha256(combined).hexdigest()[:12]
