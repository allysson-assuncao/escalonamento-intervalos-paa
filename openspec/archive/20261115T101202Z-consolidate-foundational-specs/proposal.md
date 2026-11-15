# Proposal: Consolidate Foundational Specs

> **Change ID:** `consolidate-foundational-specs`
> **Status:** approved
> **Author:** `@allysson-assuncao`
> **Created:** 2026-11-15
> **Last Updated:** 2026-11-15

---

## Summary

This change initializes the Spec-Driven Development (SDD) governance structure for `escalonamento-intervalos-paa` and consolidates all academic assignment requirements, domain modeling, mathematical proofs, algorithmic specifications, comparative architecture, testing strategy, and visual interface guidelines from the initial Portuguese draft documents (`enunciado.txt`, `resumo_tema_e_viabilidade.md`, and `definicao_problema_e_decisoes.md`) into three authoritative, 100% English canonical living specifications under `openspec/specs/`. Once consolidated, the legacy root draft files are removed to maintain a clean, single-source-of-truth specification repository.

## Motivation

At project inception, the problem definition, complexity justification, authorial domain adaptations, and academic assignment rules were scattered across three unstructured Portuguese files in the repository root (`enunciado.txt`, `resumo_tema_e_viabilidade.md`, and `definicao_problema_e_decisoes.md`). Moreover, two minor variations existed in those early notes regarding whether the hospital model uses a single shift-change break `[A, B]` or multiple maintenance windows `[a_k, b_k]`. Consolidating all requirements into formal English OpenSpec living specifications eliminates ambiguity, establishes an auditable mathematical contract before any Python code is written, enforces the workspace engineering conventions via `.agents/rules/AGENTS.md` and `openspec/specs/sdd-stack-contract.md`, and prepares the project for subsequent phased implementation changes.

## Scope

### In Scope
- Initialize `.agents/` (`rules/`, `agents/`, `skills/`) and `openspec/` (`specs/`, `changes/`, `archive/`) directories.
- Create `.agents/rules/AGENTS.md` defining language boundaries (`pt-BR` for user interaction, code comments, docstrings, and Git commits; `en-US` for identifiers and `openspec/` documents), Python 3.12+ / `pytest` stack constraints, SOLID/Clean Code standards, coexistence of Classic and Adapted solvers, and shift-left testing obligations.
- Populate `openspec/specs/sdd-stack-contract.md` and seed `openspec/specs/_template.md`.
- Author three canonical living specifications (100% English):
  1. `problem-definition-and-mathematical-model.md`
  2. `algorithms-and-domain-architecture.md`
  3. `testing-benchmark-and-visual-interface.md`
- Harmonize and lock the official adapted rule: closing horizon $H$ plus at most one optional fixed shift-change window $[A, B]$, with parallel automated sterilization $[f_i, f_i + c_i]$ and Effective Release Time $r_i$.
- Remove the superseded draft files (`enunciado.txt`, `resumo_tema_e_viabilidade.md`, `definicao_problema_e_decisoes.md`) from the workspace root after complete knowledge capture.

