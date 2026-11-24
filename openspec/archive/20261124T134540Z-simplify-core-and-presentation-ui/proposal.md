# Proposal: Simplify Core and Presentation UI

> **Change ID:** `simplify-core-and-presentation-ui`
> **Status:** draft
> **Author:** `@allysson-assuncao`
> **Created:** 2026-11-24
> **Last Updated:** 2026-11-24

---

## Summary

This change streamlines `escalonamento-intervalos-paa` into a focused, transparent, and easy-to-present PAA (*Projeto e Análise de Algoritmos*) academic deliverable by removing non-essential complexity across the core solvers, backend API, visual interface, tests, and documentation. Specifically, it retains the **4 core $\mathcal{O}(n \log n)$ algorithms** (`ClassicGreedyScheduler`, `ClassicDPScheduler`, `AdaptedGreedyScheduler`, `AdaptedDPScheduler`) plus the exact `BruteForceOracleScheduler` ($n \le 20$) for test verification, replaces the 8 fragmented `SC-*` scenario codes with **4 didactic presets** (`CASE-01`..`CASE-04`) alongside custom manual surgery editing, removes `NaiveReductionScheduler`, `src/benchmark/`, `is_presorted` / `presorted_start_indices` two-pointer permutation machinery, and the synthetic benchmark tab/random generator, and upgrades the **2-tab presentation UI** with an in-app Mathematical & Phase Complexity summary card, `HH:MM (min)` variable formatting, and vertically aligned shared-scale mini-Gantts.

## Motivation

During oral defense and live classroom presentation preparation, excessive scaffolding and unused options make the system harder to study, audit, and demonstrate reliably:
1. **Unused/Inconsistent Pre-Sorted Machinery**: The `presorted_start_indices` permutation parameter and two-pointer predecessor branch add validation complexity across `protocol.py`, `classic_dp.py`, `adapted_dp.py`, and `tracer.py`, yet neither the Web UI nor the benchmark harness passed `presorted_start_indices`, and toggling `"Entrada pré-ordenada"` on unsorted demo presets triggered an error banner.
2. **Extra Comparator & Benchmark Clutter**: Having a fifth `NaiveReductionScheduler`, a third synthetic benchmark tab, a random instance generator in the sidebar, and 8 micro-variation scenarios (`SC-01`..`SC-05b`) distracts from the assignment's core objective: explaining the classical problem, the surgical sterilization & shift-window constraints, the adapted Greedy/DP formulations, step-by-step data structures, and $\mathcal{O}(n \log n)$ complexity.
3. **Presentation Friction in the UI**: The simulator previously lacked an in-app mathematical formula & phase-complexity summary card, displayed raw integer minutes in the live variable watch, and rendered Tab 2 mini-Gantts with independent X-axis time scales that misaligned algorithms visually.

## Scope

### In Scope
- Remove `NaiveReductionScheduler` (`src/schedulers/naive_reduction.py`) and naive static-reduction helpers in `src/domain/preprocessing.py`.
- Remove `is_presorted`, `presorted_start_indices`, `validate_presorted_start_indices`, `_compute_predecessors_two_pointers`, and `_resolve_predecessors` from `src/schedulers/` and `src/ui/tracer.py`, standardizing all 4 primary schedulers on pure $\mathcal{O}(n \log n)$ sorting and `bisect_right` DP predecessor computation.
- Remove `src/benchmark/` (`__init__.py`, `runner.py`), benchmark/presorted CLI flags in `src/main.py`, and `docs/relatorio-testes-benchmark-complexidade.md`.
- Consolidate `src/ui/scenarios_catalog.py` into 4 didactic scenarios (`CASE-01`..`CASE-04`) while preserving manual surgery addition/deletion and shift constraint editing (`H`, `[A, B]`).
- Update `src/ui/tracer.py` to emit `complexity_summary` (asymptotic bounds, mathematical rules, and real per-phase operation counts), clean `pt-BR` variable labels with `HH:MM (min)` time formatting, and numeric `last_release_minutes` so the SVG Gantt cut line stays visible.
- Update `src/ui/server.py` to expose only `GET /api/scenarios`, `POST /api/trace`, and `POST /api/compare` (removing `/api/generate` and `/api/benchmark`).
- Simplify `src/ui/static/` (`index.html`, `styles.css`, `app.js`) to a 2-tab layout (`1. Simulador Passo a Passo` with the new Mathematical & Phase Complexity summary card, and `2. Comparativo dos 4 Algoritmos` with shared-axis aligned mini-Gantts).
- Update the automated `pytest` suite (`tests/`), `README.md`, and `docs/guia-revisao-arquitetura-e-apresentacao.md` to remain 100% synchronized with exact file/line anchors.

