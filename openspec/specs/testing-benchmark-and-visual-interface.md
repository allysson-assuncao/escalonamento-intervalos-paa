---
id: "testing-benchmark-and-visual-interface"
title: "Testing, Empirical Benchmark, and Visual Interface Requirements"
version: "1.2.0"
status: "active"
owners:
  - "@allysson-assuncao"
scope:
  paths:
    - "tests/**"
    - "src/benchmark/**"
    - "src/ui/**"
resources:
  - "openspec/specs/problem-definition-and-mathematical-model.md"
  - "openspec/specs/algorithms-and-domain-architecture.md"
---

# Testing, Empirical Benchmark, and Visual Interface — Living Specification

> This is the authoritative source of truth for pre-configured test scenarios, exact oracle verification, comparative complexity benchmarking, and visual demonstration requirements for `escalonamento-intervalos-paa`.
> Update this file only after merging a completed change from `openspec/changes/`.

---

## Context & Objectives

The PAA academic assignment explicitly requires pre-configured automated test cases, empirical proof of asymptotic complexity equivalence between the Greedy and Dynamic Programming solutions, clear contrast against classical approaches, comprehensive documentation with execution instructions, and a visual interface suitable for live classroom presentation. This specification codifies all verification scenarios, oracle invariants, benchmark criteria, and visual presentation requirements prior to implementation.

---

## 1. Pre-Configured Deterministic Test Scenarios

All automated tests MUST run under `pytest` and include deterministic, human-readable pre-configured scenarios in `tests/fixtures/scenarios.py` (represented cleanly in integer minutes from `00:00`, e.g., `13:00` = `780`, `18:00` = `1080`), verified across `tests/test_preprocessing.py`, `tests/test_adapted_schedulers.py`, and `tests/test_oracle_and_comparison.py`:

- **Fixture Builders (`tests/fixtures/scenarios.py`)**:
  - `build_sc01_classic_homogeneous_surgeries()` (`SC-01`)
  - `build_sc02_counterexample_surgeries()` with `ShiftConfig(closing_horizon=1080)` (`SC-02`)
  - `build_sc03_end_of_shift_boundary()` (`SC-03`: `S_END` 17:20–17:50 + 30m vs `S_OVER` 17:30–18:01)
  - `build_sc04_shift_window_scenarios()` (`SC-04a`, `SC-04b`, `SC-04c` under `[12:00, 13:00]`)
  - `build_sc05_edge_case_scenarios()` (`SC-05`: all-infeasible set and $r_i$ tie-breaking set)

### Scenario 1 (`SC-01`): Classical Homogeneous Baseline
- **Setup**: $n \ge 5$ `CLEAN` surgeries ($c_i = 0$) within $H = 18:00$ (`1080`), with `shift_window = None`.
- **Expected Behavior**:
  - `ClassicGreedyScheduler`, `ClassicDPScheduler`, `AdaptedGreedyScheduler`, and `AdaptedDPScheduler` all return identical maximum cardinality.
  - Validates backward compatibility of adapted algorithms with textbook Interval Scheduling.

### Scenario 2 (`SC-02`): Canonical 3-Surgery Non-Reducibility Counterexample
- **Setup**: Closing horizon $H = 18:00$ (`1080`), `shift_window = None`:
  - `S1` (`CONTAMINATED`): `13:00–14:00` (`780–840`), $c_1 = 120$ (`2h`) $\implies r_1 = 16:00$ (`960`).
  - `S2` (`CLEAN`): `13:30–15:00` (`810–900`), $c_2 = 0$ $\implies r_2 = 15:00$ (`900`).
  - `S3` (`CONTAMINATED`): `15:00–17:45` (`900–1065`), $c_3 = 60$ (`1h`) $\implies r_3 = 18:45$ (`1125`).
