# Autonomous Execution Plan: Implement Adapted Surgical Scheduling (Change #3)

Focus: Backend / Python 3.12+ Algorithm Engineering & SDD Architecture
Target Change: `openspec/changes/implement-adapted-surgical-scheduling`

---

## Global Architectural Context & Invariants

You are executing the approved implementation plan for Change #3: **Adapted Surgical Scheduling** in `escalonamento-intervalos-paa`.

### Mandatory Project Constraints & Conventions
1. **Zero Third-Party Runtime Dependencies**: `src/` must exclusively utilize the Python 3.12+ Standard Library (`dataclasses`, `bisect`, `typing`, `enum`, `time`, `random`, `math`, `statistics`).
2. **Language Rules**:
   - Source code identifiers (modules, classes, methods, functions, variables, type hints): strictly English (`en-US`).
   - Inline code comments, docstrings, Git commit messages, and the cumulative execution walkthrough (`openspec/changes/implement-adapted-surgical-scheduling/walkthrough.md`): strictly Brazilian Portuguese (`pt-BR`).
   - OpenSpec documentation (`openspec/`): strictly English (`en-US`).
3. **Acyclic Dependency Layering**:
   - Host `validate_scheduler_inputs` in `src/domain/preprocessing.py` and re-export it from `src/schedulers/protocol.py`. The `src/domain/` package must NEVER import from `src/schedulers/`.
   - `src/schedulers/classic_greedy.py` must remain completely untouched.
4. **Shared Dynamic Programming Kernel**:
   - Extract a generalized unweighted DP kernel (`solve_interval_dp`) into `src/schedulers/protocol.py` parameterized by release time (`finish_time` for Classic DP vs `effective_release_time` for Adapted DP).
   - `ClassicDPScheduler` and `AdaptedDPScheduler` must both reuse this shared kernel without duplicating predecessor resolution, table filling, or backtracking. `ClassicDPScheduler` external API, behavior, and `presorted_start_indices` logic must remain 100% backward-compatible.
5. **Exact Mathematical Model & Safeguards**:
   - Active feasibility: $0 \le s_i < f_i \le H$ and ($f_i \le A$ or $s_i \ge B$) when `shift_window = [A, B]` is configured. When `shift_config is None`, active feasibility is unconditionally `True`.
   - Effective Release Time ($r_i$): $e_i = f_i + c_i$. If `shift_window = [A, B]` with $f_i \le A$ and $A < e_i < B$, clamp to $r_i = B$; otherwise $r_i = e_i$.
   - When `shift_config is None`, adapted schedulers skip horizon/break filtering (`discarded_infeasible_count = 0`) while continuing to enforce biological cooldown ($r_i = f_i + c_i$).
   - In `AdaptedDPScheduler`, passing `presorted_start_indices` when infeasible items were discarded (`discarded_infeasible_count > 0`) must immediately raise `InvalidSchedulingInputError`.
   - In `BruteForceOracleScheduler`, enforce the hard guard `MAX_ORACLE_INPUT_SIZE = 20`. Any input with $n > 20$ must immediately raise `InvalidSchedulingInputError` before any search.
6. **Sequential Execution Protocol**:
   - Execute the 4 phases strictly in order (Phase 1 -> Phase 2 -> Phase 3 -> Phase 4).
   - At the conclusion of each phase:
     1. Run test validation: `./.venv/bin/pytest -v`.
     2. Update `openspec/changes/implement-adapted-surgical-scheduling/tasks.md`, marking completed phase tasks `[x]`.
     3. Append the phase execution log in Brazilian Portuguese (`pt-BR`) to `openspec/changes/implement-adapted-surgical-scheduling/walkthrough.md`.
     4. Create an atomic Git commit with a descriptive message in `pt-BR`.

---

## Phase 1: Domain Preprocessing, Naive Reduction & Scenarios SC-02..SC-05

Focus: Domain Preprocessing & Test Fixtures
Task: Execute Phase 1 of `implement-adapted-surgical-scheduling`

