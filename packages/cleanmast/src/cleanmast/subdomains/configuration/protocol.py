"""Protocol types for recommend command signatures.

Stub — actual type aliases added as recommend commands are migrated to
consume ``ProjectConfig``.

Pattern: each recommend function is ``Callable[[ProjectConfig, ...], DiscoveredConfig[T]]``.
"""
