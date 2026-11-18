# Delta Spec: `algorithms-and-domain-architecture`

> **Change ID:** `implement-adapted-surgical-scheduling`
> **Target Canonical Spec:** `openspec/specs/algorithms-and-domain-architecture.md`
> **Change Type:** Modify

## Architectural Updates

### 1. Layering & Shared Validation Placement
- Host `validate_scheduler_inputs(surgeries, shift_config)` in `src/domain/preprocessing.py` and re-export it from `src/schedulers/protocol.py` so `src/domain/` maintains strict acyclic dependency boundaries and never imports from `src/schedulers/`.

### 2. Preprocessing & Naive Static Reduction Contracts (`src/domain/preprocessing.py`, `src/schedulers/naive_reduction.py`)
- `is_actively_feasible(surgery, shift_config)`: returns `True` unconditionally when `shift_config is None`; otherwise enforces $f_i \le H$ and, when `shift_window = [A, B]` exists, enforces $f_i \le A$ or $s_i \ge B$.
- `compute_effective_release_time(surgery, shift_config)`: computes $e_i = f_i + c_i$, returning $B$ if `shift_config` defines `[A, B]` with $f_i \le A$ and $A < e_i < B$, and $e_i$ otherwise.
- `preprocess_feasible_surgeries(surgeries, shift_config=None)` returns `(feasible_processed_surgeries, discarded_infeasible_count)` in $\mathcal{O}(n)$.
- `preprocess_naive_static_reduction(surgeries, shift_config=None)` and `NaiveReductionScheduler` apply the flawed transformation $f'_i = f_i + c_i$ against active constraints $H$ and $[A, B]$ to demonstrate non-reducibility in `SC-02` and `SC-03`.

### 3. Shared Interval DP Kernel & Adapted Solver Contracts
- `src/schedulers/protocol.py` provides `order_processed_surgeries` (sorting/validating by `(effective_release_time, request.finish_time, request.start_time)`) and a parameterized unweighted interval DP kernel (`solve_interval_dp`) shared by both `ClassicDPScheduler` and `AdaptedDPScheduler` to eliminate duplicated DP/two-pointer/backtracking logic.
- When `shift_config=None`, `AdaptedGreedyScheduler` and `AdaptedDPScheduler` skip $H$ and $[A, B]$ feasibility filtering (`discarded_infeasible_count = 0`) while still computing biological cooldown release times $r_i = f_i + c_i$.
- In `AdaptedDPScheduler.schedule(..., is_presorted=True, presorted_start_indices=...)`, passing `presorted_start_indices` while any input item was filtered out by `shift_config` (`discarded_infeasible_count > 0`) MUST raise `InvalidSchedulingInputError`.

### 4. Exact Oracle & Benchmark Module (`src/schedulers/brute_force_oracle.py`, `src/benchmark/runner.py`)
- `BruteForceOracleScheduler` implements `IntervalSchedulerProtocol` with `MAX_ORACLE_INPUT_SIZE = 20`, raising `InvalidSchedulingInputError` immediately when `len(surgeries) > 20`.
- `src/benchmark/runner.py` exposes `BenchmarkPoint`, `generate_synthetic_surgeries`, `run_scaling_benchmark`, and `format_benchmark_table` using strictly Python 3.12+ Standard Library modules (`random`, `math`, `statistics`, `time`, `dataclasses`).