### Out of Scope
- Writing Python source modules under `src/` (deferred to Change #2 for Classic Baseline and Change #3 for Adapted Authorial solvers).
- Writing `pytest` test files under `tests/` (deferred to Change #2 and Change #3).
- Selecting a specific UI toolkit or implementing the visual demonstration interface (deferred to Change #4).
- Updating `README.md` with execution instructions (deferred to Change #4).

## Proposed Solution

### Approach
Following SDD governance, we isolate documentation consolidation into its own dedicated change (`consolidate-foundational-specs`). Every mathematical symbol, complexity table, counterexample, proof sketch, and engineering constraint from the three Portuguese source files is translated, verified for internal consistency, and structured into three modular canonical specifications matching `openspec/specs/_template.md`:
1. **`problem-definition-and-mathematical-model.md`** captures the PAA course mandate, classical Interval Scheduling formulation, authorial Operating Room adaptation (Clean vs. Contaminated biological risk, automated ozone/UV sterilization cooldown $c_i$, closing horizon $H$, and shift-change window $[A, B]$), closed-form Effective Release Time $r_i$, non-reducibility proof with the 3-surgery counterexample, exchange-argument/DP-recurrence optimality proofs, and asymptotic complexity parity ($\mathcal{O}(n \log n)$ general, $\mathcal{O}(n)$ pre-sorted).
2. **`algorithms-and-domain-architecture.md`** specifies immutable domain entities, input invariants, shared scheduler protocols (SOLID Dependency Inversion), both Classic Baseline solvers (retained permanently for code, runtime, and optimality comparison), both Adapted Authorial solvers (Greedy and DP with backtracking reconstruction), and the planned `src/` / `tests/` package layout.
3. **`testing-benchmark-and-visual-interface.md`** defines the pre-configured deterministic test scenarios, brute-force exact oracle ($n \le 20$), empirical runtime benchmark harness, and visual presentation requirements (timeline/Gantt chart differentiating active medical work from automated sterilization).

### Impacted Files
| File | Change Type | Notes |
|------|-------------|-------|
| `.agents/rules/AGENTS.md` | Create | Workspace-global agent and engineering rules (< 50 lines) |
| `openspec/specs/_template.md` | Create | Standard living specification template |
| `openspec/specs/sdd-stack-contract.md` | Create | Python 3.12+ / `pytest` / Standard Library stack contract |
| `openspec/specs/problem-definition-and-mathematical-model.md` | Create | Canonical academic, domain, and mathematical spec |
| `openspec/specs/algorithms-and-domain-architecture.md` | Create | Canonical data model, solver algorithms, and SOLID architecture spec |
| `openspec/specs/testing-benchmark-and-visual-interface.md` | Create | Canonical test cases, brute-force oracle, benchmark, and UI requirements spec |
| `enunciado.txt` | Delete | Superseded after 100% English capture in `openspec/specs/` |
| `resumo_tema_e_viabilidade.md` | Delete | Superseded after 100% English capture in `openspec/specs/` |
| `definicao_problema_e_decisoes.md` | Delete | Superseded after 100% English capture in `openspec/specs/` |

### Data Model Changes (if applicable)
This change introduces the specification (not yet Python code) for immutable domain entities: `SurgeryType` (`CLEAN`, `CONTAMINATED`), `ShiftWindow` (`start`, `end`), `ShiftConfig` (`closing_horizon`, optional `shift_window`), `SurgeryRequest` (`id`, `start_time`, `finish_time`, `surgery_type`, `sterilization_duration`), `ProcessedSurgery` (adds `effective_release_time`), and `SchedulingResult` (scheduled subset, count, metrics, execution time).

## Acceptance Criteria

- [ ] **Given** the original Portuguese files (`enunciado.txt`, `resumo_tema_e_viabilidade.md`, `definicao_problema_e_decisoes.md`), **When** `consolidate-foundational-specs` is audited and consolidated, **Then** 100% of the assignment requirements, domain rationale, mathematical formulas, 3-surgery counterexample, optimality arguments, and complexity tables are preserved in English inside `openspec/specs/`.
- [ ] **Given** the ambiguity in earlier drafts between single vs. multiple shift-change windows, **When** inspecting `problem-definition-and-mathematical-model.md`, **Then** the official model strictly defines a closing horizon $H$ and an optional single shift-change window $[A, B]$ with the closed-form Effective Release Time formula $r_i = B$ if $f_i \le A$ and $A < f_i + c_i < B$, else $r_i = f_i + c_i$.
- [ ] **Given** the requirement to maintain classic solutions as a comparative baseline, **When** inspecting `algorithms-and-domain-architecture.md`, **Then** both Classic (Greedy + DP) and Adapted (Greedy + DP) schedulers share a unified contract and are designed to coexist through project completion.
- [ ] **Given** all files inside `openspec/` and `.agents/`, **When** reviewing language compliance, **Then** 100% of `openspec/` documents are written in English (`en-US`) and `.agents/rules/AGENTS.md` enforces `pt-BR` for agent-user interaction, inline comments, docstrings, and Git commits, and `en-US` for source identifiers.
- [ ] **Given** the canonical specifications are persisted in `openspec/specs/`, **When** Change #1 is archived, **Then** `enunciado.txt`, `resumo_tema_e_viabilidade.md`, and `definicao_problema_e_decisoes.md` are removed from the workspace root, leaving only `README.md`, `LICENSE`, `.agents/`, and `openspec/`.

## Defensive Security & Validation Considerations

### Input Validation
- Specifications explicitly mandate strict domain validation invariants before scheduling: non-negative timestamps ($s_i \ge 0$), strict duration ($s_i < f_i$), non-negative sterilization ($c_i \ge 0$), type consistency ($t_i = \text{CLEAN} \implies c_i = 0$ and $t_i = \text{CONTAMINATED} \implies c_i > 0$), positive horizon ($H > 0$), and valid shift-change window ($0 \le A < B \le H$).
- Out-of-bounds or malformed inputs must raise explicit domain validation exceptions (`ValueError` / `InvalidSurgeryError`) rather than silently corrupting schedules.

### Secret Isolation
- N/A — this is an offline algorithmic and academic project with zero credentials, tokens, or external API integrations. No secrets are present or permitted in any spec or future configuration.

### Authorization & Authentication Impact
- N/A — this change defines algorithmic specifications and does not expose network endpoints or modify authentication logic.

### Other Security Risks
- **Denial of Service via Malformed or Excessive Brute-Force Input**: Specifications restrict the exact brute-force oracle strictly to small verification instances ($n \le 20$) and enforce a hard guard error if invoked on larger inputs to prevent exponential $\mathcal{O}(2^n)$ resource exhaustion.

## Testing Strategy & Shift-Left Plan

### Happy Path Tests
| Test ID | Scenario | Test Type | Expected Result |
|---------|----------|-----------|-----------------|
| TP-01 | Audit of SDD structure, stack contract, and canonical English specs via `sdd-spec-auditor` | Spec Audit | Verdict is `Approved` with zero missing requirements from legacy drafts |
| TP-02 | Cross-check of all mathematical formulas and 3-surgery counterexample consistency across the 3 canonical specs | Spec Review | All symbols ($s_i, f_i, t_i, c_i, H, A, B, r_i, p(i)$) and expected counts match across specs |

### Edge Case & Failure Mode Tests
| Test ID | Scenario | Test Type | Expected Result |
|---------|----------|-----------|-----------------|
| TE-01 | Verify no `-delta.md` files exist in `openspec/specs/` and no Portuguese prose remains in `openspec/` | Structural Check | Zero `*-delta.md` files in `openspec/specs/`; 100% English content inside `openspec/` |
| TE-02 | Verify `.agents/rules/AGENTS.md` contains no YAML frontmatter and stays under 50 lines | Rule Lint | Plain Markdown file under 50 lines (`wc -l < 50`) |

### Test Commands
- **Spec & Structure Verification:** `ls -la && find .agents openspec -maxdepth 4 | sort && wc -l .agents/rules/AGENTS.md`
- **Future Code Test Runner (defined for Changes #2+):** `pytest -v`

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Loss of subtle mathematical nuance or examples when removing Portuguese draft `.md` files | Med | High | Perform a line-by-line completeness checklist verifying every formula, rule, example, and assignment constraint is in `openspec/specs/` before deleting root draft files |
| Ambiguity around `A <= e_i < B` vs `A < e_i < B` at exact shift boundary $A$ | Low | Med | Explicitly formalize and test boundary behavior at $f_i = A$ and $e_i \in (A, B)$ in both `problem-definition-and-mathematical-model.md` and `testing-benchmark-and-visual-interface.md` |
| Premature scoping of UI frameworks before algorithm validation | Low | Low | Lock UI framework as `TBD` in `sdd-stack-contract.md` and capture only functional visualization needs in `testing-benchmark-and-visual-interface.md` |

## Specification Changes & Delta Stubs

### `specs/problem-definition-and-mathematical-model.md`
- **Target Canonical Spec:** `New Specification` (`openspec/specs/problem-definition-and-mathematical-model.md`)
- **Summary of Updates:** Full formalization of the PAA assignment rules, classical Interval Scheduling baseline, Operating Room adaptation (biological classification, automated sterilization, shift-change window $[A, B]$, closing horizon $H$), $r_i$ formula, non-reducibility proof, 3-surgery counterexample, optimality proofs, and complexity table.

### `specs/algorithms-and-domain-architecture.md`
- **Target Canonical Spec:** `New Specification` (`openspec/specs/algorithms-and-domain-architecture.md`)
- **Summary of Updates:** Domain models, validation invariants, SOLID scheduler protocols, Classic Greedy & DP designs (retained as baseline), Adapted Greedy & DP designs, pre-sorted $\mathcal{O}(n)$ mode, and planned `src/` / `tests/` structure.

### `specs/testing-benchmark-and-visual-interface.md`
- **Target Canonical Spec:** `New Specification` (`openspec/specs/testing-benchmark-and-visual-interface.md`)
- **Summary of Updates:** Pre-configured deterministic test suites, brute-force oracle guard ($n \le 20$), empirical asymptotic complexity benchmark protocol, and visual timeline/Gantt presentation requirements.

## References

- Legacy workspace sources being consolidated and superseded: `enunciado.txt`, `resumo_tema_e_viabilidade.md`, `definicao_problema_e_decisoes.md`
- Project governance: `.agents/rules/AGENTS.md` and `openspec/specs/sdd-stack-contract.md`
