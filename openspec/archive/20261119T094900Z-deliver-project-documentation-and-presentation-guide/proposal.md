# Proposal: Deliver Project Documentation and Presentation Guide

> **Change ID:** `deliver-project-documentation-and-presentation-guide`
> **Status:** approved
> **Author:** `@allysson-assuncao`
> **Created:** 2026-11-18
> **Last Updated:** 2026-11-18

---

## Summary

This change delivers the final academic documentation package of `escalonamento-intervalos-paa` to support project submission, reproducible execution, and live classroom presentation: a comprehensive root `README.md` (`pt-BR`), an empirical test, oracle, and complexity benchmark report at `docs/relatorio-testes-benchmark-complexidade.md` (`pt-BR`), a 5-module codebase mastery and presentation study guide at `docs/guia-revisao-arquitetura-e-apresentacao.md` (`pt-BR`) referencing exact source files and line intervals (`#Lxx-Lyy`), and an automated integrity test suite at `tests/test_documentation_integrity.py` verifying that all documented local links and line-range anchors remain valid.

## Motivation

Requirement #5 of `openspec/specs/problem-definition-and-mathematical-model.md` and Section 4.4 of `openspec/specs/testing-benchmark-and-visual-interface.md` mandate clear project documentation, reproducible setup/execution instructions, empirical complexity evidence, and presentation support materials. Providing both an executive `README.md` and dedicated `docs/` guides—backed by automated `pytest` validation of all `#Lxx-Lyy` code anchors—ensures that every presenter in the group has complete mastery over the mathematical formulation, algorithmic adaptations, benchmark evidence, and interactive UI mechanics without introducing stale code references.

## Scope

### In Scope
- **Phase 1 — Root Documentation (`README.md`)**:
  - Rewrite `README.md` in clear, objective Brazilian Portuguese (`pt-BR`) covering: academic context, classical Interval Scheduling problem vs. authorial operating-room extensions ($t_i$, $c_i$, $H$, $[A, B]$), closed-form Effective Release Time ($r_i$) formula, the canonical `SC-02` non-reducibility counterexample, repository architecture, environment setup (`venv` + `pytest`), CLI modes (`--scenario`, `--benchmark`), local Web UI launch instructions, and links to the detailed reports in `docs/`.
- **Phase 2 — Empirical Tests, Benchmark & Complexity Report (`docs/relatorio-testes-benchmark-complexidade.md`)**:
  - Execute the project's actual test suite (`pytest`) and empirical scaling benchmark (`run_scaling_benchmark` for $n \in \{100, 500, 1000, 2500, 5000, 10000\}$ across both general $\mathcal{O}(n \log n)$ and pre-sorted $\mathcal{O}(n)$ modes) and document the observed tables, normalized ratios ($T(n)/(n \log_2 n)$ and $T(n)/n$), Mermaid `xychart-beta` visualizations, scenario-by-scenario (`SC-01`..`SC-05b`) outcome analysis, and the 180-instance `BruteForceOracleScheduler` cross-validation evidence.
