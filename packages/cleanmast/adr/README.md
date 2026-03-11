# CleanMast ADR Index

Architecture Decision Records for CleanMast Python package DDD refactoring.

> **⚠️ IMPORTANT**: Use **selective loading** (see below) to avoid context bloat.

## ADR Index

### Domain-Driven Design (DDD)

#### Strategic Patterns
| ADR ID | File | Title | Purpose | Load When |
|--------|------|-------|---------|-----------|
| ddd-s-001 | [ddd-s-001-bounded-contexts.md](ddd-s-001-bounded-contexts.md) | Bounded Contexts | Define 6 context boundaries | Refactoring, new contexts |
| ddd-s-002 | [ddd-s-002-context-maps.md](ddd-s-002-context-maps.md) | Context Maps | Customer-Supplier relationships | Cross-context integration |

### Structure & Layout
| ADR ID | File | Title | Purpose | Load When |
|--------|------|-------|---------|-----------|
| structure-001 | [structure-001-subdomain-layout.md](structure-001-subdomain-layout.md) | Subdomain Layout | CleanMast folder structure | Reorganizing code |

### Data & Persistence
| ADR ID | File | Title | Purpose | Load When |
|--------|------|-------|---------|-----------|
| persistence-001 | [persistence-001-parquet-storage.md](persistence-001-parquet-storage.md) | Parquet Storage | Sensor metadata + parquet files | Saving/loading data |

### Pipeline
| ADR ID | File | Title | Purpose | Load When |
|--------|------|-------|---------|-----------|
| pipeline-001 | [pipeline-001-orchestration.md](pipeline-001-orchestration.md) | Pipeline Orchestration | Phase workflows, Julia integration | Pipeline execution |

## Quick Start: Selective Loading

```
Step 1: Read this README
Step 2: Load only ADRs relevant to your CURRENT task
```

## Phase-Based Loading

Each ADR has **main file** (concise constraints) + **phase files** (detailed guidance):

| Phase | Purpose | File Pattern |
|-------|---------|--------------|
| **on-plan** | Design/Planning | `phases/{adr}/on-plan.md` |
| **review-plan** | Review Designs | `phases/{adr}/review-plan.md` |
| **code** | Implementation | `phases/{adr}/code.md` |
| **review-implementation** | Review Code | `phases/{adr}/review-implementation.md` |

### Loading Guide by Task

| Task Type | Load ADR | Then Load Phase File |
|-----------|----------|---------------------|
| Design bounded contexts | ddd-s-001 | `phases/ddd-s-001-bounded-contexts/on-plan.md` |
| Map context relationships | ddd-s-002 | `phases/ddd-s-002-context-maps/on-plan.md` |
| Restructure folders | structure-001 | `phases/structure-001-subdomain-layout/on-plan.md` |
| Implement parquet storage | persistence-001 | `phases/persistence-001-parquet-storage/code.md` |
| Build pipeline orchestration | pipeline-001 | `phases/pipeline-001-orchestration/code.md` |

## Bounded Contexts Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    PipelineContext                           │
│              (Orchestrates all contexts)                     │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
      ┌────────▼────────┐             ┌────────▼────────┐
      │  Configuration  │             │ DataIngestion   │
      │  (recommend)    │             │ (Parse/Load)    │
      └────────┬────────┘             └────────┬────────┘
               │                               │
               │ Customer-Supplier             │ Customer-Supplier
               │                               │
      ┌────────▼────────┐             ┌────────▼────────┐
      │ DataProcessing  │             │     Analysis    │
      │  (Cleaner,      │             │  (WindRose,     │
      │   Reconstruct)  │             │   Weibull)      │
      └────────┬────────┘             └────────┬────────┘
               │                               │ Conformist
               │ Customer-Supplier             │
               │                               │
      ┌────────▼────────┐                      │
      │    Reporting    │◄─────────────────────┘
      │ (ReportAtoms)   │
      └─────────────────┘
```

## ADR Naming Conventions

| Prefix | Category | Example |
|--------|----------|---------|
| `ddd-s-*` | Strategic DDD | `ddd-s-001-bounded-contexts` |
| `structure-*` | Project structure | `structure-001-subdomain-layout` |
| `persistence-*` | Data storage | `persistence-001-parquet-storage` |
| `pipeline-*` | Workflow | `pipeline-001-orchestration` |

**Current ADRs**: 5

---

**Recommended Loading**: README + 1-2 task-specific ADRs
