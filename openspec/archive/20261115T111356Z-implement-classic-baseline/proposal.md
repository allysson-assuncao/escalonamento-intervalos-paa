# Proposal: Implement Classic Baseline

> **Change ID:** `implement-classic-baseline`
> **Status:** approved
> **Author:** `@allysson-assuncao`
> **Created:** 2026-11-15
> **Last Updated:** 2026-11-15

---

## Summary

This change establishes the initial Python 3.12+ project scaffold (`pyproject.toml`, `.gitignore`, `src/`, `tests/`), immutable domain entities (`src/domain/models.py`, `src/domain/exceptions.py`), the shared `IntervalSchedulerProtocol` strategy contract (`src/schedulers/protocol.py`), and the two consolidated textbook baseline algorithms—`ClassicGreedyScheduler` and `ClassicDPScheduler`—operating purely on surgical intervals $[s_i, f_i]$ in $\mathcal{O}(n \log n)$ general-case ($\mathcal{O}(n)$ pre-sorted) time, backed by a shift-left `pytest` verification suite.

## Motivation

Before introducing the authorial operating room constraints (biological contamination sterilization cooldowns $c_i$, closing horizon $H$, and shift-change window $[A, B]$), the project requires a clean, tested, and verified implementation of the classical Interval Scheduling algorithms (Earliest Finish Time Greedy and Unweighted Interval Scheduling Dynamic Programming). Keeping these pure textbook implementations side by side in the repository through the end of the project allows direct empirical and structural comparison of code clarity, runtime curves, and scheduling decisions against the adapted algorithms to be implemented in Change #3.

## Scope

### In Scope
- Initialize Python 3.12+ package configuration (`pyproject.toml` configured for `pytest` and `src/` layout) and standard Python `.gitignore`.
- Implement domain exceptions (`InvalidSchedulingInputError(ValueError)`) and immutable domain dataclasses (`SurgeryType`, `ShiftWindow`, `ShiftConfig`, `SurgeryRequest`, `ProcessedSurgery`, `SchedulingResult`) with forward-compatible defaults (`surgery_type=SurgeryType.CLEAN`, `sterilization_duration=0`) so classic callers only need `(surgery_id, start_time, finish_time)`.
- Implement the unified Dependency-Inversion contract `IntervalSchedulerProtocol` in `src/schedulers/protocol.py`.
- Implement `ClassicGreedyScheduler` (`src/schedulers/classic_greedy.py`):
  - Operates in Pure Classic Textbook Mode on active intervals $[s_i, f_i]$ (ignoring `sterilization_duration` and `shift_config`).
  - Sorts by $(f_i, s_i)$ in $\mathcal{O}(n \log n)$ (or validates non-decreasing $(f_i, s_i)$ order in $\mathcal{O}(n)$ when `is_presorted=True`).
  - Scans linearly in $\mathcal{O}(n)$ selecting surgeries with $s_i \ge f_{\text{last}}$ and wraps each selected surgery in `ProcessedSurgery(request=s, effective_release_time=s.finish_time)`.
- Implement `ClassicDPScheduler` (`src/schedulers/classic_dp.py`):
  - Operates in Pure Classic Textbook Mode on active intervals $[s_i, f_i]$ (ignoring `sterilization_duration` and `shift_config`).
  - Sorts by $(f_i, s_i)$ in $\mathcal{O}(n \log n)$ (or validates order in $\mathcal{O}(n)$ when `is_presorted=True`).
  - Computes predecessor indices $p(i) = \max\{j < i \mid f_j \le s_i\}$ via `bisect.bisect_right` in $\mathcal{O}(n \log n)$ in the general case, or via $\mathcal{O}(n)$ monotonic two-pointer scan when `is_presorted=True` (using an optional `presorted_start_indices` mapping or linear monotonicity check on $s_i$, falling back safely to `bisect_right` if start times are non-monotonic and no start-order index mapping is provided).
  - Evaluates $DP[i] = \max(DP[i - 1], 1 + DP[p(i)])$ and reconstructs the chronologically ordered optimal subset via backtracking in $\mathcal{O}(n)$.
- Measure internal algorithm runtime in nanoseconds via `time.perf_counter_ns()`.
- Build shift-left `pytest` tests (`tests/fixtures/scenarios.py`, `tests/test_domain_models.py`, `tests/test_classic_schedulers.py`) covering `SC-01`, tie-breaking, edge cases, pre-sorted $\mathcal{O}(n)$ mode, and constructor validation errors.

