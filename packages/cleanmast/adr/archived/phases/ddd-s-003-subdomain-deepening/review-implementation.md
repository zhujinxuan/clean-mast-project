# Review Implementation — ddd-s-003-subdomain-deepening

> **ADR**: `ddd-s-003-subdomain-deepening.md`
> **Method**: `agentic-lint` — subagent runs 9 checks against actual code.
> **Invocation**: Read by Atlas during final verification via `review-implementation.md` enforcement framework.
>
> **Enforcement framework**: `packages/cleanmast/.agents/skills/adr-guardrails-skill/review-implementation.md`
>
> **Target code root**: `packages/cleanmast/src/cleanmast/subdomains/assessment/`

---

## Pre-Check: Scope Detection

Before running checks, determine which subdomains have code:

```bash
ls -d packages/cleanmast/src/cleanmast/subdomains/assessment/subdomains/*/entities/*.py \
       packages/cleanmast/src/cleanmast/subdomains/assessment/subdomains/*/services/*.py \
       2>/dev/null | sed 's|.*/subdomains/\([^/]*\)/.*|\1|' | sort -u
```

**If a subdomain has only `__init__.py` files (no entities or services):** skip checks 1, 7, 9 for that subdomain. It is a scaffold-only directory with nothing to verify.

**Migration note:** In the current early phase, only `wind_rose`, `extreme_wind`, and `weibull` have directory scaffolding. Most checks will operate against the `domain/` directory (existing legacy entities) as a cross-reference.

---

## Check Category A: Import Isolation

> **ADR Source**: `import-contracts.md` §3.1 — "Cross-Subdomain Imports"
> **ADR Principle**: "Physical isolation = enforced discipline. If two capabilities share a directory, they will cross-import. Directories ARE boundaries."
> **Severity**: BLOCKER (violation = REJECT)

### Check 1: Cross-Subdomain Import — wind_rose

| Field | Value |
|-------|-------|
| **ADR Constraint** | §3.1: No subdomain imports another subdomain's concrete types. A subdomain may only import from `shared/`, parent `adapters/` (via protocols), and itself. |
| **Tool** | `grep` |
| **Command** | `grep -rn "from.*\.wind_rose\." --include="*.py" packages/cleanmast/src/cleanmast/subdomains/assessment/subdomains/ \| grep -v "/wind_rose/"` |
| **Expected Result (PASS)** | **0 matches.** The grep returns empty. `-v "/wind_rose/"` excludes self-imports, so any match is a cross-subdomain violation from another subdomain into wind_rose. |
| **Rollup** | Combine with Check 3 (all 10 subdomains) for final verdict. |

**Rationale**: A `from ..wind_rose.entities import WindRoseAtom` anywhere outside `wind_rose/` is a violation. The parent orchestrator alone may import subdomain services (§4 import-contracts.md). Other subdomains must communicate via `shared.protocols` or through the parent.

### Check 2: Cross-Subdomain Import — extreme_wind

| Field | Value |
|-------|-------|
| **ADR Constraint** | §3.1: Same as Check 1. |
| **Tool** | `grep` |
| **Command** | `grep -rn "from.*\.extreme_wind\." --include="*.py" packages/cleanmast/src/cleanmast/subdomains/assessment/subdomains/ \| grep -v "/extreme_wind/"` |
| **Expected Result (PASS)** | **0 matches.** No code outside `extreme_wind/` imports from extreme_wind's modules. |

### Check 3: Cross-Subdomain Import — All 10 Subdomains

| Field | Value |
|-------|-------|
| **ADR Constraint** | §3.1 + design-rationale.md L1 import-rule: "subdomain → shared/ + parent adapters/ (via protocols) + self only. No cross-subdomain imports" |
| **Tool** | `bash` (loop) |
| **Command** | ```bash
DOMAINS="air_density extreme_wind iec_standards representative_year turbulence vertical_profile weibull wind_frequency wind_rose wind_temporal"
for d in $DOMAINS; do
  results=$(grep -rn "from.*\.$d\." --include="*.py" packages/cleanmast/src/cleanmast/subdomains/assessment/subdomains/ | grep -v "/$d/")
  if [ -n "$results" ]; then
    echo "VIOLATION [$d]: $results"
  fi
done
``` |
| **Expected Result (PASS)** | **0 violations.** No output from the loop. Every subdomain is isolated — no code imports from a peer subdomain's directory. |
| **Note** | This check also catches violations in _any_ subdomain (not just the two with ADR files). If a future subdomain (e.g., `weibull` after code is added) imports from `wind_rose`, it fails here. |

