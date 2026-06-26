## Purpose
Root kernel for truly cross-cutting foundations

## Rules
- Bar for entry: used by 2+ contexts
- Timeseries types, path utils, atmospheric constants only
- No domain logic
- No context-specific types

## Anti-patterns
- Putting assessment-specific types here
- Putting IO here

## When in doubt
if only one context uses it, it belongs in that context's model/
