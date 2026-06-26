---
name: spec-guardrails
description: Teaches agents how to write and verify spec.md files. Triggers on spec, verify spec, check pipeline, enforce rules, spec.md, import-linter, ast-grep rules.
license: MIT
compatibility:
  python: ">=3.12"
  uv: ">=0.4"
metadata:
  category: architecture
  tier: foundational
  tags: [spec, guardrails, enforcement, pipeline, verification, ast-grep, import-linter]
  scope: project-level
---

## Overview

Spec-guardrails replaces adr-guardrails-skill. One co-located `spec.md` per context or capability replaces 40+ ADR phase files. Enforcement is three-tier: import-linter for dependency direction, ast-grep for structural patterns, and an LLM checklist for judgment rules. Drift tracking records deviations between spec and code.

## When to Use

- Writing a new `spec.md`
- Verifying an existing spec or running pipeline checks
- Adding or reviewing enforcement rules
- Reading or editing `drift-log.md` files (see `references/drift-spec.md`)

## Reference Index

| File | Description |
|------|-------------|
| `references/spec-template.md` | The 4-section spec.md format and what makes a rule spec-worthy |
| `references/enforcement-tiers.md` | Import-linter, ast-grep, and LLM checklist enforcement |
| `references/drift-spec.md` | Drift-log format, status lifecycle, recording protocol, and archival rules |