---

## Check Category B: shared/ Purity

> **ADR Source**: design-rationale.md L2 Principle 2 — "shared/ is a contract surface, not a dumping ground."
> **ADR Constraint**: shared/ contains abstract protocols, IR types, and pure stateless utilities. No concrete implementations, no data-processing library imports.
> **Severity**: BLOCKER

### Check 4: shared/ — No Concrete Code in protocols/

| Field | Value |
|-------|-------|
| **ADR Constraint** | design-rationale.md L2 bullet 1: `shared/protocols/` contains Section, ReportAtom, DataSetAccess (ABCs). No concrete implementations. |
| **Tool** | `bash` (ls + filter) |
| **Command** | `ls packages/cleanmast/src/cleanmast/subdomains/assessment/shared/protocols/*.py` |
| **Expected Result (PASS)** | Only `__init__.py` is present. Any additional `.py` files (e.g., `concrete_thing.py`) indicate concrete code has leaked into the protocol contract surface. **Current state**: PASS (only `__init__.py` exists). |
| **Note** | During migration, protocol ABCs (`Section`, `ReportAtom`, `DataSetAccess`) will be created here. Those are abstract type definitions — NOT concrete code. This check verifies that no `.py` files with concrete implementations or data-processing logic exist. A file defining only ABCs is acceptable when the migration reaches that phase. |

### Check 5: shared/ — No Data-Processing Libraries

| Field | Value |
|-------|-------|
| **ADR Constraint** | design-rationale.md L2 Principle 2 + import-contracts.md §3.2: shared/ must not depend on data-processing frameworks. |
| **Tool** | `grep` |
| **Command** | `grep -rn "import polars\|import pandas\|from polars\|from pandas" packages/cleanmast/src/cleanmast/subdomains/assessment/shared/` |
| **Expected Result (PASS)** | **Empty output.** No polars or pandas imports anywhere under `shared/`. |
| **Why** | shared/ is a contract surface — it must be pure. If shared/ depends on polars, every subdomain transitively depends on polars. |

### Check 6: shared/ — All Directories Have __init__.py

| Field | Value |
|-------|-------|
| **ADR Constraint** | structure-001-subdomain-layout: shared/ packages must be importable. |
| **Tool** | `bash` |
| **Command** | `find packages/cleanmast/src/cleanmast/subdomains/assessment/shared/ -type d -mindepth 1 -exec test -f {}/__init__.py \; -print` |
| **Expected Result (PASS)** | All subdirectories are listed (each has `__init__.py`): `protocols/`, `adapter_protocols/`, `ir_types/`, `utils/`. No directory is missing its package marker. |

---

## Check Category C: Per-Domain ADRs

> **ADR Source**: ddd-s-003-subdomain-deepening.md — "10 subdomains, 10 ADR files, 10 self-diagnoses"
> **ADR Constraint**: Each subdomain must have `adr-ddd-s-003-subdomain-deepening.md` documenting its Role, Concrete Structure, and Principles.
> **Severity**: WARNING (aspirational; early migration exempt)

### Check 7: Per-Domain ADR Files Exist

| Field | Value |
|-------|-------|
| **ADR Constraint** | design-rationale.md L1 bullet "per-domain ADR" + L2 Principle 3: "Ten subdomains, ten ADR files." |
| **Tool** | `bash` |
| **Command** | `ls packages/cleanmast/src/cleanmast/subdomains/assessment/subdomains/wind_rose/adr-ddd-s-003-subdomain-deepening.md packages/cleanmast/src/cleanmast/subdomains/assessment/subdomains/extreme_wind/adr-ddd-s-003-subdomain-deepening.md 2>&1` |
| **Expected Result (PASS)** | Both files exist: `wind_rose/adr-ddd-s-003-subdomain-deepening.md` and `extreme_wind/adr-ddd-s-003-subdomain-deepening.md`. |
| **Current State** | **PASS** — 2/10 subdomains have ADR files (wind_rose, extreme_wind). These are the only subdomains with entities/services scaffolding; the remaining 8 are empty scaffolds. |
| **Migration Note** | As each subdomain is populated with code (entities/, services/), its per-domain ADR must be created. Adjust expected count: 2 now → 10 at full migration. Until a subdomain has actual code files beyond `__init__.py`, the ADR is not required. |
| **Self-Diagnostic Post-Check** | For any ADR file that exists, verify: total lines ≤ ~40 (or the subdomain is too compressed — consider splitting). Use: `wc -l packages/cleanmast/src/cleanmast/subdomains/assessment/subdomains/*/adr-ddd-s-003-subdomain-deepening.md` |

