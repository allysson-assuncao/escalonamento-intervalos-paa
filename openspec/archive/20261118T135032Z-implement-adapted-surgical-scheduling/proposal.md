# Proposal: Implement Adapted Surgical Scheduling

> **Change ID:** `implement-adapted-surgical-scheduling`
> **Status:** approved
> **Author:** `@allysson-assuncao`
> **Created:** 2026-11-15
> **Last Updated:** 2026-11-15

---

## Summary

This change implements the authorial Operating Room scheduling core of `escalonamento-intervalos-paa` on top of the classic baseline established in Change #2: active feasibility preprocessing against closing horizon $H$ and shift-change window $[A, B]$, closed-form Effective Release Time ($r_i$) computation for `CLEAN` vs. `CONTAMINATED` surgeries, `AdaptedGreedyScheduler`, `AdaptedDPScheduler`, the comparative `NaiveReductionScheduler` ($f'_i = f_i + c_i$), the bounded `BruteForceOracleScheduler` ($n \le 20$), an empirical scaling benchmark runner (`src/benchmark/runner.py`), and comprehensive `pytest` verification suites covering scenarios `SC-01` through `SC-05` and randomized oracle cross-validation.

## Motivation

The classical `ClassicGreedyScheduler` and `ClassicDPScheduler` operate exclusively on $[s_i, f_i]$ and therefore produce physically invalid or suboptimal schedules when surgeries require post-operative automated ozone/UV sterilization ($c_i > 0$) and medical staff are constrained by a shift closing horizon $H$ and a shift-change window $[A, B]$. Similarly, naive static reduction ($f'_i = f_i + c_i$) falsely discards valid end-of-shift surgeries whose automated sterilization completes after $H$ (`SC-02` and `SC-03`). Delivering the adapted algorithms, naive comparator, exact brute-force oracle, and scaling benchmark proves both 100% exact optimality and asymptotic $\mathcal{O}(n \log n)$ / $\mathcal{O}(n)$ parity before building the visual demonstration interface in Change #4.

## Scope

### In Scope
- **Phase 1 — Domain Preprocessing, Naive Comparator & Scenarios (`SC-02`..`SC-05`)**:
  - Implement `src/domain/preprocessing.py` with `is_actively_feasible`, `compute_effective_release_time`, `preprocess_feasible_surgeries`, and `preprocess_naive_static_reduction`.
  - Refactor shared input validation (`validate_scheduler_inputs`) into the domain layer (re-exported in `src/schedulers/protocol.py`) to avoid circular dependencies between `src/domain` and `src/schedulers`.
  - Add `order_processed_surgeries` and a shared unweighted DP solver helper in `src/schedulers/protocol.py` (reused by `ClassicDPScheduler` and `AdaptedDPScheduler` to eliminate duplicated DP logic).
  - Implement `NaiveReductionScheduler` (`src/schedulers/naive_reduction.py`) conforming to `IntervalSchedulerProtocol`.
  - Expand `tests/fixtures/scenarios.py` with deterministic scenarios `SC-02`, `SC-03`, `SC-04` (`SC-04a`, `SC-04b`, `SC-04c`), and `SC-05`, and create `tests/test_preprocessing.py`.
- **Phase 2 — Authorial Adapted Schedulers**:
  - Implement `AdaptedGreedyScheduler` (`src/schedulers/adapted_greedy.py`) sorting feasible `ProcessedSurgery` items by `(effective_release_time, finish_time, start_time)` in $\mathcal{O}(n \log n)$ (or validating in $\mathcal{O}(n)$ when `is_presorted=True`) and selecting compatible intervals (`start_time >= last_release`).
  - Implement `AdaptedDPScheduler` (`src/schedulers/adapted_dp.py`) supporting `is_presorted=True` and optional `presorted_start_indices` ($\mathcal{O}(n)$ two-pointer predecessors) as well as general-case `bisect.bisect_right` predecessors ($\mathcal{O}(n \log n)$), DP table filling, and iterative backtracking reconstruction.
  - Define explicit `shift_config=None` behavior for adapted schedulers: horizon $H$ and shift-window $[A, B]$ filtering are skipped (`discarded_infeasible_count = 0`), while biological sterilization ($r_i = f_i + c_i$) remains enforced—ensuring full equivalence with Classic Greedy/DP on `CLEAN` datasets such as `SC-01`.
  - Create `tests/test_adapted_schedulers.py` covering `SC-01`..`SC-05`, `is_presorted=True`, and direct comparison showing `ClassicGreedyScheduler` and `NaiveReductionScheduler` failing `SC-02` while `AdaptedGreedyScheduler` and `AdaptedDPScheduler` achieve `total_selected == 2`.
- **Phase 3 — Exact Brute-Force Oracle & Empirical Benchmark Runner**:
  - Implement `BruteForceOracleScheduler` (`src/schedulers/brute_force_oracle.py`) with hard guard `MAX_ORACLE_INPUT_SIZE = 20` raising `InvalidSchedulingInputError` for $n > 20$.
  - Implement `src/benchmark/runner.py` (`BenchmarkPoint`, `generate_synthetic_surgeries`, `run_scaling_benchmark`, `format_benchmark_table`) measuring runtime (`perf_counter_ns`), cardinality, and normalized ratios $T(n) / (n \log_2 n)$ and $T(n) / n$.
  - Create `tests/test_oracle_and_comparison.py` with 150+ seeded randomized cross-validation instances ($n \in [0, 16]$) verifying `AdaptedGreedy.total_selected == AdaptedDP.total_selected == BruteForceOracle.total_selected`, constraint invariants on every selected schedule, oracle bound guard ($n = 21$), and benchmark runner smoke checks.
- **Phase 4 — Final Verification & OpenSpec Consolidation**:
  - Update `src/domain/__init__.py`, `src/schedulers/__init__.py`, and `src/benchmark/__init__.py` exports.
  - Run full `pytest -v` and security/language checks (`en-US` identifiers, `pt-BR` docstrings/comments, zero hardcoded secrets, zero third-party runtime dependencies in `src/`).

### Out of Scope
- Visual / graphical UI framework selection, implementation, and `src/main.py` entrypoint (deferred to Change #4).
- Writing full project execution guides in `README.md` (deferred to Change #4).
- Supporting multiple simultaneous operating rooms or multiple shift-change windows $[a_k, b_k]$.

## Proposed Solution

### Approach
The implementation strictly respects SOLID principles and Clean Architecture:
1. **Preprocessing (`src/domain/preprocessing.py`)**: Isolates active-feasibility validation ($f_i \le H$; $f_i \le A$ or $s_i \ge B$) and closed-form Effective Release Time computation ($r_i = B$ if $f_i \le A$ and $A < f_i + c_i < B$, else $r_i = f_i + c_i$) from scheduling algorithms. `validate_scheduler_inputs` is hosted in the domain module and re-exported in `src/schedulers/protocol.py` so `domain` never depends on `schedulers`.
2. **Unified Strategy & Shared DP Kernel (`src/schedulers/protocol.py`)**: All five schedulers (`ClassicGreedyScheduler`, `ClassicDPScheduler`, `NaiveReductionScheduler`, `AdaptedGreedyScheduler`, `AdaptedDPScheduler`, plus `BruteForceOracleScheduler`) conform to `IntervalSchedulerProtocol`. Common ordering (`order_processed_surgeries`), two-pointer validation (`_validate_presorted_start_indices`), predecessor resolution, and iterative DP table/backtracking live in parameterized helper functions shared between `ClassicDPScheduler` and `AdaptedDPScheduler`, guaranteeing zero logic duplication while keeping each scheduler class concise and directly comparable.
3. **Empirical Verification & Complexity Guardrails (`src/schedulers/brute_force_oracle.py`, `src/benchmark/runner.py`)**: The exact branch-and-bound oracle verifies mathematical optimality on small randomized hospital workloads ($n \le 20$, strictly guarding against $n > 20$), while the benchmark runner isolates `schedule()` execution from data generation to quantify $\Theta(n \log n)$ and $\Theta(n)$ behavior across all four production algorithms plus `NaiveReductionScheduler`.

### Impacted Files
| File | Change Type | Notes |
|------|-------------|-------|
| `src/domain/preprocessing.py` | Create | Active feasibility filter, $r_i$ formula, `preprocess_feasible_surgeries`, `preprocess_naive_static_reduction`, `validate_scheduler_inputs` |
| `src/domain/__init__.py` | Modify | Export preprocessing functions |
| `src/schedulers/protocol.py` | Modify | Re-export `validate_scheduler_inputs`; add `order_processed_surgeries` and parameterized DP solver kernel |
| `src/schedulers/classic_dp.py` | Modify | Delegate shared DP kernel to `protocol.py` without changing behavior or public API |
| `src/schedulers/naive_reduction.py` | Create | Implement `NaiveReductionScheduler` ($f'_i = f_i + c_i$) |
| `src/schedulers/adapted_greedy.py` | Create | Implement `AdaptedGreedyScheduler` ($\mathcal{O}(n \log n)$ / $\mathcal{O}(n)$ pre-sorted) |
| `src/schedulers/adapted_dp.py` | Create | Implement `AdaptedDPScheduler` ($\mathcal{O}(n \log n)$ / $\mathcal{O}(n)$ pre-sorted + backtracking) |
| `src/schedulers/brute_force_oracle.py` | Create | Implement `BruteForceOracleScheduler` with $n \le 20$ guard |
| `src/schedulers/__init__.py` | Modify | Export `NaiveReductionScheduler`, `AdaptedGreedyScheduler`, `AdaptedDPScheduler`, `BruteForceOracleScheduler` |
| `src/benchmark/__init__.py` | Create | Export `BenchmarkPoint`, `generate_synthetic_surgeries`, `run_scaling_benchmark`, `format_benchmark_table` |
| `src/benchmark/runner.py` | Create | Implement synthetic instance generator and empirical complexity benchmark runner |
| `tests/fixtures/scenarios.py` | Modify | Add deterministic `SC-02`, `SC-03`, `SC-04a/b/c`, and `SC-05` fixtures |
| `tests/test_preprocessing.py` | Create | Unit tests for active feasibility, $r_i$ boundary math, and naive static reduction |
| `tests/test_adapted_schedulers.py` | Create | Unit & comparative tests across `SC-01..SC-05`, pre-sorted mode, and `SC-02` counterexample proof |
| `tests/test_oracle_and_comparison.py` | Create | Oracle $n > 20$ guard tests, 150+ randomized equivalence tests, and benchmark runner tests |

### Data Model Changes (if applicable)
No breaking changes to existing domain entities in `src/domain/models.py`. Introduces `BenchmarkPoint` frozen dataclass in `src/benchmark/runner.py` for empirical runtime and normalized asymptotic ratio reporting.

## Acceptance Criteria

- [x] **Given** `SC-02` (the 3-surgery hospital counterexample with $H = 1080$), **When** scheduled by `AdaptedGreedyScheduler`, `AdaptedDPScheduler`, `BruteForceOracleScheduler`, `NaiveReductionScheduler`, and `ClassicGreedyScheduler`, **Then** `AdaptedGreedyScheduler`, `AdaptedDPScheduler`, and `BruteForceOracleScheduler` all select `{"S2", "S3"}` (`total_selected == 2`), whereas `NaiveReductionScheduler` discards `"S3"` and selects at most `1` surgery and `ClassicGreedyScheduler` picks `"S1"` first (leaving room blocked until `16:00`).
- [x] **Given** `SC-03` (contaminated surgery ending at `17:50` with $30$ min sterilization under $H = 18:00$, alongside an infeasible surgery ending at `18:01`), **When** preprocessed and scheduled by adapted solvers, **Then** the `17:50` surgery is accepted (`effective_release_time == 18:20`) and the `18:01` surgery is counted in `discarded_infeasible_count`.
- [x] **Given** `SC-04a`, `SC-04b`, and `SC-04c` with `shift_window = [12:00, 13:00]`, **When** preprocessed and scheduled, **Then** active overlaps with `[12:00, 13:00)` are rejected (`SC-04a`), boundary surgeries ending at `12:00` or starting at `13:00` are accepted, sterilization ending at `12:15` is clamped to $r_i = 13:00$ (`SC-04b`), and sterilization ending at `13:15` preserves $r_i = 13:15$ (`SC-04c`).
- [x] **Given** `shift_config=None` and mixed `CLEAN`/`CONTAMINATED` inputs (or `SC-01` all-`CLEAN` inputs), **When** scheduled by `AdaptedGreedyScheduler` and `AdaptedDPScheduler`, **Then** no horizon or shift-window filtering occurs (`discarded_infeasible_count == 0`), sterilization cooldown $r_i = f_i + c_i$ is enforced, and `SC-01` results match `ClassicGreedyScheduler` and `ClassicDPScheduler` (`total_selected == 5`).
- [x] **Given** 150+ deterministic seeded randomized hospital instances with $n \in [0, 16]$ (varying `CLEAN`/`CONTAMINATED` ratios, $c_i$, $H$, and $[A, B]$), **When** evaluated by `AdaptedGreedyScheduler`, `AdaptedDPScheduler`, and `BruteForceOracleScheduler`, **Then** `AdaptedGreedy.total_selected == AdaptedDP.total_selected == BruteForceOracle.total_selected` holds for 100% of instances and every returned schedule satisfies active feasibility and $s_k \ge r_{k-1}$.
- [x] **Given** an input of size $n = 21$ passed to `BruteForceOracleScheduler`, **When** `schedule()` is invoked, **Then** it immediately raises `InvalidSchedulingInputError`.
- [x] **Given** pre-sorted feasible `SurgeryRequest` sequences (and valid `presorted_start_indices` for `AdaptedDPScheduler`), **When** `schedule(..., is_presorted=True)` is invoked, **Then** both adapted solvers validate ordering in $\mathcal{O}(n)$, match `is_presorted=False` cardinality, and raise `InvalidSchedulingInputError` on unsorted sequences or partial-feasibility mismatches with `presorted_start_indices`.

## Defensive Security & Validation Considerations

### Input Validation
- All preprocessing functions (`preprocess_feasible_surgeries`, `preprocess_naive_static_reduction`) and all schedulers enforce `validate_scheduler_inputs(surgeries, shift_config)`, rejecting `None`, non-sequences, `str`/`bytes`, invalid elements, and caller mutations.
- `AdaptedGreedyScheduler` and `AdaptedDPScheduler` validate non-decreasing `(effective_release_time, finish_time, start_time)` order in $\mathcal{O}(n')$ when `is_presorted=True`, and reject `presorted_start_indices` if `is_presorted=False` or if infeasible items were filtered out (preventing silent index misalignment).
- `generate_synthetic_surgeries` validates `n >= 0`, `0.0 <= contaminated_ratio <= 1.0`, and strict integer types; `run_scaling_benchmark` validates positive `repetitions` and non-negative sizes.

### Secret Isolation
- N/A — strictly offline algorithmic modules using only the Python 3.12+ Standard Library (`dataclasses`, `bisect`, `typing`, `enum`, `time`, `random`, `math`, `statistics`) with zero credentials, tokens, or external network connections.

### Authorization & Authentication Impact
- N/A — local in-memory optimization algorithms and benchmark harness with no endpoints, persistence layer, or authentication surface.

### Other Security Risks
- **Exponential CPU Exhaustion (DoS) in Exact Oracle**: `BruteForceOracleScheduler` enforces `MAX_ORACLE_INPUT_SIZE = 20` before any preprocessing or search, raising `InvalidSchedulingInputError` immediately if `len(surgeries) > 20`.

## Testing Strategy & Shift-Left Plan

### Happy Path Tests
| Test ID | Scenario | Test Type | Expected Result |
|---------|----------|-----------|-----------------|
| TP-01 | `is_actively_feasible` and `compute_effective_release_time` across clean, contaminated, horizon, and shift-window cases | Unit | Exact boolean feasibility and closed-form $r_i$ values |
| TP-02 | `SC-01` backward compatibility (`shift_config=None`) across `AdaptedGreedyScheduler` and `AdaptedDPScheduler` | Comparative | Matches `ClassicGreedyScheduler` / `ClassicDPScheduler` (`total_selected == 5`) |
| TP-03 | `SC-02` 3-surgery non-reducibility counterexample across all schedulers | Comparative | Adapted Greedy/DP/Oracle return `{"S2", "S3"}` (`2`); Naive Reduction discards `"S3"` (`1`); Classic Greedy picks `"S1"` first |
| TP-04 | `SC-03` end-of-shift passive sterilization (`17:20–17:50 + 30m`, $H=18:00$) and `SC-04b`/`SC-04c` shift-break absorption/overflow | Unit | `S_end` scheduled with $r_i = 18:20$; `SC-04b` clamped to `13:00`; `SC-04c` yields `13:15` |
| TP-05 | `is_presorted=True` on `AdaptedGreedyScheduler` and `AdaptedDPScheduler` (monotonic start and `presorted_start_indices`) | Unit / Comparative | Matches `is_presorted=False` optimal schedule without re-sorting |
| TP-06 | 150+ seeded randomized instances ($n \in [0, 16]$) cross-validating `AdaptedGreedy == AdaptedDP == BruteForceOracle` | Property / Oracle | 100% cardinality match and physical schedule validity |
| TP-07 | Benchmark runner `run_scaling_benchmark` and `format_benchmark_table` across small scaling sizes (e.g., `n=(50, 100, 200)`) | Integration / Smoke | Returns valid `BenchmarkPoint` records with positive timing and finite normalized ratios |

### Edge Case & Failure Mode Tests
| Test ID | Scenario | Test Type | Expected Result |
|---------|----------|-----------|-----------------|
| TE-01 | `SC-04a` active overlap with `[12:00, 13:00)` vs. boundary touching (`11:00–12:00`, `13:00–14:00`) | Unit | Overlapping discarded; boundary-touching accepted |
| TE-02 | `SC-05` all surgeries infeasible, empty list `[]`, single valid surgery, and ties on identical $r_i$ with distinct $f_i$ | Unit | Accurate `discarded_infeasible_count`, empty/1 results, optimal tie resolution |
| TE-03 | Exact sterilization boundary landing right at $e_i = A$ or $e_i = B$ | Unit | $e_i = A \implies r_i = A$; $e_i = B \implies r_i = B$ |
| TE-04 | `BruteForceOracleScheduler` invoked with `n = 21` surgeries | Unit / Security | Immediately raises `InvalidSchedulingInputError` |
| TE-05 | Unsorted input passed with `is_presorted=True`, or `presorted_start_indices` when feasible filtering drops items | Unit | Raises `InvalidSchedulingInputError` |
| TE-06 | Caller list non-mutation and `None`/invalid parameters in preprocessing, adapted schedulers, oracle, and benchmark generator | Unit | Caller sequence untouched; invalid inputs raise `InvalidSchedulingInputError` / `ValueError` |

### Test Commands
- **Run full suite:** `./.venv/bin/pytest -v`
- **Secret & third-party import check:** `grep -rnE "password|secret|token|api_key" src/ tests/`

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Circular imports between `src/domain/preprocessing.py` and `src/schedulers/protocol.py` | Med | High | Move `validate_scheduler_inputs` to `src/domain/preprocessing.py` (or `src/domain/models.py`) and re-export it from `src/schedulers/protocol.py` so `domain` never imports `schedulers` |
| Subtle index mismatch in `AdaptedDPScheduler` when `is_presorted=True` with `presorted_start_indices` and infeasible items filtered out | Med | High | Explicitly reject `presorted_start_indices` when `discarded_infeasible_count > 0` and enforce permutation validation on feasible length $n'$ |
| Slow randomized test suite if brute-force oracle runs on too many large $n$ instances | Low | Med | Bound randomized property tests to $n \in [0, 16]$ with branch-and-bound pruning, keeping total `pytest -v` runtime under 5 seconds |

## Specification Changes & Delta Stubs

### `specs/algorithms-and-domain-architecture-delta.md`
- **Target Canonical Spec:** `openspec/specs/algorithms-and-domain-architecture.md`
- **Summary of Updates:** Updates Section 1.2/3/4/5 to document `validate_scheduler_inputs` placement in the domain layer, `NaiveReductionScheduler` specification, `shift_config=None` behavior on adapted solvers, shared DP kernel extraction in `src/schedulers/protocol.py`, `BruteForceOracleScheduler` contract, and `src/benchmark/runner.py` API.

### `specs/testing-benchmark-and-visual-interface-delta.md`
- **Target Canonical Spec:** `openspec/specs/testing-benchmark-and-visual-interface.md`
- **Summary of Updates:** Updates Sections 1–3 to record concrete `SC-02`..`SC-05` fixture names, `test_preprocessing.py`, `test_adapted_schedulers.py`, `test_oracle_and_comparison.py`, and exact `BenchmarkPoint` / `run_scaling_benchmark` contracts.

## References

- `openspec/specs/sdd-stack-contract.md`
- `openspec/specs/problem-definition-and-mathematical-model.md`
- `openspec/specs/algorithms-and-domain-architecture.md`
- `openspec/specs/testing-benchmark-and-visual-interface.md`
