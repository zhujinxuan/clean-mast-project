# Per-Project Overrides

Some steps in the processing pipeline are driven by auto-generated
configuration files that may not fit every project. When you need to
override a step's configuration beyond the available CLI options:

1. Place your override scripts in this directory
2. Update the corresponding `recommend-*` recipe in `Justfile`
   to call the override after the recommend command

Common use case: overriding representative-year time ranges when
masts have different recording periods.
