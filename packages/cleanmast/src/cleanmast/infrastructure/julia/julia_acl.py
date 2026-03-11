"""Julia Anti-Corruption Layer.

ADR-GUARDRAILS: integration-001-julia, structure-001-subdomain-layout
Compliance: ACL Pattern ✓ | Translation layer for Julia interoperability

Future: Translate between Python and Julia data formats.
Currently: Raises NotImplementedError with helpful message directing to Julia CLI.
"""


class JuliaAntiCorruptionLayer:
    """
    Anti-Corruption Layer for Julia integration.

    This class provides a boundary between Python and Julia implementations,
    ensuring that data formats are properly translated between the two worlds.

    Note: Currently not implemented. Use Julia CLI directly for these features.
    """

    def translate_config_to_julia(self, config: object) -> dict:
        """
        Translate Python configuration to Julia-compatible format.

        Args:
            config: Python configuration object

        Returns:
            Dictionary in Julia-compatible format

        Raises:
            NotImplementedError: Julia integration not yet available
        """
        raise NotImplementedError(
            "Julia integration not yet implemented. "
            "Use Julia CLI directly for configuration."
        )

    def translate_model_from_julia(self, model_path: str) -> object:
        """
        Translate Julia model output to Python-compatible format.

        Args:
            model_path: Path to Julia model output

        Returns:
            Python-compatible model object

        Raises:
            NotImplementedError: Julia integration not yet available
        """
        raise NotImplementedError(
            "Julia integration not yet implemented. "
            "Use Julia CLI directly for model operations."
        )