### Out of Scope
- Changing the mathematical rules of active feasibility ($f_i \le H$, $f_i \le A \lor s_i \ge B$) or effective release time $r_i$.
- Modifying `BruteForceOracleScheduler`'s $n \le 20$ branch-and-bound limit or domain immutability (`@dataclass(frozen=True)`).
- Adding external Python or JavaScript UI dependencies, databases, or multi-room scheduling.

## Proposed Solution

### Approach
The refactoring proceeds cleanly from the domain core outward to the presentation layer and verification suite so no broken intermediate dependencies remain:
1. **Domain & Schedulers (`src/domain/`, `src/schedulers/`)**: Remove naive static reduction and `is_presorted` / `presorted_start_indices` parameters across `IntervalSchedulerProtocol` and all 5 concrete scheduler classes (`ClassicGreedyScheduler`, `ClassicDPScheduler`, `AdaptedGreedyScheduler`, `AdaptedDPScheduler`, `BruteForceOracleScheduler`), deleting `src/schedulers/naive_reduction.py` and `src/benchmark/`. DP predecessor search simplifies to a single `compute_predecessors_binary_search` helper using `bisect.bisect_right`.
2. **UI Backend (`src/ui/scenarios_catalog.py`, `tracer.py`, `server.py`, `src/main.py`)**: Replace the 8 `SC-*` scenarios with 4 self-explanatory presets (`CASE-01`..`CASE-04`). Restrict `tracer.py` and `server.py` to the 4 primary algorithms and the 3 core routes (`/api/scenarios`, `/api/trace`, `/api/compare`). Enrich `SimulationTrace` with `complexity_summary` (rules, $\mathcal{O}(n \log n)$ time / $\mathcal{O}(n)$ space, and actual operation counts per phase) and clean `HH:MM (min)` variable formatting while keeping `last_release_minutes: int | None` on `SimulationStep` for the SVG marker.
3. **Lean 2-Tab Frontend (`src/ui/static/`)**: Remove Tab 3 (`#tab-benchmark`), the sidebar random generator, `#presorted-checkbox`, and `Tempo (ns)` noise in Tab 2. Add `#complexity-summary-card` in Tab 1 rendered via safe DOM methods (zero `innerHTML`). In Tab 2 (`runComparisonArena`), compute one shared `{ minT, maxT }` domain across all input surgeries and `shiftConfig` so all 4 mini-Gantts share the exact same horizontal timeline scale.
4. **Tests & Documentation (`tests/`, `README.md`, `docs/`)**: Update unit, oracle, tracer/HTTP, and documentation-integrity tests to reflect the simplified architecture and verify every `[symbol](path#Lxx-Lyy)` anchor after final edits.

