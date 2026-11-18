# Tasks: Implement Adapted Surgical Scheduling

> **Change ID:** `implement-adapted-surgical-scheduling`
> **Linked Proposal:** [proposal.md](./proposal.md)
> **Status:** completed
>
> All tasks must be `[x]` before this change can be archived via `sdd-spec-archive`.

---

## Implementation Tasks

### Phase 1 — Domain Preprocessing, Naive Reduction & Counterexample Fixtures
- [x] Move/place `validate_scheduler_inputs` in `src/domain/preprocessing.py` (re-exporting in `src/schedulers/protocol.py`) to maintain clean acyclic `domain -> schedulers` layering
- [x] Implement `is_actively_feasible`, `compute_effective_release_time`, `preprocess_feasible_surgeries`, and `preprocess_naive_static_reduction` in `src/domain/preprocessing.py` and export them in `src/domain/__init__.py`
- [x] Add `order_processed_surgeries` and parameterized unweighted interval DP kernel (`solve_interval_dp`) to `src/schedulers/protocol.py` and refactor `src/schedulers/classic_dp.py` to reuse it without behavior changes
- [x] Implement `NaiveReductionScheduler` in `src/schedulers/naive_reduction.py`
- [x] Expand `tests/fixtures/scenarios.py` with `SC-02`, `SC-03`, `SC-04a/b/c`, and `SC-05` fixtures and write `tests/test_preprocessing.py`

### Phase 2 — Authorial Adapted Schedulers (Greedy & DP)
- [x] Implement `AdaptedGreedyScheduler` in `src/schedulers/adapted_greedy.py` ($\mathcal{O}(n \log n)$ general, $\mathcal{O}(n)$ pre-sorted, supporting `shift_config=None` and `[A, B]`/`H`)
- [x] Implement `AdaptedDPScheduler` in `src/schedulers/adapted_dp.py` ($\mathcal{O}(n \log n)$ via `bisect_right`, $\mathcal{O}(n)$ two-pointer pre-sorted mode with `presorted_start_indices`, iterative DP + backtracking)
- [x] Write `tests/test_adapted_schedulers.py` covering `SC-01`..`SC-05`, pre-sorted mode, `shift_config=None`, and comparative proof against `ClassicGreedyScheduler` and `NaiveReductionScheduler`

### Phase 3 — Exact Brute-Force Oracle & Empirical Benchmark Runner
- [x] Implement `BruteForceOracleScheduler` (`MAX_ORACLE_INPUT_SIZE = 20`) in `src/schedulers/brute_force_oracle.py` and update exports in `src/schedulers/__init__.py`
- [x] Implement `BenchmarkPoint`, `generate_synthetic_surgeries`, `run_scaling_benchmark`, and `format_benchmark_table` in `src/benchmark/runner.py` and `src/benchmark/__init__.py`
- [x] Write `tests/test_oracle_and_comparison.py` covering $n > 20$ oracle guard, 150+ randomized equivalence tests (`AdaptedGreedy == AdaptedDP == BruteForceOracle`), and benchmark runner tests

### Phase 4 — Final Verification & Consolidation Prep
- [x] Verify all identifiers use English (`en-US`), all docstrings/comments use Brazilian Portuguese (`pt-BR`), and `src/` uses zero third-party runtime dependencies

## Security Validation Tasks

- [x] Verify `BruteForceOracleScheduler` immediately rejects `len(surgeries) > 20` with `InvalidSchedulingInputError` before search execution
- [x] Verify all preprocessing and scheduler functions validate inputs without mutating caller-supplied collections
- [x] Confirm zero hardcoded secrets, tokens, or external network calls exist across `src/` and `tests/`

## Shift-Left Test Suite Tasks

### Happy Path
- [x] Verify `TP-01`: Unit tests for `is_actively_feasible` and `compute_effective_release_time` pass in `tests/test_preprocessing.py`
- [x] Verify `TP-02`: `SC-01` backward compatibility tests (`shift_config=None`) pass in `tests/test_adapted_schedulers.py`
- [x] Verify `TP-03`: `SC-02` 3-surgery counterexample proves Adapted Greedy/DP return `2` while Naive Reduction (`1`) and Classic Greedy fail
- [x] Verify `TP-04`: `SC-03` end-of-shift sterilization past $H$ and `SC-04b`/`SC-04c` shift-break clamping/overflow pass
- [x] Verify `TP-05`: `is_presorted=True` matches `is_presorted=False` for both `AdaptedGreedyScheduler` and `AdaptedDPScheduler`
- [x] Verify `TP-06`: 150+ seeded randomized tests confirm `AdaptedGreedy == AdaptedDP == BruteForceOracle`
- [x] Verify `TP-07`: `run_scaling_benchmark` and `format_benchmark_table` smoke tests pass in `tests/test_oracle_and_comparison.py`

### Edge Cases & Failure Modes
- [x] Verify `TE-01`: `SC-04a` active overlap rejection vs. boundary touching (`11:00–12:00`, `13:00–14:00`) passes
- [x] Verify `TE-02`: `SC-05` empty, single, all-infeasible, and $r_i$-tie tests pass
- [x] Verify `TE-03`: Exact shift boundaries ($e_i = A$ and $e_i = B$) pass
- [x] Verify `TE-04`: `BruteForceOracleScheduler` with `n = 21` raises `InvalidSchedulingInputError`
- [x] Verify `TE-05`: Unsorted `is_presorted=True` and filtered `presorted_start_indices` raise `InvalidSchedulingInputError`
- [x] Verify `TE-06`: Caller sequence non-mutation and `None`/invalid parameter guards pass

## Documentation Tasks

- [x] Merge `specs/algorithms-and-domain-architecture-delta.md` into `openspec/specs/algorithms-and-domain-architecture.md` upon archive
- [x] Merge `specs/testing-benchmark-and-visual-interface-delta.md` into `openspec/specs/testing-benchmark-and-visual-interface.md` upon archive

## Review Gate

- [x] All implementation tasks complete
- [x] All security validation tasks complete
- [x] All tests passing (`./.venv/bin/pytest -v`)
- [x] Proposal acceptance criteria verified
- [x] Ready for `sdd-spec-archive`