### Execution Context
- Active Plan: `openspec/changes/implement-adapted-surgical-scheduling/tasks.md` (Phase 1 tasks)
- Scope: Execute Phase 1 only. Establish domain preprocessing, shared validation/DP kernel extraction, naive static reduction, and canonical scenario fixtures.

### Implementation Steps
1. **Layering & Validation Placement (`src/domain/preprocessing.py`, `src/schedulers/protocol.py`)**:
   - Move/place `validate_scheduler_inputs(surgeries, shift_config)` in `src/domain/preprocessing.py`.
   - Re-export `validate_scheduler_inputs` in `src/schedulers/protocol.py` so existing importers (`src/schedulers/classic_greedy.py`, `src/schedulers/classic_dp.py`, and tests) continue working without modification.
2. **Preprocessing Contracts (`src/domain/preprocessing.py`, `src/domain/__init__.py`)**:
   - Implement `is_actively_feasible(surgery: SurgeryRequest, shift_config: ShiftConfig | None) -> bool`:
     - If `shift_config is None`: return `True`.
     - If `shift_config` is set: enforce $0 \le s_i < f_i \le H$. If `shift_config.shift_window` is present ($[A, B]$), enforce $f_i \le A$ or $s_i \ge B$.
   - Implement `compute_effective_release_time(surgery: SurgeryRequest, shift_config: ShiftConfig | None) -> int`:
     - Raw end time $e_i = f_i + c_i$.
     - If `shift_config` defines `shift_window = [A, B]`: return $B$ if $f_i \le A$ and $A < e_i < B$; otherwise return $e_i$.
     - If no shift window or `shift_config is None`: return $e_i$.
   - Implement `preprocess_feasible_surgeries(surgeries: Sequence[SurgeryRequest], shift_config: ShiftConfig | None = None) -> tuple[list[ProcessedSurgery], int]`:
     - Validate inputs via `validate_scheduler_inputs`.
     - Filter surgeries using `is_actively_feasible`. For feasible surgeries, compute $r_i$ and wrap in `ProcessedSurgery(request=item, effective_release_time=r_i)`.
     - Return `(feasible_processed_surgeries, discarded_infeasible_count)`.
   - Implement `preprocess_naive_static_reduction(surgeries: Sequence[SurgeryRequest], shift_config: ShiftConfig | None = None) -> tuple[list[ProcessedSurgery], int]`:
     - Applies naive transformation $f'_i = f_i + c_i$. Filters items where $f'_i > H$ or $[s_i, f'_i)$ overlaps $[A, B)$ ($f'_i \le A$ or $s_i \ge B$).
     - Wraps feasible items as `ProcessedSurgery(request=item, effective_release_time=f'_i)` and returns `(feasible_processed_surgeries, discarded_infeasible_count)`.
   - Export all new functions in `src/domain/__init__.py`.
3. **Shared DP Kernel & Ordering (`src/schedulers/protocol.py`, `src/schedulers/classic_dp.py`)**:
   - Implement `order_processed_surgeries(items: list[ProcessedSurgery], *, is_presorted: bool) -> list[ProcessedSurgery]`:
     - Sorts or validates ordering by `(item.effective_release_time, item.request.finish_time, item.request.start_time)`. In `is_presorted=True` mode, validate in $\mathcal{O}(n)$ and raise `InvalidSchedulingInputError` if unsorted.
   - Extract parameterized unweighted interval DP solver helper (`solve_interval_dp`) in `src/schedulers/protocol.py`:
     - Parameterized to handle predecessor resolution (binary search `bisect_right` vs two-pointer sweep), DP table filling, and iterative backtracking.
   - Refactor `ClassicDPScheduler` in `src/schedulers/classic_dp.py` to delegate to `solve_interval_dp` while preserving existing public API and behavior.
4. **Naive Reduction Scheduler (`src/schedulers/naive_reduction.py`)**:
   - Implement `NaiveReductionScheduler` implementing `IntervalSchedulerProtocol` (`name = "Naive Static Reduction"`).
   - Preprocesses input with `preprocess_naive_static_reduction`, executes classical earliest-finish greedy selection on reduced intervals, and returns `SchedulingResult` containing `ProcessedSurgery` items with `effective_release_time = item.finish_time + item.sterilization_duration`.
