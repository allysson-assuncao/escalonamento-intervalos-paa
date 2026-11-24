# Delta Spec: `algorithms-and-domain-architecture`

> **Change ID:** `simplify-core-and-presentation-ui`
> **Target Canonical Spec:** `openspec/specs/algorithms-and-domain-architecture.md`
> **Change Type:** Modify

## Architectural Updates

### 1. Simplified Strategy Contract (`src/schedulers/protocol.py`)
- Update `IntervalSchedulerProtocol.schedule` signature to:
  ```python
  def schedule(
      self,
      surgeries: Sequence[SurgeryRequest],
      shift_config: ShiftConfig | None = None,
  ) -> SchedulingResult: ...
  ```
- Remove `is_presorted`, `presorted_start_indices`, `validate_presorted_start_indices`, `_compute_predecessors_two_pointers`, and `_resolve_predecessors` from `src/schedulers/protocol.py` and all scheduler implementations (`ClassicGreedyScheduler`, `ClassicDPScheduler`, `AdaptedGreedyScheduler`, `AdaptedDPScheduler`, `BruteForceOracleScheduler`).
- Expose `compute_predecessors_binary_search(ordered: Sequence[ProcessedSurgery]) -> list[int]` using `bisect.bisect_right` in $\mathcal{O}(n \log n)$ inside `solve_interval_dp`.

### 2. Removal of Naive Reduction & Synthetic Benchmark Modules
- Delete `src/schedulers/naive_reduction.py` (`NaiveReductionScheduler`) and remove `_is_naive_interval_feasible`, `preprocess_naive_validated_surgeries`, and `preprocess_naive_static_reduction` from `src/domain/preprocessing.py` and `src/domain/__init__.py`.
- Delete `src/benchmark/` (`__init__.py`, `runner.py`) and remove `--benchmark`, `--sizes`, `--repetitions`, `--seed`, and `--presorted` CLI flags from `src/main.py`.

### 3. Enhanced Presentation Tracer & Lean HTTP Backend (`src/ui/`)
- Update `src/ui/scenarios_catalog.py` to export 4 didactic presets (`CASE-01`..`CASE-04`).
- Update `src/ui/tracer.py` to trace the 4 core algorithms, include `complexity_summary` on `SimulationTrace` (formulas, $\mathcal{O}(n \log n)$ / $\mathcal{O}(n)$ bounds, and per-phase operation counts), expose `last_release_minutes: int | None` on `SimulationStep`, and format step `variables` with didactic Portuguese/mathematical keys and `HH:MM (min)` values.
- Restrict `src/ui/server.py` endpoints to `GET /api/scenarios`, `POST /api/trace`, and `POST /api/compare` (removing `/api/generate` and `/api/benchmark`), using `MAX_COMPARE_INPUT_SIZE = 500`.
- Update Section 5 (Repository Layout) to reflect removed files (`naive_reduction.py`, `src/benchmark/`, `docs/relatorio-testes-benchmark-complexidade.md`).
