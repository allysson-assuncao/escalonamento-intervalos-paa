---
id: "algorithms-and-domain-architecture"
title: "Algorithms and Domain Architecture — Classic vs. Adapted Solvers"
version: "1.4.0"
status: "active"
owners:
  - "@allysson-assuncao"
scope:
  paths:
    - "src/**"
resources:
  - "openspec/specs/sdd-stack-contract.md"
  - "openspec/specs/problem-definition-and-mathematical-model.md"
---

# Algorithms and Domain Architecture — Living Specification

> This is the authoritative source of truth for domain data structures, input validation invariants, solver contracts, algorithmic steps for all four schedulers (Classic Greedy, Classic DP, Adapted Greedy, Adapted DP), and the Python modular architecture.
> Update this file only after merging a completed change from `openspec/changes/`.

---

## Context & Objectives

To uphold SOLID principles, Clean Code, and side-by-side comparability between textbook baselines and authorial adaptations, the codebase separates immutable domain modeling, shift/interval validation, scheduling strategies, and empirical benchmarking into distinct, single-responsibility Python 3.12+ modules relying solely on the Python Standard Library for core algorithms.

---

## 1. Domain Data Models & Validation Invariants

All core data structures MUST be immutable (`@dataclass(frozen=True)`) and typed with strict Python type annotations.

### 1.1. Enumerations & Value Objects
- **`SurgeryType(Enum)`**:
  - `CLEAN = "CLEAN"`
  - `CONTAMINATED = "CONTAMINATED"`
- **`ShiftWindow`**:
  - `start: int` ($A$, in integer time units such as minutes from day start)
  - `end: int` ($B$)
  - **Invariant**: $0 \le A < B$.
- **`ShiftConfig`**:
  - `closing_horizon: int` ($H$)
  - `shift_window: ShiftWindow | None = None` ($[A, B]$)
  - **Invariants**:
    - $H > 0$.
    - If `shift_window is not None`: $0 \le A < B \le H$.
- **`SurgeryRequest`**:
  - `surgery_id: str` (non-empty unique/traceable identifier)
  - `start_time: int` ($s_i$)
  - `finish_time: int` ($f_i$)
  - `surgery_type: SurgeryType = SurgeryType.CLEAN` ($t_i$)
  - `sterilization_duration: int = 0` ($c_i$)
  - **Invariants**:
    - `surgery_id.strip() != ""`
    - $0 \le s_i < f_i$
    - $c_i \ge 0$
    - If $t_i == \text{CLEAN}$, then $c_i == 0$ (enforced on construction)
    - If $t_i == \text{CONTAMINATED}$, then $c_i > 0$ (enforced on construction)
- **`ProcessedSurgery`**:
  - `request: SurgeryRequest`
  - `effective_release_time: int` ($r_i$)
- **`SchedulingResult`**:
  - `algorithm_name: str`
  - `selected_surgeries: tuple[ProcessedSurgery, ...]` (chronologically ordered)
  - `total_selected: int`
  - `discarded_infeasible_count: int`
  - `elapsed_ns: int` (high-resolution execution timing via `time.perf_counter_ns()`)

### 1.2. Defensive Input Validation & Layering
- Invalid structural inputs (e.g., $s_i \ge f_i$, negative timestamps, `CLEAN` surgery with $c_i > 0$, `CONTAMINATED` surgery with $c_i \le 0$, or `ShiftWindow` outside $[0, H]$) MUST raise a dedicated domain exception (`InvalidSchedulingInputError(ValueError)`).
- Validation MUST happen explicitly at construction/entry boundaries without mutating caller-owned collections.
- `validate_scheduler_inputs(surgeries, shift_config)` is hosted in `src/domain/preprocessing.py` and re-exported from `src/schedulers/protocol.py` so `src/domain/` maintains strict acyclic dependency boundaries and never imports from `src/schedulers/`.

---

## 2. Unified Strategy Contract & Shared Kernel (Dependency Inversion)