### Impacted Files
| File | Change Type | Notes |
|------|-------------|-------|
| `src/schedulers/naive_reduction.py` | Delete | Remove `NaiveReductionScheduler` |
| `src/benchmark/__init__.py` | Delete | Remove benchmark package |
| `src/benchmark/runner.py` | Delete | Remove synthetic generator and empirical scaling runner |
| `docs/relatorio-testes-benchmark-complexidade.md` | Delete | Remove obsolete empirical benchmark report |
| `src/domain/preprocessing.py` | Modify | Remove `_is_naive_interval_feasible`, `preprocess_naive_validated_surgeries`, `preprocess_naive_static_reduction` |
| `src/domain/__init__.py` | Modify | Remove `preprocess_naive_static_reduction` export |
| `src/schedulers/protocol.py` | Modify | Remove `is_presorted`, `presorted_start_indices`, two-pointer helpers; expose `compute_predecessors_binary_search` |
| `src/schedulers/classic_greedy.py` | Modify | Remove `is_presorted` from `schedule()` |
| `src/schedulers/classic_dp.py` | Modify | Remove `is_presorted` and `presorted_start_indices` from `schedule()` |
| `src/schedulers/adapted_greedy.py` | Modify | Remove `is_presorted` from `schedule()` |
| `src/schedulers/adapted_dp.py` | Modify | Remove `is_presorted` and `presorted_start_indices` from `schedule()` |
| `src/schedulers/brute_force_oracle.py` | Modify | Remove `is_presorted` from `schedule()` |
| `src/schedulers/__init__.py` | Modify | Remove `NaiveReductionScheduler` export |
| `src/main.py` | Modify | Remove `--benchmark`, `--sizes`, `--repetitions`, `--seed`, `--presorted`, `naive_reduction` |
| `src/ui/__init__.py` | Modify | Remove benchmark/generate limit exports |
| `src/ui/scenarios_catalog.py` | Modify | Consolidate into 4 didactic scenarios `CASE-01`..`CASE-04` |
| `src/ui/tracer.py` | Modify | Support 4 algorithms; add `complexity_summary`, `last_release_minutes`, and `HH:MM (min)` variable labels |
| `src/ui/server.py` | Modify | Remove `/api/generate`, `/api/benchmark`, and `is_presorted` parsing; keep `/api/scenarios`, `/api/trace`, `/api/compare` |
| `src/ui/static/index.html` | Modify | 2-tab layout, 4-algorithm selector, complexity summary card; remove random generator & benchmark tab |
| `src/ui/static/styles.css` | Modify | Remove benchmark/chart styles; style complexity summary card & aligned mini-Gantts |
| `src/ui/static/app.js` | Modify | Remove benchmark/generator/presorted logic; render complexity card; pass shared X-axis domain to mini-Gantts |
| `tests/fixtures/scenarios.py` | Modify | Re-export `CASE-01`..`CASE-04` builders |
| `tests/test_preprocessing.py` | Modify | Remove naive reduction tests; verify `CASE-*` feasibility & $r_i$ |
| `tests/test_classic_schedulers.py` | Modify | Remove `is_presorted` / `presorted_start_indices` tests |
| `tests/test_adapted_schedulers.py` | Modify | Remove `NaiveReductionScheduler` & `presorted` tests; test `CASE-01`..`CASE-04` |
| `tests/test_oracle_and_comparison.py` | Modify | Remove `TestBenchmarkRunner` & `src.benchmark` imports; keep 180-instance oracle cross-validation |
| `tests/test_ui_tracer_and_server.py` | Modify | Test 4 scenarios, 4 algorithms, `complexity_summary`, `HH:MM` labels, 404 on removed routes, XSS/security checks |
| `tests/test_documentation_integrity.py` | Modify | Remove `REPORT_PATH` checks; update required markers for simplified `README.md` & presentation guide |
| `README.md` | Modify | Simplify overview, complexity table, CLI instructions, and line anchors |
| `docs/guia-revisao-arquitetura-e-apresentacao.md` | Modify | Update architecture, 2-tab walkthrough, FAQ, and line anchors |

### Data Model Changes
- `IntervalSchedulerProtocol.schedule(self, surgeries: Sequence[SurgeryRequest], shift_config: ShiftConfig | None = None) -> SchedulingResult`: drops `is_presorted` (and DP classes drop `presorted_start_indices`).
- `SimulationStep`: gains optional `last_release_minutes: int | None = None` so the frontend renders the green `last_release` marker reliably even when `variables` holds formatted `"HH:MM (min)"` strings.
- `SimulationTrace`: drops `is_presorted: bool` and gains `complexity_summary: dict[str, object]` serialized into `POST /api/trace` responses (`algorithm_name`, `time_complexity`, `space_complexity`, `sorting_key_formula`, `decision_rule_formula`, `input_n`, `feasible_n`, `phases`).
- `ScenarioPreset` catalog IDs change from `SC-01..SC-05b` (8 items) to `CASE-01..CASE-04` (4 items).

## Acceptance Criteria

- [ ] **Given** `src/schedulers/` and `src/domain/` **When** inspecting public exports and scheduler signatures **Then** `NaiveReductionScheduler`, `preprocess_naive_static_reduction`, `is_presorted`, `presorted_start_indices`, and `src/benchmark/` do not exist, and all 4 primary schedulers (`ClassicGreedyScheduler`, `ClassicDPScheduler`, `AdaptedGreedyScheduler`, `AdaptedDPScheduler`) implement the simplified `IntervalSchedulerProtocol.schedule(surgeries, shift_config)`.
- [ ] **Given** `GET /api/scenarios` **When** requested from `src/ui/server.py` **Then** it returns HTTP 200 with exactly 4 scenarios (`CASE-01`, `CASE-02`, `CASE-03`, `CASE-04`), where `CASE-02` reproduces the classic-vs-adapted counterexample (`Adapted = {S2, S3}` valid vs. `Classic = {S1, S3}` physical conflict) and `CASE-03` demonstrates shift-window `[12:00, 13:00]` filtering and $r_1 = B$ jump.
- [ ] **Given** `POST /api/trace` for any of the 4 algorithms **When** tracing `CASE-01`..`CASE-04` or a valid custom surgery list **Then** `SimulationTrace` matches `schedule()` 100%, exposes `complexity_summary` (`time_complexity == "O(n log n)"`, `space_complexity == "O(n)"`, formulas, and phase operation counts), formats timestamps in `variables` as `"HH:MM (min)"`, and preserves numeric `last_release_minutes` when applicable.
- [ ] **Given** `POST /api/compare` **When** comparing all 4 algorithms **Then** it returns 4 entries (`classic_greedy`, `classic_dp`, `adapted_greedy`, `adapted_dp`) with conflict auditing, and the Tab 2 frontend renders all 4 mini-Gantts on an identical shared `[minT, maxT]` horizontal scale.
- [ ] **Given** `POST /api/generate` or `POST /api/benchmark` **When** requested from `src/ui/server.py` **Then** the server returns HTTP 404 (routes removed), while valid `/api/trace` and `/api/compare` requests enforce `MAX_TRACE_INPUT_SIZE = 200`, `MAX_COMPARE_INPUT_SIZE = 500`, and `MAX_REQUEST_BODY_BYTES = 262_144`.
- [ ] **Given** the Web UI (`src/ui/static/index.html`, `app.js`) **When** inspecting structure and behavior **Then** only 2 tabs (`1. Simulador Passo a Passo`, `2. Comparativo dos 4 Algoritmos`) exist, `#complexity-summary-card` renders safely without `innerHTML`, and there is no random generator or `#presorted-checkbox`.
- [ ] **Given** the full automated test suite **When** running `pytest -v` **Then** all tests (including 180-instance oracle cross-validation and `test_documentation_integrity.py`) pass cleanly.