- **Phase 3 — 5-Module Architecture & Presentation Study Guide (`docs/guia-revisao-arquitetura-e-apresentacao.md`)**:
  - Author a structured 5-module study and presentation guide (`pt-BR`):
    1. **Architecture & SOLID**: Layered architecture, unidirectional dependency rules, immutability, and Mermaid component/flow diagrams.
    2. **Code-by-Code Dissection**: Detailed walkthrough of every core module and function across `src/domain/`, `src/schedulers/`, `src/benchmark/`, `src/ui/`, and `src/main.py` using clickable relative Markdown links with exact line intervals (`#Lxx-Lyy`) and step-by-step time/space complexity explanations.
    3. **Tracer & Visual Interface Internals**: How `src/ui/tracer.py` isolates `schedule()` timing (`[RNF-02]`), captures multi-stage snapshots (`phase_offsets`), serves JSON endpoints via `src/ui/server.py`, and renders native SVG Gantt/arrays/charts with XSS and `HH:MM` guards in `src/ui/static/`.
    4. **Live Presentation Walkthrough & Validation Script**: Step-by-step live demo script covering the `HH:MM` input editor and Tabs 1, 2, and 3 (`SC-02`, `SC-04b`/`SC-04c`, benchmark curves).
    5. **Examining-Board Defense FAQ**: Concise, rigorous answers to anticipated academic questions (why naive $f'_i = f_i + c_i$ fails, exchange argument proof for $r_i$, $\mathcal{O}(n)$ pre-sorted DP two-pointers vs. `bisect_right`, and `elapsed_ns` isolation).
- **Phase 4 — Automated Documentation Integrity Suite (`tests/test_documentation_integrity.py`)**:
  - Implement `pytest` checks validating the existence and required structure of `README.md` and `docs/*.md`, parsing all relative Markdown links, and verifying that every referenced file exists and every `#L<line>` or `#L<start>-L<end>` anchor satisfies $1 \le \text{start} \le \text{end} \le \text{total\_lines}$.

### Out of Scope
- Functional modifications to `src/domain/`, `src/schedulers/`, `src/benchmark/`, `src/ui/`, or `src/main.py`.
- Adding external documentation tooling (Sphinx, MkDocs, Pandoc) or third-party runtime/test dependencies.

## Proposed Solution

### Approach
1. **Verified Empirical Data Gathering**: Before authoring `docs/relatorio-testes-benchmark-complexidade.md`, execute `pytest` and `src/main.py --benchmark` (both unsorted and `--presorted` modes across $n \in \{100, 500, 1000, 2500, 5000, 10000\}$) so every reported timing, ratio, and test count comes directly from observed project runs on the current codebase.
2. **Exact Source Line Anchoring**: Map exact file paths and `#Lxx-Lyy` line intervals across `src/` via subagent/source verification when authoring `docs/guia-revisao-arquitetura-e-apresentacao.md`, using repository-relative Markdown links (e.g., `../src/schedulers/adapted_dp.py#L19-L68` inside `docs/` and `docs/...` inside `README.md`) so links work cleanly both in GitHub/IDE viewers and offline clones.
3. **Shift-Left Documentation Guard (`tests/test_documentation_integrity.py`)**: Add lightweight deterministic regex/AST-free Markdown link checks to `tests/` so future edits to `src/` cannot silently invalidate line numbers or file paths cited in `README.md` or `docs/*.md`.

### Impacted Files
| File | Change Type | Notes |
|------|-------------|-------|
| `README.md` | Modify | Full project overview, mathematical summary, setup, CLI/UI usage, and `docs/` navigation (`pt-BR`) |
| `docs/relatorio-testes-benchmark-complexidade.md` | Create | Observed test/oracle results, scaling benchmark tables ($n=100..10000$), Mermaid `xychart-beta`, and `SC-01..SC-05b` analysis (`pt-BR`) |
| `docs/guia-revisao-arquitetura-e-apresentacao.md` | Create | 5-module study & presentation guide with `#Lxx-Lyy` references, UI internals, demo script, and Defense FAQ (`pt-BR`) |
| `tests/test_documentation_integrity.py` | Create | Automated `pytest` checks for doc structure, relative links, `#Lxx-Lyy` bounds, and secret hygiene |

### Data Model Changes (if applicable)
N/A — pure documentation and documentation-verification test change; zero runtime data model modifications.

## Acceptance Criteria

- [x] **Given** `README.md` in the repository root, **When** read by an evaluator or student, **Then** it is written in clear Brazilian Portuguese (`pt-BR`) and covers problem background, authorial constraints ($t_i$, $c_i$, $H$, $[A, B]$), $r_i$ closed-form formula, `SC-02` counterexample, setup instructions, `pytest` execution, CLI (`--scenario`, `--benchmark`) and Web UI launch commands, and valid links to both documents in `docs/`.
- [x] **Given** `docs/relatorio-testes-benchmark-complexidade.md`, **When** reviewed against actual benchmark and test outputs, **Then** it includes directly observed tables for $n \in \{100, 500, 1000, 2500, 5000, 10000\}$ in both general $\mathcal{O}(n \log n)$ and pre-sorted $\mathcal{O}(n)$ modes, valid Mermaid `xychart-beta` plots, `SC-01`..`SC-05b` comparative outcomes, and the 180-instance `BruteForceOracleScheduler` validation summary.
- [x] **Given** `docs/guia-revisao-arquitetura-e-apresentacao.md`, **When** used to prepare for the classroom presentation, **Then** it contains all 5 modules (Architecture & SOLID with Mermaid diagrams, Code-by-Code dissection with clickable `#Lxx-Lyy` references, Tracer & SVG UI internals, Live 3-Tab Walkthrough, and Defense FAQ).
- [x] **Given** `tests/test_documentation_integrity.py`, **When** `C:\Python314\python.exe -m pytest -v -p no:cacheprovider` runs, **Then** it verifies every relative Markdown link and `#L<start>-L<end>` anchor across `README.md` and `docs/*.md`, checks for zero secret leaks, and passes alongside all 63 existing tests in under 5 seconds total (`[RNF-01]`).

## Defensive Security & Validation Considerations

### Input Validation
- `tests/test_documentation_integrity.py` validates relative link targets strictly within the repository root using `Path.resolve().is_relative_to(repo_root)` and parses line numbers safely with explicit integer bounds checking.

### Secret Isolation
- Confirm zero credentials, tokens, API keys, or local machine absolute paths (`C:\Users\...`) are hardcoded in `README.md` or `docs/*.md` (portable relative Markdown links only).

### Authorization & Authentication Impact
- N/A — static Markdown documentation and read-only `pytest` link verification tests; no endpoints or auth logic are added or modified.

### Other Security Risks
- **Stale Documentation / Broken Line Anchors**: Mitigated by running `tests/test_documentation_integrity.py` on every `pytest` run to fail fast if any cited file path or line range drifts out of bounds.

## Testing Strategy & Shift-Left Plan

### Happy Path Tests
| Test ID | Scenario | Test Type | Expected Result |
|---------|----------|-----------|-----------------|
| TP-01 | Required documentation files (`README.md`, `docs/relatorio-testes-benchmark-complexidade.md`, `docs/guia-revisao-arquitetura-e-apresentacao.md`) exist and include all mandated sections | Unit | All three files exist, are non-empty UTF-8 Markdown, and contain required headings |
| TP-02 | Every relative Markdown link in `README.md` and `docs/*.md` resolves to an existing repository file | Unit | Zero broken file links across all documentation files |
| TP-03 | Every `#L<line>` or `#L<start>-L<end>` anchor in `README.md` and `docs/*.md` falls within `[1, total_lines]` of the target file | Unit | Zero out-of-range line references; key cited symbols appear inside cited line ranges |
| TP-04 | Full `pytest` suite (`tests/`) runs deterministically after documentation completion | Integration | All existing 63 tests + new documentation integrity tests pass in under 5 seconds (`[RNF-01]`) |

### Edge Case & Failure Mode Tests
| Test ID | Scenario | Test Type | Expected Result |
|---------|----------|-----------|-----------------|
| TE-01 | Verification helper behavior on inverted line ranges (`#L50-L10`), out-of-bounds lines, or missing target files | Unit | Validation helper raises `AssertionError` / rejects invalid anchors cleanly |
| TE-02 | Portability & security check for accidental absolute machine paths (`C:/Users/...`) or secret tokens in `README.md` / `docs/*.md` | Unit / Security | Zero machine-specific absolute paths or secret keywords present in documentation |
| TE-03 | Unclosed Mermaid fenced code blocks or malformed `xychart-beta` blocks check | Unit | Even number of triple-backtick code fences in every Markdown document |

### Test Commands
- **Run full suite:** `C:\Python314\python.exe -m pytest -v -p no:cacheprovider`
- **Secret & absolute-path scan:** Verified deterministically inside `tests/test_documentation_integrity.py` and via `Select-String`

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Line numbers `#Lxx-Lyy` drift if `src/` is edited later | Med | Med | `tests/test_documentation_integrity.py` validates all `#Lxx-Lyy` anchors and cited symbol presence automatically |
| Benchmark numbers in report differ across CPU loads | Low | Low | Record exact test parameters (`seed`, `repetitions`, hardware/Python version, command) and emphasize asymptotic ratio stability $T(n)/(n \log_2 n)$ |
| Hardcoded absolute local paths breaking links on teammates' clones | Med | High | Enforce repository-relative links exclusively and assert zero `C:\` / `file:///` links in `tests/test_documentation_integrity.py` |

## Specification Changes & Delta Stubs

### `specs/algorithms-and-domain-architecture-delta.md`
- **Target Canonical Spec:** `openspec/specs/algorithms-and-domain-architecture.md`
- **Summary of Updates:** Updates Section 5 Repository Layout to include `docs/relatorio-testes-benchmark-complexidade.md`, `docs/guia-revisao-arquitetura-e-apresentacao.md`, and `tests/test_documentation_integrity.py`.

### `specs/testing-benchmark-and-visual-interface-delta.md`
- **Target Canonical Spec:** `openspec/specs/testing-benchmark-and-visual-interface.md`
- **Summary of Updates:** Updates Section 4.4 Documentation to record the finalized three-document structure (`README.md`, `docs/relatorio-testes-benchmark-complexidade.md`, `docs/guia-revisao-arquitetura-e-apresentacao.md`) and automated integrity verification (`tests/test_documentation_integrity.py`).

## References

- `openspec/specs/sdd-stack-contract.md`
- `openspec/specs/problem-definition-and-mathematical-model.md`
- `openspec/specs/algorithms-and-domain-architecture.md`
- `openspec/specs/testing-benchmark-and-visual-interface.md`