---

## Check Category D: Domain Purity

> **ADR Source**: import-contracts.md §3.2 — "Polars/Pandas in Entities Layer"
> **ADR Principle**: "The entities layer is the core of the domain. Coupling it to a specific data library prevents testing with simple Python types, blocks framework migration, and violates the dependency rule."
> **Severity**: WARNING (target-state; current codebase has known gap — see import-contracts.md §3.2 Note)

### Check 8: Domain Purity — No Polars/Pandas in entities/

| Field | Value |
|-------|-------|
| **ADR Constraint** | §3.2: Entities are domain objects — they must not depend on data-processing frameworks. |
| **Tool** | `grep` |
| **Command** | `grep -rn "import polars\|import pandas\|from polars\|from pandas" packages/cleanmast/src/cleanmast/subdomains/assessment/domain/entities/` |
| **Expected Result (PASS)** | **0 matches.** No polars or pandas imports in any file under `domain/entities/`. |
| **Current State** | **EXPECTED FAIL** — The existing codebase (legacy migration) has `polars` in entities (e.g., `ReportAtom.df: pl.DataFrame`). This is a **known gap** documented in import-contracts.md §3.2 Note. Mark as `FAIL (acknowledged)` — tracked for future phase resolution. |
| **Subdomain-Specific Check** | Additionally check new subdomain entities: `grep -rn "import polars\|import pandas" packages/cleanmast/src/cleanmast/subdomains/assessment/subdomains/*/entities/` → **0 matches expected**. New code must not repeat the legacy pattern. |
| **Migration Path** | Polars types in `domain/entities/` must be replaced with domain-primitive types (Python builtins, Pydantic models without DataFrame fields). Tracked as a separate refactoring phase. |

---

## Check Category E: ADR-GUARDRAILS Comments

> **ADR Source**: ddd-s-003 enforcement protocol — each subdomain file must declare which ADRs govern it.
> **Severity**: WARNING

### Check 9: ADR-GUARDRAILS Comment in Every Non-__init__ Python File

| Field | Value |
|-------|-------|
| **ADR Constraint** | Enforcement framework: every file under a subdomain must declare its governing ADRs via `"""ADR-GUARDRAILS: ddd-s-003-..., structure-001-..."""` or equivalent comment. |
| **Tool** | `bash` (find + grep -L) |
| **Command** | ```bash
find packages/cleanmast/src/cleanmast/subdomains/assessment/subdomains/ \
  -name "*.py" \
  ! -name "__init__.py" \
  -exec grep -L "ADR-GUARDRAILS" {} \;
``` |
| **Expected Result (PASS)** | **Empty output.** Every `.py` file that is NOT `__init__.py` contains `ADR-GUARDRAILS`. |
| **Current State** | **PASS** — currently no non-`__init__.py` files exist under subdomains (all code is still in legacy `domain/`). This check will activate as subdomains are populated. |
| **Note** | `__init__.py` files are exempt — they already serve as package markers with ADR-GUARDRAILS (all 10 confirmed present). This check targets service, entity, and value_object modules. |

---

## Check Category F: Section Protocol Compliance

> **ADR Source**: ddd-s-003 — unified SectionService pattern.
> **ADR Constraint**: Every subdomain service must implement the Section protocol with `render_ir(self, images_dir: Path) -> TypstSection`.
> **Severity**: WARNING (aspirational; early migration exempt)

### Check 10: Section Protocol — render_ir Method Exists

| Field | Value |
|-------|-------|
| **ADR Constraint** | design-rationale.md L1 bullet "service pattern": "one unified SectionService per subdomain (calculates + builds + renders)." §2.3 import-contracts.md: every subdomain produces `TypstSection` output via `render_ir()`. |
| **Tool** | `ast-grep run` |
| **Command** | ```bash
ast-grep run \
  --pattern 'def render_ir(self, $$$): $$$' \
  --lang python \
  packages/cleanmast/src/cleanmast/subdomains/assessment/subdomains/
``` |
| **Expected Result (PASS)** | At least 1 match per subdomain that has services code. For the current migration state: **0 matches expected** (no services code written yet). As subdomains are populated, each service module must implement `render_ir`. |
| **Migration Note** | This is a forward-looking check. Until a subdomain's `services/` directory contains actual `.py` files (beyond `__init__.py`), this check is vacuously true (no code to violate). Once code exists, enforce: each `services/*_section.py` must contain `def render_ir`. |

---

## Check Category G: Parent Domain Boundaries