## Defensive Security & Validation Considerations

### Input Validation
- Domain constructors (`SurgeryRequest`, `ShiftWindow`, `ShiftConfig`) continue validating integer bounds (`is_strict_int`), `0 <= s_i < f_i`, `CLEAN => c_i == 0`, `CONTAMINATED => c_i > 0`, and `0 <= A < B <= H`, raising `InvalidSchedulingInputError`.
- HTTP JSON handlers in `src/ui/server.py` strictly validate `algorithm` against the 4 allowed keys (`classic_greedy`, `classic_dp`, `adapted_greedy`, `adapted_dp`), enforce `MAX_REQUEST_BODY_BYTES = 262_144`, `MAX_TRACE_INPUT_SIZE = 200`, and `MAX_COMPARE_INPUT_SIZE = 500`, and return HTTP 400 on malformed payloads.

### Secret Isolation
- N/A — the application operates completely offline in-memory with zero credentials, API keys, or environment secrets. `test_documentation_integrity.py` explicitly verifies that no secret patterns or host paths appear in docs.

### Authorization & Authentication Impact
- N/A — this change does not introduce authentication or multi-user access control; the local server binds strictly to loopback `127.0.0.1` by default.

### Other Security Risks
- **XSS Prevention**: All dynamic DOM rendering in `src/ui/static/app.js` (including the new `#complexity-summary-card`) MUST use `document.createElement`, `textContent`, and `createElementNS` — never `innerHTML` (enforced by automated test).
- **Path Traversal & DoS**: `src/ui/server.py` retains `STATIC_DIR` canonical path containment and bounded TCP draining before returning HTTP 413 on oversized bodies.

## Testing Strategy & Shift-Left Plan

### Happy Path Tests
| Test ID | Scenario | Test Type | Expected Result |
|---------|----------|-----------|-----------------|
| TP-01 | Domain validation, `is_actively_feasible`, and `compute_effective_release_time` across `CASE-01`..`CASE-04` | Unit | Exact `r_i` values (including $B$ jump in `CASE-03`) and accurate discarded counts |
| TP-02 | `ClassicGreedyScheduler` and `ClassicDPScheduler` on `CASE-01` and ties | Unit | Both return 3 optimal surgeries on `CASE-01`; `ClassicDP` matches `ClassicGreedy` across random clean inputs |
| TP-03 | `AdaptedGreedyScheduler` and `AdaptedDPScheduler` on `CASE-01`..`CASE-04` | Unit | Exact optimum on all 4 scenarios (`CASE-02` selects `{S2, S3}`, `CASE-03` selects `{S1, S4, S5}`) |
| TP-04 | Randomized 180-instance oracle cross-validation (`n <= 16`) | Property / Unit | `AdaptedGreedy == AdaptedDP == BruteForceOracle` with zero physical conflicts |
| TP-05 | Tracer parity & `complexity_summary` for all 4 algorithms on `CASE-01`..`CASE-04` | Integration | `trace.final_result` matches `schedule()`, `complexity_summary` contains formulas & operation counts, timestamps formatted as `HH:MM (min)` |
| TP-06 | HTTP server `GET /api/scenarios`, `POST /api/trace`, `POST /api/compare`, and CLI `--scenario` | Integration | 4 presets returned, 4-way Arena detects classic conflicts, HTML/JS passes XSS/no-`innerHTML` checks |