5. **Deterministic Scenarios (`tests/fixtures/scenarios.py`)**:
   - Add builders for:
     - `SC-02`: `build_sc02_counterexample_surgeries()` and `build_sc02_shift_config()` ($H = 1080$, $S1=[780, 840, C, 120]$, $S2=[810, 900, L, 0]$, $S3=[900, 1065, C, 60]$).
     - `SC-03`: `build_sc03_end_of_shift_boundary()` ($H = 1080$, $S_{\text{END}}=[1040, 1070, C, 30]$, $S_{\text{OVER}}=[1050, 1081, L, 0]$).
     - `SC-04`: `build_sc04_shift_window_scenarios()` (`SC-04a` overlap rejection vs boundary touching; `SC-04b` sterilization absorption into $[A, B]$; `SC-04c` sterilization overflow past $B$).
     - `SC-05`: `build_sc05_edge_case_scenarios()` (all-infeasible surgeries, $r_i$ tie-breaking).
6. **Unit Test Suite (`tests/test_preprocessing.py`)**:
   - Implement tests covering `is_actively_feasible`, `compute_effective_release_time`, boundaries ($e_i = A$, $e_i = B$), `preprocess_feasible_surgeries`, `preprocess_naive_static_reduction`, and defensive copy immutability.

### Quality Gates & Verification
- Run tests: `./.venv/bin/pytest -v` (must achieve 100% pass across all tests, including existing classic tests).
- Update tasks: Check off Phase 1 tasks in `openspec/changes/implement-adapted-surgical-scheduling/tasks.md`.
- Update walkthrough: Create/append Phase 1 entry in `openspec/changes/implement-adapted-surgical-scheduling/walkthrough.md` in Brazilian Portuguese (`pt-BR`).
- Git commit in `pt-BR`:
  ```bash
  git add src/ tests/ openspec/changes/implement-adapted-surgical-scheduling/
  git commit -m "feat(domain): implementa pré-processamento cirúrgico, redução ingênua e cenários SC-02 a SC-05"
  ```

---

## Phase 2: Authorial Adapted Schedulers (Greedy & DP)

Focus: Adapted Schedulers Implementation & Comparative Proof
Task: Execute Phase 2 of `implement-adapted-surgical-scheduling`

### Execution Context
- Active Plan: `openspec/changes/implement-adapted-surgical-scheduling/tasks.md` (Phase 2 tasks)
- Scope: Execute Phase 2 only. Implement `AdaptedGreedyScheduler` and `AdaptedDPScheduler`, and write comprehensive tests proving optimality on `SC-02` against baseline algorithms.

### Implementation Steps
1. **Adapted Greedy Scheduler (`src/schedulers/adapted_greedy.py`)**:
   - Implement `AdaptedGreedyScheduler` conforming to `IntervalSchedulerProtocol`.
   - Algorithm Name: `"Adapted Greedy (Earliest Effective Release Time)"`.
   - Method: `schedule(surgeries: Sequence[SurgeryRequest], shift_config: ShiftConfig | None = None, *, is_presorted: bool = False) -> SchedulingResult`:
     - Calls `preprocess_feasible_surgeries(surgeries, shift_config)`.
     - Measures algorithm runtime using `time.perf_counter_ns()`.
     - Orders feasible processed surgeries using `order_processed_surgeries(..., is_presorted=is_presorted)`.
     - Greedily selects compatible items where `item.request.start_time >= last_release`.
     - Returns `SchedulingResult` with selected items, `total_selected`, `discarded_infeasible_count`, and `elapsed_ns`.
