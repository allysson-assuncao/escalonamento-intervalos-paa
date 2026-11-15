# Delta Spec: `testing-benchmark-and-visual-interface`

> **Change ID:** `implement-adapted-surgical-scheduling`
> **Target Canonical Spec:** `openspec/specs/testing-benchmark-and-visual-interface.md`
> **Change Type:** Modify

## Architectural Updates

### 1. Deterministic Fixture Coverage (`tests/fixtures/scenarios.py`)
- Codify builder functions for all canonical scenarios:
  - `build_sc02_counterexample_surgeries()` and `ShiftConfig(closing_horizon=1080)`
  - `build_sc03_end_of_shift_boundary()` (`S_END` 17:20–17:50 + 30m vs `S_OVER` 17:30–18:01)
  - `build_sc04_shift_window_scenarios()` (`SC-04a`, `SC-04b`, `SC-04c` under `[12:00, 13:00]`)
  - `build_sc05_edge_case_scenarios()` (all-infeasible set, $r_i$ tie-breaking set)

### 2. Automated Verification Suites
- `tests/test_preprocessing.py`: unit verification of active feasibility, closed-form $r_i$, exact `[A, B]` boundary handling ($e_i = A$, $e_i = B$), and naive static reduction behavior.
- `tests/test_adapted_schedulers.py`: comparative tests confirming `AdaptedGreedyScheduler` and `AdaptedDPScheduler` match Classic solvers on `SC-01` (`shift_config=None`), defeat `ClassicGreedyScheduler` and `NaiveReductionScheduler` on `SC-02`, handle `SC-03..SC-05`, and support `is_presorted=True`.
- `tests/test_oracle_and_comparison.py`: cross-validation of `AdaptedGreedyScheduler == AdaptedDPScheduler == BruteForceOracleScheduler` across 150+ deterministic seeded instances ($n \in [0, 16]$), $n = 21$ oracle guard verification, and `src/benchmark/runner.py` scaling smoke tests.