### Edge Case & Failure Mode Tests
| Test ID | Scenario | Test Type | Expected Result |
|---------|----------|-----------|-----------------|
| TE-01 | Empty input, single surgery, all-infeasible input, and end-of-shift passive sterilization boundary | Unit | Correct empty/singleton schedules and accurate `discarded_infeasible_count` |
| TE-02 | Malformed domain inputs (`s_i >= f_i`, `CLEAN` with `c_i > 0`, `B > H`) and Oracle `n > 20` | Unit | Raises `InvalidSchedulingInputError` |
| TE-03 | Removed routes (`POST /api/generate`, `POST /api/benchmark`) and unknown `algorithm` key | Integration | HTTP 404 on removed routes; HTTP 400 on unknown algorithm |
| TE-04 | Oversized HTTP body (> 262,144 bytes), trace > 200 items, path traversal `/static/../server.py` | Security / Integration | HTTP 413, HTTP 400, and HTTP 403/404 respectively |
| TE-05 | Documentation link & `#Lxx-Lyy` anchor validation on `README.md` and `docs/guia-revisao-arquitetura-e-apresentacao.md` | Integrity | Zero broken links, valid line slices containing named symbols, zero host paths/secrets |

### Test Commands
- **Run tests:** `pytest -v`
- **Verification check:** `pytest -v` (verifying full deterministic pass under 5 seconds)

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Formatting `variables` as `"HH:MM (min)"` breaks the Gantt green `last_release` line in `app.js` | Med | Med | Add explicit numeric `last_release_minutes: int | None` on `SimulationStep` and read it in `app.js` |
| Removing `SC-01..SC-05b` breaks doc integrity assertions or line-number anchors | High | Med | Update `tests/test_documentation_integrity.py`, `README.md`, and `docs/guia-revisao-arquitetura-e-apresentacao.md` together and verify with `pytest -v` |
| Deleting `MAX_GENERATE_SIZE` leaves `_handle_compare_request` referencing an undefined constant | Med | High | Introduce explicit `MAX_COMPARE_INPUT_SIZE = 500` in `src/ui/server.py` |

## Specification Changes & Delta Stubs

### `specs/problem-definition-and-mathematical-model-delta.md`
- **Target Canonical Spec:** `openspec/specs/problem-definition-and-mathematical-model.md`
- **Summary of Updates:** Streamline mathematical model and complexity comparison around the 4 core $\mathcal{O}(n \log n)$ algorithms (`ClassicGreedy`, `ClassicDP`, `AdaptedGreedy`, `AdaptedDP`), retaining the `S1/S2/S3` counterexample conceptually (`CASE-02`) while removing naive static reduction comparator and $\mathcal{O}(n)$ pre-sorted index permutation requirements.

### `specs/algorithms-and-domain-architecture-delta.md`
- **Target Canonical Spec:** `openspec/specs/algorithms-and-domain-architecture.md`
- **Summary of Updates:** Remove `NaiveReductionScheduler`, naive preprocessing helpers, `is_presorted` / `presorted_start_indices` two-pointer branches, and `src/benchmark/`; document simplified `IntervalSchedulerProtocol`, `complexity_summary` & `last_release_minutes` in `src/ui/tracer.py`, and streamlined `src/main.py` / `src/ui/server.py`.

### `specs/testing-benchmark-and-visual-interface-delta.md`
- **Target Canonical Spec:** `openspec/specs/testing-benchmark-and-visual-interface.md`
- **Summary of Updates:** Replace `SC-01`..`SC-05b` with `CASE-01`..`CASE-04`, remove empirical scaling benchmark specification (`src/benchmark/` and Tab 3), and specify the 2-tab Web UI (with `#complexity-summary-card`, `HH:MM (min)` variables, shared-axis mini-Gantts, and 3 HTTP API endpoints).

### `specs/sdd-stack-contract-delta.md`
- **Target Canonical Spec:** `openspec/specs/sdd-stack-contract.md`
- **Summary of Updates:** Remove `benchmarking` / `random` / `statistics` references and remove `POST /api/generate` and `POST /api/benchmark` from the declared API contract during consolidation/archival.

## References

- [sdd-stack-contract.md](../../specs/sdd-stack-contract.md)
- [problem-definition-and-mathematical-model.md](../../specs/problem-definition-and-mathematical-model.md)
- [algorithms-and-domain-architecture.md](../../specs/algorithms-and-domain-architecture.md)
- [testing-benchmark-and-visual-interface.md](../../specs/testing-benchmark-and-visual-interface.md)