### Out of Scope
- Active feasibility filtering against closing horizon $H$ and shift-change window $[A, B]$ (`src/domain/preprocessing.py` — deferred to Change #3).
- Effective Release Time ($r_i$) with sterilization cooldown $c_i$ and Naive Static Reduction ($f'_i = f_i + c_i$) comparative helper (deferred to Change #3).
- `AdaptedGreedyScheduler`, `AdaptedDPScheduler`, and `BruteForceOracleScheduler` (deferred to Change #3).
- Empirical scaling benchmark runner (`src/benchmark/runner.py`) and visual presentation interface (`src/ui/`, `README.md` execution guide — deferred to Change #3 / Change #4).

## Proposed Solution

### Approach
Following SOLID and Clean Code rules from `.agents/rules/AGENTS.md` and `openspec/specs/algorithms-and-domain-architecture.md`, domain invariants live exclusively inside `@dataclass(frozen=True)` `__post_init__` hooks in `src/domain/models.py`, preventing invalid states from propagating into any scheduler. Both classic solvers depend solely on Python 3.12+ Standard Library primitives (`dataclasses`, `bisect`, `typing`, `enum`, `time`), implement `IntervalSchedulerProtocol`, copy caller sequences safely without side-effect mutation, and use English identifiers (`en-US`) paired with Brazilian Portuguese (`pt-BR`) docstrings and inline comments.

### Impacted Files
| File | Change Type | Notes |
|------|-------------|-------|
| `.gitignore` | Create | Ignore Python bytecode, `.venv/`, `.pytest_cache/`, IDE artifacts |
| `pyproject.toml` | Create | Project metadata and `pytest` configuration (`pythonpath = ["."]`) |
| `src/__init__.py` | Create | Top-level package marker |
| `src/domain/__init__.py` | Create | Exports domain models and `InvalidSchedulingInputError` |
| `src/domain/exceptions.py` | Create | Defines `InvalidSchedulingInputError(ValueError)` |
| `src/domain/models.py` | Create | Immutable dataclasses (`SurgeryType`, `ShiftWindow`, `ShiftConfig`, `SurgeryRequest`, `ProcessedSurgery`, `SchedulingResult`) |
| `src/schedulers/__init__.py` | Create | Exports `IntervalSchedulerProtocol`, `ClassicGreedyScheduler`, `ClassicDPScheduler` |
| `src/schedulers/protocol.py` | Create | Defines `IntervalSchedulerProtocol` |
| `src/schedulers/classic_greedy.py` | Create | `ClassicGreedyScheduler` ($\mathcal{O}(n \log n)$ / $\mathcal{O}(n)$ pre-sorted) |
| `src/schedulers/classic_dp.py` | Create | `ClassicDPScheduler` ($\mathcal{O}(n \log n)$ / $\mathcal{O}(n)$ pre-sorted + backtracking) |
| `tests/__init__.py` | Create | Test package marker |
| `tests/fixtures/__init__.py` | Create | Fixtures package marker |
| `tests/fixtures/scenarios.py` | Create | Pre-configured `SC-01` classical dataset and boundary fixtures |
| `tests/test_domain_models.py` | Create | Unit tests for immutability and `InvalidSchedulingInputError` invariants |
| `tests/test_classic_schedulers.py` | Create | Unit & equivalence tests for `ClassicGreedyScheduler` vs. `ClassicDPScheduler` |

### Data Model Changes (if applicable)
Introduces the Python implementation of all canonical domain structures specified in `openspec/specs/algorithms-and-domain-architecture.md`: `SurgeryType`, `ShiftWindow`, `ShiftConfig`, `SurgeryRequest`, `ProcessedSurgery`, and `SchedulingResult`.

## Acceptance Criteria

- [x] **Given** valid or invalid arguments for `SurgeryRequest`, `ShiftWindow`, and `ShiftConfig`, **When** instantiated, **Then** valid instances are immutable (`FrozenInstanceError` on attribute assignment) and malformed inputs ($s_i \ge f_i$, negative timestamps, blank `surgery_id`, `CLEAN` with $c_i > 0$, `CONTAMINATED` with $c_i \le 0$, $A \ge B$, $B > H$) raise `InvalidSchedulingInputError`.
- [x] **Given** the pre-configured classical homogeneous dataset `SC-01` and edge-case interval sets (empty, single item, all overlapping, finish-time ties), **When** scheduled by `ClassicGreedyScheduler` and `ClassicDPScheduler`, **Then** both return chronologically ordered, pairwise non-overlapping subsets ($s_k \ge f_{k-1}$) with identical `total_selected`, `discarded_infeasible_count == 0`, and non-negative `elapsed_ns`.
- [x] **Given** an input sequence pre-sorted by $(f_i, s_i)$, **When** `schedule(surgeries, is_presorted=True)` is called on `ClassicGreedyScheduler` and `ClassicDPScheduler`, **Then** both skip re-sorting, validate order in $\mathcal{O}(n)$, compute the exact same optimal cardinality as `is_presorted=False`, and raise `InvalidSchedulingInputError` if an unsorted sequence is passed with `is_presorted=True`.
- [x] **Given** `SurgeryRequest` items containing `CONTAMINATED` type with $c_i > 0$ or a non-None `shift_config`, **When** passed to `ClassicGreedyScheduler` or `ClassicDPScheduler`, **Then** both pure textbook schedulers ignore `sterilization_duration` and `shift_config`, evaluating compatibility strictly on $[s_i, f_i]$ with `effective_release_time == finish_time`.

## Defensive Security & Validation Considerations

### Input Validation
- All numeric and string invariants are validated eagerly in `@dataclass(frozen=True).__post_init__`, raising `InvalidSchedulingInputError(ValueError)`.
- Schedulers explicitly validate that `surgeries` is not `None`, copy input sequences into internal lists without mutating caller data, and validate sort order in $\mathcal{O}(n)$ when `is_presorted=True`.
- When `ClassicDPScheduler` receives `presorted_start_indices`, its length and permutation bounds (`0..n-1`) are validated before indexing.

### Secret Isolation
- N/A — strictly offline algorithmic modules using only Python Standard Library with zero credentials, tokens, environment secrets, or external network I/O.

### Authorization & Authentication Impact
- N/A — this change implements in-memory scheduling domain models and textbook algorithms and does not expose network endpoints or modify authentication logic.

### Other Security Risks
- **Unbounded Memory / Recursion Stack**: Both `ClassicGreedyScheduler` and `ClassicDPScheduler` use iterative loops (`for` / `while`) instead of deep recursion, eliminating `RecursionError` stack-overflow risk on large inputs ($n \ge 10\,000$).

## Testing Strategy & Shift-Left Plan

### Happy Path Tests
| Test ID | Scenario | Test Type | Expected Result |
|---------|----------|-----------|-----------------|
| TP-01 | Construct valid `SurgeryRequest` (clean defaults & explicit contaminated), `ShiftWindow`, and `ShiftConfig` | Unit | Instances created cleanly; attributes immutable |
| TP-02 | Schedule `SC-01` classic homogeneous baseline via `ClassicGreedyScheduler` and `ClassicDPScheduler` | Unit / Comparative | Both return identical optimal cardinality and pairwise non-overlapping intervals |
| TP-03 | Schedule pre-sorted inputs with `is_presorted=True` (including monotonic start and `presorted_start_indices` two-pointer DP) | Unit / Comparative | Matches `is_presorted=False` cardinality without sorting |
| TP-04 | Verify Pure Classic Textbook Mode ignores `sterilization_duration` and `shift_config` | Unit | `effective_release_time == finish_time`; `discarded_infeasible_count == 0` |

### Edge Case & Failure Mode Tests
| Test ID | Scenario | Test Type | Expected Result |
|---------|----------|-----------|-----------------|
| TE-01 | Reject invalid `SurgeryRequest`, `ShiftWindow`, and `ShiftConfig` inputs ($s_i \ge f_i$, `CLEAN` + $c_i>0$, `CONTAMINATED` + $c_i=0$, $B > H$, blank ID) | Unit | Raises `InvalidSchedulingInputError` |
| TE-02 | Empty list `[]`, single surgery `[s1]`, and all-mutually-overlapping intervals | Unit | Returns 0, 1, and 1 selected surgery respectively |
| TE-03 | Adjacent touching boundaries ($s_j == f_i$) and identical finish-time ties | Unit | Touching intervals are compatible ($s_j \ge f_i$); ties yield identical optimal count |
| TE-04 | Unsorted input passed with `is_presorted=True` | Unit | Raises `InvalidSchedulingInputError` |
| TE-05 | Caller list immutability and `None` input guard | Unit | Caller list order unchanged; `None` raises `InvalidSchedulingInputError` |

### Test Commands
- **Run tests:** `pytest -v`

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Caller passes `is_presorted=True` on unsorted input or non-monotonic start times to two-pointer DP | Med | High | Validate $(f_i, s_i)$ order in $\mathcal{O}(n)$ when `is_presorted=True` and check start-time monotonicity (or require valid `presorted_start_indices`) before running the two-pointer scan, falling back safely to `bisect_right` otherwise |
| Divergence in `SurgeryRequest` signature between Change #2 and Change #3 | Low | Med | Define complete `SurgeryRequest` fields now with safe classic defaults (`CLEAN`, `0`) per `algorithms-and-domain-architecture.md` |

## Specification Changes & Delta Stubs

### `specs/algorithms-and-domain-architecture-delta.md`
- **Target Canonical Spec:** `openspec/specs/algorithms-and-domain-architecture.md`
- **Summary of Updates:** Clarifies that `ClassicGreedyScheduler` and `ClassicDPScheduler` implement Pure Classic Textbook Mode (ignoring `shift_config` and `sterilization_duration` with `effective_release_time = f_i`), defers Naive Static Reduction to Change #3, and specifies $\mathcal{O}(n)$ order validation and two-pointer safety guards for `is_presorted=True`.

## References

- `openspec/specs/sdd-stack-contract.md`
- `openspec/specs/problem-definition-and-mathematical-model.md`
- `openspec/specs/algorithms-and-domain-architecture.md`
- `openspec/specs/testing-benchmark-and-visual-interface.md`
