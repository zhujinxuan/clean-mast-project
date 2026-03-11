"""Julia integration infrastructure.

ADR-GUARDRAILS: structure-001-subdomain-layout
Compliance: Infrastructure Pattern ✓ | ACL Package ✓
"""

from cleanmast.infrastructure.julia.julia_acl import JuliaAntiCorruptionLayer

__all__ = ["JuliaAntiCorruptionLayer"]