> **ADR Source**: import-contracts.md §3.4 — "Subdomains must NOT import the parent domain's internal implementation."
> **ADR Constraint**: Subdomains may import from `shared/` and `adapters/` (via protocols) but NEVER from `domain/{services,entities,value_objects}/`.
> **Severity**: BLOCKER

### Check 11: No Parent Domain Internals in Subdomains

| Field | Value |
|-------|-------|
| **ADR Constraint** | §3.4: `assessment.domain/*` is forbidden for subdomains. The parent domain is an orchestrator, not a dependency. |
| **Tool** | `grep` |
| **Command** | `grep -rn "from.*assessment\.domain\." --include="*.py" packages/cleanmast/src/cleanmast/subdomains/assessment/subdomains/` |
| **Expected Result (PASS)** | **0 matches.** No subdomain imports from the parent domain layer. |
| **Why it matters** | If a subdomain imports `AtomCollection` or `ReportAssemblyService`, it inverts the dependency: subdomains become coupled to the orchestrator. The parent calls subdomains — not the reverse. |

---

## Verdict Aggregation

| Outcome | Rule |
|---------|------|
| **APPROVE** | All BLOCKER checks PASS. WARNING-level failures are acknowledged with migration notes. |
| **REJECT (Hard Block)** | Any BLOCKER check FAILS. Code must not proceed. |
| **CONDITIONAL APPROVE** | All BLOCKER pass; some WARNING fail but are documented as "known gap — tracked in migration roadmap." |

### Current Expected Verdict (Early Migration Phase)

| Check # | Name | Category | Severity | Expected |
|---------|------|----------|----------|----------|
| 1 | Cross-subdomain import: wind_rose | Import Isolation | BLOCKER | PASS |
| 2 | Cross-subdomain import: extreme_wind | Import Isolation | BLOCKER | PASS |
| 3 | Cross-subdomain import: all 10 | Import Isolation | BLOCKER | PASS |
| 4 | shared/ no concrete code | shared/ Purity | BLOCKER | PASS |
| 5 | shared/ no data libs | shared/ Purity | BLOCKER | PASS |
| 6 | shared/ package markers | shared/ Purity | BLOCKER | PASS |
| 7 | Per-domain ADRs exist | Per-Domain ADRs | WARNING | PASS (2/2 of populated subdomains) |
| 8 | No polars/pandas in entities | Domain Purity | WARNING | FAIL (known gap) |
| 9 | ADR-GUARDRAILS in files | ADR-GUARDRAILS | WARNING | PASS (no non-init files yet) |
| 10 | Section protocol: render_ir | Section Protocol | WARNING | PASS (no service code yet) |
| 11 | No parent domain internals | Parent Boundaries | BLOCKER | PASS |

**Expected verdict: CONDITIONAL APPROVE** — all BLOCKER checks pass; Check 8 (domain purity) fails but is a documented known gap tracked for future phase resolution.

---

## Output Format (for subagent to return)

```markdown
ADR: ddd-s-003-subdomain-deepening (method: agentic-lint)
  Check  1: cross-subdomain-import-wind_rose  → PASS  (0 matches)
  Check  2: cross-subdomain-import-extreme_wind → PASS  (0 matches)
  Check  3: cross-subdomain-import-all-10     → PASS  (0 violations)
  Check  4: shared-no-concrete-code           → PASS  (only __init__.py)
  Check  5: shared-no-data-libs               → PASS  (0 matches)
  Check  6: shared-package-markers            → PASS  (all 4 dirs)
  Check  7: per-domain-adrs                   → PASS  (2/2 populated)
  Check  8: domain-purity-entities            → FAIL  (known gap: polars in domain/entities/)
  Check  9: adr-guardrails-in-files           → PASS  (no non-init files to check)
  Check 10: section-protocol-render_ir        → PASS  (no service code to check)
  Check 11: no-parent-domain-internals        → PASS  (0 matches)

  VERDICT: CONDITIONAL APPROVE (1 acknowledged known gap)
```

---

## References

| Reference | Location |
|-----------|----------|
| Main ADR | `packages/cleanmast/adr/ddd-s-003-subdomain-deepening.md` |
| Import Contracts | `packages/cleanmast/adr/phases/ddd-s-003-subdomain-deepening/import-contracts.md` |
| Design Rationale | `.sisyphus/design-rationale.md` |
| Enforcement Framework | `packages/cleanmast/.agents/skills/adr-guardrails-skill/review-implementation.md` |
| Subdomain Code Root | `packages/cleanmast/src/cleanmast/subdomains/assessment/subdomains/` |