2. **Adapted Dynamic Programming Scheduler (`src/schedulers/adapted_dp.py`)**:
   - Implement `AdaptedDPScheduler` conforming to `IntervalSchedulerProtocol`.
   - Algorithm Name: `"Adapted Dynamic Programming"`.
   - Method: `schedule(surgeries: Sequence[SurgeryRequest], shift_config: ShiftConfig | None = None, *, is_presorted: bool = False, presorted_start_indices: Sequence[int] | None = None) -> SchedulingResult`:
     - Validates `presorted_start_indices`: raise `InvalidSchedulingInputError` if provided when `is_presorted=False`.
     - Preprocesses: `feasible, discarded = preprocess_feasible_surgeries(surgeries, shift_config)`.
     - Critical Guard: If `presorted_start_indices is not None` and `discarded > 0`, raise `InvalidSchedulingInputError` (indices cannot safely map when items were filtered out).
     - If `presorted_start_indices is not None` and `discarded == 0`, validate permutation and monotonic start times on `feasible`.
     - Reuses shared DP kernel in `src/schedulers/protocol.py`, resolving predecessors against `effective_release_time` via two pointers ($\mathcal{O}(n)$) or binary search `bisect_right` ($\mathcal{O}(n \log n)$).
     - Backtracks to reconstruct exact optimal schedule.
3. **Module Exports (`src/schedulers/__init__.py`)**:
   - Export `NaiveReductionScheduler`, `AdaptedGreedyScheduler`, and `AdaptedDPScheduler`.
4. **Verification Test Suite (`tests/test_adapted_schedulers.py`)**:
   - Implement comprehensive tests:
     - `TP-02`: Backward compatibility on `SC-01` (`shift_config=None`): Adapted Greedy and Adapted DP match Classic solvers (`total_selected == 5`).
     - `TP-03`: `SC-02` counterexample comparative proof: Adapted Greedy and Adapted DP select `{"S2", "S3"}` (`total_selected == 2`), while `ClassicGreedyScheduler` (picks `"S1"`) and `NaiveReductionScheduler` (discards `"S3"`) achieve at most `1`.
     - `TP-04`: `SC-03` passive sterilization past $H$ ($r_i = 18:20$) and `SC-04b`/`SC-04c` shift-break absorption ($r_i = 13:00$) / overflow ($r_i = 13:15$).
     - `TP-05`: `is_presorted=True` parity with `is_presorted=False` for both adapted schedulers.
     - `TE-01`: `SC-04a` active break overlap rejection vs boundary touching.
     - `TE-02`: `SC-05` empty list, single surgery, all-infeasible, and $r_i$ tie-breaks.
     - `TE-05`: Unsorted sequence with `is_presorted=True` and `presorted_start_indices` with `discarded > 0` raising `InvalidSchedulingInputError`.

### Quality Gates & Verification
- Run tests: `./.venv/bin/pytest -v`.
- Update tasks: Check off Phase 2 tasks in `openspec/changes/implement-adapted-surgical-scheduling/tasks.md`.
- Update walkthrough: Append Phase 2 progress entry to `openspec/changes/implement-adapted-surgical-scheduling/walkthrough.md` in `pt-BR`.
- Git commit in `pt-BR`:
  ```bash
  git add src/ tests/ openspec/changes/implement-adapted-surgical-scheduling/
  git commit -m "feat(schedulers): implementa algoritmos adaptados Guloso e PD com esterilização e janelas de turno"
  ```

---

## Phase 3: Exact Brute-Force Oracle & Empirical Benchmark Runner

Focus: Oracle Verification & Asymptotic Benchmarking
Task: Execute Phase 3 of `implement-adapted-surgical-scheduling`

### Execution Context
- Active Plan: `openspec/changes/implement-adapted-surgical-scheduling/tasks.md` (Phase 3 tasks)
- Scope: Execute Phase 3 only. Implement the bounded brute-force oracle scheduler, the empirical benchmark runner, and 150+ randomized property-based cross-validation tests.