- **Expected Behavior**:
  - `AdaptedGreedyScheduler` and `AdaptedDPScheduler` both select **`{S2, S3}` (`total_selected == 2`)**.
  - `ClassicGreedyScheduler` (pure $f_i$ ordering without $c_i$ awareness, or checked for valid sterilization compatibility) fails to find `{S2, S3}` (picking `S1` first because $f_1 = 14:00 < f_2 = 15:00$).
  - Naive static reduction ($f'_i = f_i + c_i \le H$) falsely discards `S3` ($18:45 > 18:00$) and yields only `1` surgery.

### Scenario 3 (`SC-03`): End-of-Shift Passive Sterilization Boundary
- **Setup**: Closing horizon $H = 18:00$ (`1080`), `shift_window = None`. Contaminated surgery `S_end` runs `17:20–17:50` (`1040–1070`) with $c = 30$ (`e = 18:20 > H`).
- **Expected Behavior**:
  - `S_end` is accepted as active-feasible ($17:50 \le 18:00$) and scheduled if compatible with prior surgeries.
  - A surgery ending at `18:01` (`1081 > H`) is discarded as active-infeasible.

### Scenario 4 (`SC-04`): Shift-Change Window $[A, B]$ Interactions
- **Setup**: Closing horizon $H = 18:00$ (`1080`), `shift_window = [12:00, 13:00]` (`[720, 780]`).
- **Subcases**:
  - `SC-04a` (Active overlap rejected): Surgeries `11:30–12:15` and `12:30–13:30` are discarded; boundary surgeries `11:00–12:00` ($f_i = A$) and `13:00–14:00` ($s_i = B$) are accepted.
  - `SC-04b` (Parallel sterilization absorbed by shift break): Contaminated surgery `11:15–11:45` with $c = 30$ ($e_i = 12:15 \in (12:00, 13:00)$) yields $r_i = 13:00$ (`780`), allowing a next surgery starting at `13:00`.
  - `SC-04c` (Sterilization overflowing shift break): Contaminated surgery `11:15–11:45` with $c = 90$ ($e_i = 13:15 > 13:00$) yields $r_i = 13:15$ (`795`), blocking a surgery at `13:00–14:00` while allowing `13:15–14:15`.

### Scenario 5 (`SC-05`): Edge Cases & Domain Validation Failures
- Empty surgery list `[]` $\implies$ empty result (`total_selected == 0`).
- Single valid surgery $\implies$ `total_selected == 1`.
- All surgeries invalid against $H$ or $[A, B]$ $\implies$ empty result with accurate `discarded_infeasible_count`.
- Ties on $r_i$ (e.g., two surgeries with identical $r_i$ and distinct $f_i$) $\implies$ deterministic tie-breaking preserving optimal cardinality.
- Malformed inputs ($s_i \ge f_i$, `CLEAN` with $c_i > 0$, `CONTAMINATED` with $c_i = 0$, $A \ge B$, $B > H$) $\implies$ raises `InvalidSchedulingInputError`.

---

## 2. Exact Brute-Force Oracle & Cross-Validation

To empirically verify correctness across thousands of randomized edge configurations without relying solely on manual cases:

1. **Brute-Force Exact Oracle (`BruteForceOracleScheduler`)**:
   - Enumerates feasible subsets (branch-and-bound over $n \le 20$) respecting active feasibility against $H$ and $[A, B]$ and compatibility $s_j \ge r_i$.
   - **Hard Safety Guard**: Raises `InvalidSchedulingInputError` (a `ValueError` subclass) immediately if `len(surgeries) > 20` to prevent exponential $\mathcal{O}(2^n)$ hangs.
2. **Randomized Property Cross-Validation (`tests/test_oracle_and_comparison.py`)**:
   - Generates deterministic-seed (`random.Random(seed)`) random hospital instances across 180 trials with $n \in [0, 16]$, mixed `CLEAN` and `CONTAMINATED` ratios, varied $c_i$, and varied $[A, B]$ / $H$.
   - Asserts across hundreds/thousands of instances:
     $$\text{len}(\text{AdaptedGreedy}) == \text{len}(\text{AdaptedDP}) == \text{len}(\text{BruteForceOracle})$$
   - Validates that every returned schedule strictly satisfies all physical non-overlap, sterilization, shift-window, and horizon constraints.

---

## 3. Empirical Runtime & Complexity Benchmark Specification

The benchmark harness (`src/benchmark/runner.py`) exposes `BenchmarkPoint`, `generate_synthetic_surgeries`, `run_scaling_benchmark`, and `format_benchmark_table` to evaluate all four production algorithms (`ClassicGreedyScheduler`, `ClassicDPScheduler`, `AdaptedGreedyScheduler`, `AdaptedDPScheduler`) across scaling input sizes (e.g., $n \in \{100, 500, 1000, 2500, 5000, 10000\}$):

1. **Metrics Collected per Run**:
   - Input size $n$ and number of feasible intervals $n'$.
   - Median / mean execution time (`elapsed_ns` / `ms`) over multiple repetitions.
   - Normalized ratio $T(n) / (n \log_2 n)$ (and $T(n) / n$ in pre-sorted mode) to empirically confirm the $\Theta(n \log n)$ and $\Theta(n)$ asymptotic growth curves.
   - Selected count comparison (`Classic` vs. `Adapted`) on realistic mixed-contamination instances.
2. **Comparison Deliverables**:
   - Structured tabular summary suitable for terminal/UI display and optional chart generation for the class presentation.

---

## 4. Visual Interface & Presentation Architecture (Zero-Dependency Local Web + Native SVG)

The visual interface uses a **Zero-Dependency Local Web Application** (`http.server.ThreadingHTTPServer` bound to `127.0.0.1:8765` by default + Vanilla HTML5/CSS3/ES6 JS and interactive native SVG in `src/ui/static/`), supporting live classroom demonstration of **correctness**, **real-time data structures**, and **asymptotic complexity**:

1. **Interactive 3-Tab Presentation Layout + Live `HH:MM` Editor**:
   - **Tab 1 — Step-by-Step Debugger**: Full multi-stage micro-step playback (`PREPROCESSING`, `SORTING`, `PREDECESSORS` with `bisect` `lo/mid/hi` or two-pointer `release_ptr`, `SELECTION_OR_DP` with `last_release` or `dp[i]` recurrence, `BACKTRACKING`, and `RESULT`), phase-jump shortcuts (`phase_offsets`), custom SVG Gantt (solid `[s_i, f_i]` active bars, hatched sterilization extensions `[f_i, f_i + c_i]`, `[A, B]` shaded band, `H` cutoff, `r_i` tick), Real-Time Variable Watch, and Array Inspector (`Ordered[]`, `p[]`, `DP[]`).
   - **Tab 2 — Comparative Arena**: Side-by-side execution across all 5 schedulers (`ClassicGreedyScheduler`, `ClassicDPScheduler`, `NaiveReductionScheduler`, `AdaptedGreedyScheduler`, `AdaptedDPScheduler`) highlighting `SC-02` non-reducibility and flagging physical sterilization, shift-window, and horizon violations on classic schedules.
   - **Tab 3 — Complexity & Benchmark Lab**: Interactive benchmark runner and native SVG curves plotting $T(n)$, $T(n)/(n \log_2 n)$, and $T(n)/n$ across growing $n$ (plus `is_presorted` toggle) alongside formatted tabular metrics.
   - **Live Input Editor**: Preset selector (`SC-01`..`SC-05b`), automatic `HH:MM` masked time inputs (`attachHhmmInputMask`, `parseHhmmToMinutes`) enforcing `start_time < finish_time` and valid $[A, B]$ / $H$ bounds, add/delete surgery controls, and seeded synthetic generation.
2. **Local Loopback HTTP JSON API & Defensive Resource Guards (`src/ui/server.py`)**:
   - Endpoints: `GET /api/scenarios`, `POST /api/trace`, `POST /api/compare`, `POST /api/generate`, `POST /api/benchmark`.
   - Security bounds: `MAX_REQUEST_BODY_BYTES = 262_144` (with bounded TCP drain on Windows before HTTP 413), `MAX_TRACE_INPUT_SIZE = 200`, `MAX_GENERATE_SIZE = 5000`, `MAX_BENCHMARK_SIZE = 10000`, `MAX_BENCHMARK_REPETITIONS = 20`, static directory-traversal protection confined to `src/ui/static/`, and XSS-safe DOM rendering (`textContent`).
3. **Automated UI, Tracer & CLI Verification (`tests/test_ui_tracer_and_server.py`)**:
   - Validates tracer parity across all 5 schedulers and `SC-01`..`SC-05`, DP micro-steps, comparative conflict detection, live HTTP endpoints, resource/security guards, `HH:MM` validation, and `src/main.py` headless CLI (`--scenario`, `--benchmark`).
4. **Documentation (`README.md`)**:
   - Complete setup instructions (`venv`, running `pytest`, launching benchmarks, launching the visual interface) and academic project documentation (delivered in dedicated subsequent documentation change).

---

## Functional Requirements

- **[RF-01]** Automated tests MUST cover all pre-configured scenarios (`SC-01` through `SC-05`).
- **[RF-02]** Randomized cross-validation MUST assert `AdaptedGreedy == AdaptedDP == BruteForceOracle` for $n \le 20$ using reproducible RNG seeds.
- **[RF-03]** The benchmark runner MUST record execution time, cardinality, and normalized complexity ratios across all four algorithms for scaling $n$.
- **[RF-04]** The visual interface MUST render active surgical bars, dashed/hatched sterilization extensions, shift window $[A, B]$, horizon $H$, and algorithm comparisons.

## Non-Functional Requirements

- **[RNF-01]** Full `pytest` suite (including seeded oracle cross-validation) MUST execute deterministically and complete in under 5 seconds on standard hardware.
- **[RNF-02]** Benchmark measurements MUST use `time.perf_counter_ns()` and isolate algorithm execution from input generation and UI rendering overhead.

## Out of Scope

- Cloud hosting or multi-user authentication for the local presentation UI.
- External third-party Python or JavaScript UI frameworks.

## Revision History

| Version | Date | Author | Summary |
|---------|------|--------|---------|
| 1.0.0 | 2026-11-15 | `@allysson-assuncao` | Initial specification of pre-configured scenarios, brute-force oracle, complexity benchmark, and presentation UI guidelines |
| 1.1.0 | 2026-11-18 | `@allysson-assuncao` | Consolidated `implement-adapted-surgical-scheduling`: codified `SC-01`..`SC-05` fixture builders, `test_preprocessing.py` / `test_adapted_schedulers.py` / `test_oracle_and_comparison.py`, and `BenchmarkPoint` / `run_scaling_benchmark` contracts |
| 1.2.0 | 2026-11-18 | `@allysson-assuncao` | Consolidated `implement-visual-simulation-interface`: finalized Section 4 with zero-dependency local web server + native SVG architecture, 3-tab UI + live `HH:MM` editor, loopback HTTP JSON API contracts, resource/security guards, and `tests/test_ui_tracer_and_server.py` |
