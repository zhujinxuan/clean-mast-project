"""Infrastructure layer - external system adapters.

ADR-GUARDRAILS: structure-001-subdomain-layout
Compliance: Infrastructure Pattern ✓ | Anti-Corruption Layer ✓
"""

from cleanmast.infrastructure.julia.julia_acl import JuliaAntiCorruptionLayer

__all__ = ["JuliaAntiCorruptionLayer"]