### Implementation Steps
1. **Brute-Force Oracle Scheduler (`src/schedulers/brute_force_oracle.py`, `src/schedulers/__init__.py`)**:
   - Implement `BruteForceOracleScheduler` conforming to `IntervalSchedulerProtocol`.
   - Algorithm Name: `"Brute-Force Oracle"`.
   - Hard DoS Guard: Define `MAX_ORACLE_INPUT_SIZE: int = 20`.
     - If `len(surgeries) > MAX_ORACLE_INPUT_SIZE`, immediately raise `InvalidSchedulingInputError(f"O oráculo exaustivo suporta no máximo {MAX_ORACLE_INPUT_SIZE} cirurgias (recebeu {len(surgeries)}).")` before performing any search.
   - Preprocesses input via `preprocess_feasible_surgeries`.
   - Finds the mathematically exact optimal compatible subset via exhaustive branch-and-bound search with pruning.
   - Export in `src/schedulers/__init__.py`.
2. **Empirical Benchmark Runner (`src/benchmark/runner.py`, `src/benchmark/__init__.py`)**:
   - Define `@dataclass(frozen=True) class BenchmarkPoint`:
     - Fields: `algorithm_name: str`, `input_size: int`, `feasible_count: int`, `selected_count: int`, `median_elapsed_ns: int`, `mean_elapsed_ns: float`, `normalized_n_log_n_ratio: float`, `normalized_linear_ratio: float`, `is_presorted: bool`.
   - Implement `generate_synthetic_surgeries(n: int, *, seed: int = 42, shift_config: ShiftConfig | None = None, contaminated_ratio: float = 0.4) -> list[SurgeryRequest]`:
     - Deterministic generation using `random.Random(seed)`. Validates arguments strictly ($n \ge 0$, $0.0 \le \text{contaminated\_ratio} \le 1.0$).
   - Implement `run_scaling_benchmark(schedulers: Sequence[IntervalSchedulerProtocol], sizes: Sequence[int] = (100, 500, 1000, 2500, 5000), *, shift_config: ShiftConfig | None = None, repetitions: int = 3, seed: int = 42, is_presorted: bool = False) -> list[BenchmarkPoint]`:
     - Runs each scheduler across sizes and repetitions. Isolates `schedule()` invocation from synthetic instance generation (and when `is_presorted=True`, pre-sorts inputs per scheduler before timing).
     - Computes `median_elapsed_ns` and `mean_elapsed_ns` across repetitions, and normalized asymptotic ratios:
       $$\text{normalized\_n\_log\_n\_ratio} = \frac{\text{median\_elapsed\_ns}}{n \log_2 n} \quad (n > 1, \text{ else } 0.0), \quad \text{normalized\_linear\_ratio} = \frac{\text{median\_elapsed\_ns}}{n} \quad (n > 0, \text{ else } 0.0)$$
   - Implement `format_benchmark_table(points: Sequence[BenchmarkPoint]) -> str`:
     - Produces a formatted Markdown table comparing algorithm performance and scaling ratios across input sizes.
   - Export `BenchmarkPoint`, `generate_synthetic_surgeries`, `run_scaling_benchmark`, and `format_benchmark_table` in `src/benchmark/__init__.py`.
3. **Randomized Oracle Cross-Validation Suite (`tests/test_oracle_and_comparison.py`)**:
   - `TE-04`: Verify `BruteForceOracleScheduler` with $n = 21$ immediately raises `InvalidSchedulingInputError`.
   - `TP-06`: Implement 150+ deterministic seeded randomized test instances ($n \in [0, 16]$, varying clean/contaminated ratios, shift configs, and seeds):
     - Assert `AdaptedGreedy.total_selected == AdaptedDP.total_selected == BruteForceOracle.total_selected` on 100% of instances.
     - Verify structural validity on all returned schedules: pairwise $s_k \ge r_{k-1}$, all $f_k \le H$, and no active overlap with $[A, B)$.
   - `TP-07`: Smoke tests for `generate_synthetic_surgeries`, `run_scaling_benchmark(schedulers, sizes=(20, 50), repetitions=2)`, and `format_benchmark_table`.