All schedulers MUST implement a shared Python `Protocol` so benchmarking harnesses, comparative tests, and the visual interface depend only on the abstraction:

```python
class IntervalSchedulerProtocol(Protocol):
    @property
    def name(self) -> str: ...

    def schedule(
        self,
        surgeries: Sequence[SurgeryRequest],
        shift_config: ShiftConfig | None = None,
        *,
        is_presorted: bool = False,
    ) -> SchedulingResult: ...
```

`src/schedulers/protocol.py` also provides `order_processed_surgeries` (sorting or validating by `(effective_release_time, request.finish_time, request.start_time)`), `select_greedy_processed_surgeries`, `validate_presorted_start_indices`, and the parameterized unweighted interval DP kernel (`solve_interval_dp`) shared by both `ClassicDPScheduler` and `AdaptedDPScheduler` to eliminate duplicated DP, two-pointer/binary-search predecessor, and backtracking logic.

---

## 3. Baseline Classic Solvers (Retained for Comparison)

Both classic algorithms serve as permanent comparative baselines reflecting standard textbook behavior before authorial adaptation.

### 3.1. `ClassicGreedyScheduler` ($\mathcal{O}(n \log n)$ / $\mathcal{O}(n)$ pre-sorted)
- **Compatibility Criterion**: Operates strictly in **Pure Classic Textbook Mode** over active surgical intervals $[s_i, f_i]$ ($s_j \ge f_i$). It intentionally ignores `sterilization_duration` ($c_i$) and `shift_config` ($H$, $[A, B]$), setting `effective_release_time = request.finish_time` and `discarded_infeasible_count = 0`. *(The separate Naive Static Reduction comparator $f'_i = f_i + c_i$ with horizon filtering is paired with the adapted solvers for counterexample comparison.)*
- **Steps**:
  1. Validate caller sequence without mutating it (raising `InvalidSchedulingInputError` on invalid sequence or `None`).
  2. Unless `is_presorted=True`, sort surgeries by $(f_i, s_i)$ in $\mathcal{O}(n \log n)$. When `is_presorted=True`, validate non-decreasing $(f_i, s_i)$ order in a single $\mathcal{O}(n)$ pass (raising `InvalidSchedulingInputError` if unsorted).
  3. Maintain `last_finish = -1`.
  4. Linearly scan in $\mathcal{O}(n)$: if $s_i \ge \text{last\_finish}$, append `ProcessedSurgery(request=i, effective_release_time=f_i)` and update `last_finish = f_i`.

### 3.2. `ClassicDPScheduler` ($\mathcal{O}(n \log n)$ / $\mathcal{O}(n)$ pre-sorted)
- **Compatibility Criterion**: Pure Classic Textbook Mode over $[s_i, f_i]$ (identical to `ClassicGreedyScheduler`).
- **Steps**:
  1. Validate caller sequence without mutating it.
  2. Unless `is_presorted=True`, sort surgeries by $(f_i, s_i)$ in $\mathcal{O}(n \log n)$. When `is_presorted=True`, validate non-decreasing $(f_i, s_i)$ order in $\mathcal{O}(n)$.
  3. Compute 1-based predecessor array `p[1..n]`:
     - **Two-pointer $\mathcal{O}(n)$ mode**: If `is_presorted=True` and an optional `presorted_start_indices: Sequence[int] | None = None` permutation ordered by `start_time` is supplied (validated in $\mathcal{O}(n)$), OR if `start_time` is already monotonically non-decreasing across the finish-sorted sequence (checked in $\mathcal{O}(n)$), compute predecessors via monotonic two-pointer scan in $\mathcal{O}(n)$.
     - **Binary-search $\mathcal{O}(n \log n)$ mode**: Otherwise, build finish-time array $F = [f_1, \dots, f_n]$ and compute $p(i)$ using `bisect.bisect_right(F, s_i, lo=0, hi=i)` in $\mathcal{O}(n \log n)$.
  4. Fill `dp[0..n]` iteratively where `dp[i] = max(dp[i - 1], 1 + dp[p[i]])` in $\mathcal{O}(n)$.
  5. Reconstruct optimal subset iteratively by backtracking from $i = n$ to $1$ in $\mathcal{O}(n)$.

---

## 4. Authorial Adapted Solvers, Naive Comparator, Oracle & Benchmark

Both adapted algorithms share pure preprocessing helpers in `src/domain/preprocessing.py` running in $\mathcal{O}(n)$ time:

### 4.1. Preprocessing: Feasibility Filter, Effective Release & Naive Reduction ($\mathcal{O}(n)$)
- **`is_actively_feasible(surgery, shift_config)`**: returns `True` unconditionally when `shift_config is None`; otherwise enforces $f_i \le H$ and, when `shift_window = [A, B]` exists, enforces $f_i \le A$ or $s_i \ge B$.
- **`compute_effective_release_time(surgery, shift_config)`**: computes $e_i = f_i + c_i$, returning $B$ if `shift_config` defines `[A, B]` with $f_i \le A$ and $A < e_i < B$, and $e_i$ otherwise.
- **`preprocess_feasible_surgeries(surgeries, shift_config=None)`**: validates inputs and returns `(feasible_processed_surgeries, discarded_infeasible_count)` in $\mathcal{O}(n)$.
- **`preprocess_naive_static_reduction(surgeries, shift_config=None)`** and **`NaiveReductionScheduler`** (`src/schedulers/naive_reduction.py`): apply the flawed static transformation $f'_i = f_i + c_i$ against active constraints $H$ and $[A, B]$ to demonstrate non-reducibility in `SC-02` and `SC-03`.

### 4.2. `AdaptedGreedyScheduler` ($\mathcal{O}(n \log n)$ / $\mathcal{O}(n)$ pre-sorted)
1. Preprocess feasible surgeries and compute $r_i$ in $\mathcal{O}(n)$. When `shift_config=None`, $H$ and $[A, B]$ filtering is skipped (`discarded_infeasible_count = 0`) while biological cooldown release times $r_i = f_i + c_i$ remain enforced.
2. Unless `is_presorted=True`, sort feasible items by `(effective_release_time, request.finish_time, request.start_time)` in $\mathcal{O}(n \log n)$ (or validate non-decreasing order in $\mathcal{O}(n)$ when `is_presorted=True`).
3. Initialize `last_release = -1` and `selected = []`.
4. Linear scan in $\mathcal{O}(n)$ via `select_greedy_processed_surgeries`:
   - For each item, if `item.request.start_time >= last_release`:
     - Append `item` to `selected`.
     - Update `last_release = item.effective_release_time`.
5. Return `SchedulingResult`.

### 4.3. `AdaptedDPScheduler` ($\mathcal{O}(n \log n)$ / $\mathcal{O}(n)$ pre-sorted)
1. Preprocess feasible surgeries and compute $r_i$ in $\mathcal{O}(n)$ (skipping $H$/$[A, B]$ filtering when `shift_config=None`, while enforcing $r_i = f_i + c_i$).
2. Passing `presorted_start_indices` when `is_presorted=False` or when any input item was filtered out by `shift_config` (`discarded_infeasible_count > 0`) MUST raise `InvalidSchedulingInputError`.
3. Unless `is_presorted=True`, sort $n'$ feasible items by `(effective_release_time, request.finish_time, request.start_time)` in $\mathcal{O}(n \log n)$.
4. Delegate predecessor resolution, DP table evaluation, and backtracking to the shared kernel `solve_interval_dp`:
   - **Standard / binary-search mode**: computes $p(i+1) = \text{bisect\_right}(R, s_i, 0, i)$ in $\mathcal{O}(n \log n)$.
   - **Pre-sorted two-pointer mode**: when `is_presorted=True` with validated `presorted_start_indices` (or monotonic `start_time`), computes predecessors via two pointers in $\mathcal{O}(n)$.
   - Fills `dp[0..n']` and reconstructs the optimal subset iteratively via backtracking.
5. Return `SchedulingResult`.

### 4.4. `BruteForceOracleScheduler` & Empirical Benchmark (`src/schedulers/brute_force_oracle.py`, `src/benchmark/runner.py`)
- **`BruteForceOracleScheduler`**: implements `IntervalSchedulerProtocol` using exact branch-and-bound enumeration with `MAX_ORACLE_INPUT_SIZE = 20`, raising `InvalidSchedulingInputError` immediately when `len(surgeries) > 20`.
- **`src/benchmark/runner.py`**: exposes `BenchmarkPoint`, `generate_synthetic_surgeries`, `run_scaling_benchmark`, and `format_benchmark_table` using strictly Python 3.12+ Standard Library modules (`collections.abc`, `dataclasses`, `math`, `random`, `statistics`).

### 4.5. Visual Simulation & Presentation Layer (`src/ui/`, `src/main.py`)
- **`src/ui/scenarios_catalog.py`**: canonical single source of truth for deterministic presets `SC-01`..`SC-05` (`ScenarioPreset`, `get_scenario_presets`, `get_scenario_by_id`) reused by `tests/fixtures/scenarios.py`.
- **`src/ui/tracer.py`**: decoupled multi-stage execution tracer (`TracePhase`, `SurgeryVisualStatus`, `SimulationStep`, `SimulationTrace`, `trace_scheduler_execution`) and 5-algorithm side-by-side comparator (`AlgorithmComparisonEntry`, `run_comparative_arena`). Production `IntervalSchedulerProtocol.schedule()` implementations in `src/schedulers/` remain strictly uninstrumented (`[RNF-02]`), and `trace_scheduler_execution` cross-validates final parity against `schedule()`.
- **`src/ui/server.py`**: loopback `ThreadingHTTPServer` (`127.0.0.1` default) serving zero-dependency Vanilla HTML5/CSS3/ES6 JS + SVG static assets (`src/ui/static/`) and validated JSON API routes.
- **`src/main.py`**: unified CLI and browser launcher entrypoint supporting `--host`, `--port`, `--no-browser`, `--scenario`, and `--benchmark`.

---

## 5. Planned Repository Layout

```text
escalonamento-intervalos-paa/
├── .agents/
│   └── rules/AGENTS.md
├── openspec/
│   ├── specs/
│   ├── changes/
│   └── archive/
├── src/
│   ├── __init__.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── exceptions.py          # InvalidSchedulingInputError
│   │   ├── models.py              # Enums, ShiftConfig, SurgeryRequest, SchedulingResult
│   │   └── preprocessing.py       # Feasibility validation & Effective Release Time (r_i)
│   ├── schedulers/
│   │   ├── __init__.py
│   │   ├── protocol.py            # IntervalSchedulerProtocol & shared DP/ordering kernel
│   │   ├── classic_greedy.py      # ClassicGreedyScheduler (Baseline)
│   │   ├── classic_dp.py          # ClassicDPScheduler (Baseline)
│   │   ├── naive_reduction.py     # NaiveReductionScheduler (f'_i = f_i + c_i comparator)
│   │   ├── adapted_greedy.py      # AdaptedGreedyScheduler (Authorial)
│   │   ├── adapted_dp.py          # AdaptedDPScheduler (Authorial)
│   │   └── brute_force_oracle.py  # Exact oracle (n <= 20) for test cross-validation
│   ├── benchmark/
│   │   ├── __init__.py
│   │   └── runner.py              # Comparative runtime & optimality benchmark runner
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── scenarios_catalog.py   # Canonical SC-01..SC-05 presets shared with tests
│   │   ├── tracer.py              # Multi-stage step tracer & 5-algorithm comparator
│   │   ├── server.py              # Loopback ThreadingHTTPServer & validated JSON API
│   │   └── static/
│   │       ├── index.html         # 3-tab presentation UI + live HH:MM input editor
│   │       ├── styles.css         # High-contrast classroom-projector stylesheet
│   │       └── app.js             # Step playback, SVG Gantt, arrays & benchmark charts
│   └── main.py                    # CLI & local web server entrypoint
├── tests/
│   ├── fixtures/
│   │   └── scenarios.py           # Re-exported deterministic hospital scenarios
│   ├── test_domain_models.py
│   ├── test_preprocessing.py
│   ├── test_classic_schedulers.py
│   ├── test_adapted_schedulers.py
│   ├── test_oracle_and_comparison.py
│   ├── test_ui_tracer_and_server.py
│   └── test_documentation_integrity.py
├── docs/
│   ├── relatorio-testes-benchmark-complexidade.md
│   └── guia-revisao-arquitetura-e-apresentacao.md
├── pyproject.toml
├── README.md
└── LICENSE
```

---

## Functional Requirements

- **[RF-01]** All domain models MUST enforce validation invariants at creation time and remain immutable.
- **[RF-02]** All four primary schedulers (`ClassicGreedyScheduler`, `ClassicDPScheduler`, `AdaptedGreedyScheduler`, `AdaptedDPScheduler`) MUST implement `IntervalSchedulerProtocol`.
- **[RF-03]** Both DP implementations MUST reconstruct and return the exact optimal subset of surgeries (not only the numeric cardinality).
- **[RF-04]** Both Classic and Adapted solvers MUST measure and expose execution timing (`elapsed_ns`) excluding external I/O.
- **[RF-05]** All Python identifiers (packages, modules, classes, methods, attributes, variables) MUST be written in English (`en-US`), while all comments and docstrings MUST be written in Brazilian Portuguese (`pt-BR`).

## Non-Functional Requirements

- **[RNF-01]** Core scheduling modules (`src/domain/`, `src/schedulers/`) MUST have zero third-party runtime dependencies, relying strictly on Python 3.12+ Standard Library modules.
- **[RNF-02]** Each scheduler module MUST adhere to Single Responsibility and remain concise, readable, and strictly typed.
- **[RNF-03]** Brute-force oracle execution MUST reject any input with $n > 20$ to prevent exponential execution lockups.

## Out of Scope

- Parallelizing or multi-threading scheduler runs across CPU cores.
- Persisting schedules to an external relational or NoSQL database.

## Revision History

| Version | Date | Author | Summary |
|---------|------|--------|---------|
| 1.0.0 | 2026-11-15 | `@allysson-assuncao` | Initial specification of domain models, SOLID contracts, classic baselines, adapted algorithms, and package layout |
| 1.1.0 | 2026-11-15 | `@allysson-assuncao` | Consolidated `implement-classic-baseline`: finalized Pure Classic Textbook Mode, $\mathcal{O}(n)$ pre-sorted validation, and `presorted_start_indices` two-pointer DP predecessor contract |
| 1.2.0 | 2026-11-18 | `@allysson-assuncao` | Consolidated `implement-adapted-surgical-scheduling`: acyclic domain preprocessing, shared DP kernel, `NaiveReductionScheduler`, `AdaptedGreedyScheduler`, `AdaptedDPScheduler`, `BruteForceOracleScheduler` ($n \le 20$), and `src/benchmark/runner.py` |
| 1.3.0 | 2026-11-18 | `@allysson-assuncao` | Consolidated `implement-visual-simulation-interface`: added zero-dependency `src/ui/` (`scenarios_catalog.py`, `tracer.py`, `server.py`, `static/`), `src/main.py`, and `tests/test_ui_tracer_and_server.py` while keeping `src/schedulers/` uninstrumented |
| 1.4.0 | 2026-11-19 | `@allysson-assuncao` | Consolidated `deliver-project-documentation-and-presentation-guide`: added `docs/relatorio-testes-benchmark-complexidade.md`, `docs/guia-revisao-arquitetura-e-apresentacao.md`, root `README.md`, and `tests/test_documentation_integrity.py` |
