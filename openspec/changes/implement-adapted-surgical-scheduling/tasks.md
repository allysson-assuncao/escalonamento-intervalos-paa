# Tasks: Implement Adapted Surgical Scheduling

> **Change ID:** `implement-adapted-surgical-scheduling`
> **Linked Proposal:** [proposal.md](./proposal.md)
> **Status:** in-progress
>
> All tasks must be `[x]` before this change can be archived via `sdd-spec-archive`.

---

## Implementation Tasks

### Phase 1 — Domain Preprocessing, Naive Reduction & Counterexample Fixtures
- [ ] Move/place `validate_scheduler_inputs` in `src/domain/preprocessing.py` (re-exporting in `src/schedulers/protocol.py`) to maintain clean acyclic `domain -> schedulers` layering
- [ ] Implement `is_actively_feasible`, `compute_effective_release_time`, `preprocess_feasible_surgeries`, and `preprocess_naive_static_reduction` in `src/domain/preprocessing.py` and export them in `src/domain/__init__.py`
- [ ] Add `order_processed_surgeries` and parameterized unweighted interval DP kernel (`solve_interval_dp`) to `src/schedulers/protocol.py` and refactor `src/schedulers/classic_dp.py` to reuse it without behavior changes
- [ ] Implement `NaiveReductionScheduler` in `src/schedulers/naive_reduction.py`
- [ ] Expand `tests/fixtures/scenarios.py` with `SC-02`, `SC-03`, `SC-04a/b/c`, and `SC-05` fixtures and write `tests/test_preprocessing.py`

### Phase 2 — Authorial Adapted Schedulers (Greedy & DP)
- [ ] Implement `AdaptedGreedyScheduler` in `src/schedulers/adapted_greedy.py` ($\mathcal{O}(n \log n)$ general, $\mathcal{O}(n)$ pre-sorted, supporting `shift_config=None` and `[A, B]`/`H`)
- [ ] Implement `AdaptedDPScheduler` in `src/schedulers/adapted_dp.py` ($\mathcal{O}(n \log n)$ via `bisect_right`, $\mathcal{O}(n)$ two-pointer pre-sorted mode with `presorted_start_indices`, iterative DP + backtracking)
- [ ] Write `tests/test_adapted_schedulers.py` covering `SC-01`..`SC-05`, pre-sorted mode, `shift_config=None`, and comparative proof against `ClassicGreedyScheduler` and `NaiveReductionScheduler`

### Phase 3 — Exact Brute-Force Oracle & Empirical Benchmark Runner
- [ ] Implement `BruteForceOracleScheduler` (`MAX_ORACLE_INPUT_SIZE = 20`) in `src/schedulers/brute_force_oracle.py` and update exports in `src/schedulers/__init__.py`
- [ ] Implement `BenchmarkPoint`, `generate_synthetic_surgeries`, `run_scaling_benchmark`, and `format_benchmark_table` in `src/benchmark/runner.py` and `src/benchmark/__init__.py`
- [ ] Write `tests/test_oracle_and_comparison.py` covering $n > 20$ oracle guard, 150+ randomized equivalence tests (`AdaptedGreedy == AdaptedDP == BruteForceOracle`), and benchmark runner tests

### Phase 4 — Final Verification & Consolidation Prep
- [ ] Verify all identifiers use English (`en-US`), all docstrings/comments use Brazilian Portuguese (`pt-BR`), and `src/` uses zero third-party runtime dependencies

## Security Validation Tasks

- [ ] Verify `BruteForceOracleScheduler` immediately rejects `len(surgeries) > 20` with `InvalidSchedulingInputError` before search execution
- [ ] Verify all preprocessing and scheduler functions validate inputs without mutating caller-supplied collections
- [ ] Confirm zero hardcoded secrets, tokens, or external network calls exist across `src/` and `tests/`

## Shift-Left Test Suite Tasks

### Happy Path
- [ ] Verify `TP-01`: Unit tests for `is_actively_feasible` and `compute_effective_release_time` pass in `tests/test_preprocessing.py`
- [ ] Verify `TP-02`: `SC-01` backward compatibility tests (`shift_config=None`) pass in `tests/test_adapted_schedulers.py`
- [ ] Verify `TP-03`: `SC-02` 3-surgery counterexample proves Adapted Greedy/DP return `2` while Naive Reduction (`1`) and Classic Greedy fail
- [ ] Verify `TP-04`: `SC-03` end-of-shift sterilization past $H$ and `SC-04b`/`SC-04c` shift-break clamping/overflow pass
- [ ] Verify `TP-05`: `is_presorted=True` matches `is_presorted=False` for both `AdaptedGreedyScheduler` and `AdaptedDPScheduler`
- [ ] Verify `TP-06`: 150+ seeded randomized tests confirm `AdaptedGreedy == AdaptedDP == BruteForceOracle`
- [ ] Verify `TP-07`: `run_scaling_benchmark` and `format_benchmark_table` smoke tests pass in `tests/test_oracle_and_comparison.py`

### Edge Cases & Failure Modes
- [ ] Verify `TE-01`: `SC-04a` active overlap rejection vs. boundary touching (`11:00–12:00`, `13:00–14:00`) passes
- [ ] Verify `TE-02`: `SC-05` empty, single, all-infeasible, and $r_i$-tie tests pass
- [ ] Verify `TE-03`: Exact shift boundaries ($e_i = A$ and $e_i = B$) pass
- [ ] Verify `TE-04`: `BruteForceOracleScheduler` with `n = 21` raises `InvalidSchedulingInputError`
- [ ] Verify `TE-05`: Unsorted `is_presorted=True` and filtered `presorted_start_indices` raise `InvalidSchedulingInputError`
- [ ] Verify `TE-06`: Caller sequence non-mutation and `None`/invalid parameter guards pass

## Documentation Tasks

- [ ] Merge `specs/algorithms-and-domain-architecture-delta.md` into `openspec/specs/algorithms-and-domain-architecture.md` upon archive
- [ ] Merge `specs/testing-benchmark-and-visual-interface-delta.md` into `openspec/specs/testing-benchmark-and-visual-interface.md` upon archive

## Review Gate

- [ ] All implementation tasks complete
- [ ] All security validation tasks complete
- [ ] All tests passing (`./.venv/bin/pytest -v`)
- [ ] Proposal acceptance criteria verified
- [ ] Ready for `sdd-spec-archive`