### Quality Gates & Verification
- Run tests: `./.venv/bin/pytest -v`.
- Update tasks: Check off Phase 3 tasks in `openspec/changes/implement-adapted-surgical-scheduling/tasks.md`.
- Update walkthrough: Append Phase 3 progress entry to `openspec/changes/implement-adapted-surgical-scheduling/walkthrough.md` in `pt-BR`.
- Git commit in `pt-BR`:
  ```bash
  git add src/ tests/ openspec/changes/implement-adapted-surgical-scheduling/
  git commit -m "feat(benchmark): implementa oráculo exaustivo de força bruta e executor de benchmark assintótico"
  ```

---

## Phase 4: Final Quality Verification, Spec Consolidation & Archival

Focus: Quality Assurance, Delta Spec Consolidation & Change Archival
Task: Execute Phase 4 of `implement-adapted-surgical-scheduling`

### Execution Context
- Active Plan: `openspec/changes/implement-adapted-surgical-scheduling/tasks.md` (Phase 4, Security, Shift-Left, Documentation, and Review Gate tasks)
- Scope: Execute Phase 4. Conduct all quality, security, and language audits, consolidate delta specs into canonical specs, archive the change using `sdd-spec-archive`, and produce the consolidated final walkthrough.

### Implementation Steps
1. **Quality, Security & Language Gates**:
   - Run full test suite: `./.venv/bin/pytest -v` (ensure all tests pass cleanly).
   - Secret scan: Ensure zero passwords, tokens, API keys, or hardcoded credentials exist across `src/` and `tests/`.
   - Dependency audit: Verify `src/` contains zero external third-party imports (Python Standard Library only).
   - Language compliance audit:
     - Check identifiers (`modules`, `classes`, `functions`, `variables`, `type hints`): 100% English (`en-US`).
     - Check inline comments, docstrings, and commit messages: 100% Brazilian Portuguese (`pt-BR`).
2. **Delta Specification Consolidation**:
   - Merge `openspec/changes/implement-adapted-surgical-scheduling/specs/algorithms-and-domain-architecture-delta.md` into `openspec/specs/algorithms-and-domain-architecture.md`.
   - Merge `openspec/changes/implement-adapted-surgical-scheduling/specs/testing-benchmark-and-visual-interface-delta.md` into `openspec/specs/testing-benchmark-and-visual-interface.md`.
   - Ensure the canonical living specs accurately document:
     - The placement of `validate_scheduler_inputs` in the domain layer and its re-export in `src/schedulers/protocol.py`.
     - The shared DP kernel in `src/schedulers/protocol.py` and its parameterization.
     - `NaiveReductionScheduler`, `AdaptedGreedyScheduler`, `AdaptedDPScheduler`, and `BruteForceOracleScheduler`.
     - The benchmark module (`src/benchmark/runner.py`) and its public API.
     - Scenarios `SC-02` through `SC-05` and oracle cross-validation testing.
3. **Task Completion & Consolidated Walkthrough**:
   - Mark all remaining checkboxes as completed `[x]` in `openspec/changes/implement-adapted-surgical-scheduling/tasks.md` and `proposal.md`.
   - Finalize `openspec/changes/implement-adapted-surgical-scheduling/walkthrough.md` in Brazilian Portuguese (`pt-BR`) with:
     - Complete list of all files created and modified across all 4 phases.
     - Full test summary (`pytest -v` output, scenario verification, oracle cross-validation).
     - Clear handoff summary preparing the workspace for Change #4 (Visual Interface and UI demonstration).
4. **Change Archival Gate**:
   - Activate skill `sdd-spec-archive` for change `implement-adapted-surgical-scheduling`.
   - Verify no `*-delta.md` files exist in `openspec/specs/` and confirm the change (including `walkthrough.md`) is safely archived into `openspec/archive/`.
5. **Final Git Commit**:
   - Create final commit in `pt-BR` (do not commit the temporary root prompt file unless requested):
     ```bash
     git add openspec/ src/ tests/
     git commit -m "docs(openspec): consolida especificações canônicas e arquiva change implement-adapted-surgical-scheduling"
     ```

### Quality Gates & Verification
- Verify `./.venv/bin/pytest -v` passes after consolidation and archiving.
- Verify working tree is clean with `git status`.
