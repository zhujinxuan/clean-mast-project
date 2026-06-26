# ADR: Assessment Subdomain Layout

> Following `packages/cleanmast/adr/structure-001-subdomain-layout.md`
> References: `ddd-s-001-bounded-contexts.md`, `ddd-s-002-context-maps.md`, `ddd-s-003-subdomain-deepening.md`

## Role
Assessment follows the Nested Subdomain pattern from structure-001.

## Concrete Structure
Uses Nested Subdomain + layered hybrid pattern:

```
assessment/
├── domain/entities/, domain/protocols/, domain/services/, domain/value_objects/
├── application/services/
├── infrastructure/
├── shared/
├── adapters/
└── subdomains/
    └── {capability}/
        ├── adr-{adr-id}.md
        ├── entities/
        ├── services/
        └── value_objects/
```

## Principles

1. Nesting is proportional to complexity. Assessment warrants nesting because it has 10 independent capability groups. Simpler contexts (configuration, pipeline) do not.
2. Pattern coexistence is intentional. The layered + nested hybrid reflects assessment's dual role: orchestrator (nested) AND domain model holder (layered).
