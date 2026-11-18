# Proposal: Implement Visual Simulation Interface

> **Change ID:** `implement-visual-simulation-interface`
> **Status:** approved
> **Author:** `@allysson-assuncao`
> **Created:** 2026-11-18
> **Last Updated:** 2026-11-18

---

## Summary

This change implements the visual simulation and presentation interface (`src/ui/` and `src/main.py`) of `escalonamento-intervalos-paa` using a zero-dependency Python 3.12+ Standard Library local web server (`http.server` + `webbrowser`) paired with Vanilla HTML5/CSS3/ES6 JavaScript and native interactive SVG. It delivers a decoupled multi-stage execution tracer (`src/ui/tracer.py`), a shared canonical scenario catalog (`src/ui/scenarios_catalog.py`), a 3-tab presentation interface (Step-by-Step Debugger with SVG Gantt + Real-Time Variable Watch + Array Inspector, Side-by-Side 5-Algorithm Comparative Arena, and Empirical Complexity Benchmark Lab) with live scenario editing, CLI/headless modes in `src/main.py`, and comprehensive `pytest` verification (`tests/test_ui_tracer_and_server.py`).

## Motivation

The PAA assignment requires an intuitive visual demonstration tool capable of illustrating algorithm execution step by step, explaining data structures and changing variable values across iterations, contrasting classic baselines and naive reduction against the authorial adapted solutions (`SC-01`..`SC-05`), and displaying empirical asymptotic complexity curves ($\Theta(n \log n)$ and $\Theta(n)$). Using a local zero-dependency Stdlib web server + native SVG preserves `dependencies = []` in `pyproject.toml`, eliminates installation risks on presentation hardware, avoids frame-rerun flicker during single-step debugging, and keeps core scheduler `elapsed_ns` timings strictly isolated from tracing and UI overhead (`[RNF-02]`).

## Scope

### In Scope
- **Phase 1 — Scenario Catalog & Decoupled Execution Tracer**:
  - Implement `src/ui/scenarios_catalog.py` exposing `ScenarioPreset` and canonical `SC-01`..`SC-05` builders accessible to both `src/ui/` and `tests/fixtures/scenarios.py` (with `tests/fixtures/scenarios.py` reusing `src/ui/scenarios_catalog.py` or keeping full backward-compatible signatures without duplicating scenario definitions).
  - Implement `src/ui/tracer.py` defining `TracePhase`, `SurgeryVisualStatus`, `SimulationStep`, `SimulationTrace`, `AlgorithmComparisonEntry`, and `trace_scheduler_execution(...)` supporting all five algorithms (`ClassicGreedyScheduler`, `ClassicDPScheduler`, `NaiveReductionScheduler`, `AdaptedGreedyScheduler`, `AdaptedDPScheduler`) in general and pre-sorted modes.
  - Record complete multi-stage micro-steps (`PREPROCESSING`, `SORTING`, `PREDECESSORS` with binary search `lo`/`mid`/`hi` or two-pointer `release_ptr`, `SELECTION_OR_DP` with `last_release` or `DP[i]` recurrence, `BACKTRACKING` jumps, and `RESULT`) alongside `phase_offsets` for instant phase jumping.
- **Phase 2 — Comparative Arena & Local Loopback HTTP API Server**:
  - Implement `run_comparative_arena(...)` in `src/ui/tracer.py` evaluating all five schedulers side by side and detecting physical sterilization, shift-window $[A, B]$, and closing-horizon $H$ violations on classic schedules.
  - Implement `src/ui/server.py` using `http.server.ThreadingHTTPServer` bound to `127.0.0.1` by default, serving static frontend assets and JSON API endpoints (`GET /api/scenarios`, `POST /api/trace`, `POST /api/compare`, `POST /api/generate`, `POST /api/benchmark`) with strict payload size, schema, and interactive computation bounds.
- **Phase 3 — 3-Tab Presentation Frontend (`src/ui/static/`)**:
  - Implement `src/ui/static/index.html`, `src/ui/static/styles.css`, and `src/ui/static/app.js` with:
    1. **Tab 1 (Simulador Passo a Passo)**: Playback controls (`⏮`, `◀`, `▶`, `⏯ Auto-Play`, scrubber slider, phase-jump buttons), custom SVG surgical Gantt (active `[s_i, f_i]` bars, hatched/dashed sterilization `[f_i, f_i + c_i]`, `[A, B]` shaded band, `H` vertical line, `r_i` markers), Real-Time Variable Watch, and Interactive Array Inspector (`Ordered[]`, `p[1..n']`, `DP[0..n']`).
    2. **Tab 2 (Arena Comparativa)**: Side-by-side results and mini-Gantt/timeline comparison across all 5 algorithms highlighting `SC-02` non-reducibility and conflict badges on classic schedules.
    3. **Tab 3 (Benchmark e Complexidade)**: Configurable benchmark runner UI + interactive SVG charts plotting $T(n)$, $T(n)/(n \log_2 n)$, and $T(n)/n$ across growing $n$ (and `is_presorted` toggle) plus tabular metrics.
    4. **Editor Ao Vivo de Entrada**: Preset selector (`SC-01`..`SC-05`), live add/edit/delete of `SurgeryRequest` items, live editing of $H$ and $[A, B]$, and seeded synthetic generator integration.
- **Phase 4 — Entrypoint `src/main.py` & Automated Test Suite**:
  - Implement `src/main.py` with `argparse` CLI flags (`--host`, `--port`, `--no-browser`, `--scenario`, `--benchmark`) supporting both interactive web UI launch and headless CLI summaries/benchmarks.
  - Create `tests/test_ui_tracer_and_server.py` verifying tracer parity against `schedule()`, DP micro-step fidelity, comparative conflict detection, HTTP endpoints, security/bound guards, XSS escaping helpers/contracts, and `src/main.py` CLI modes.

### Out of Scope
- Comprehensive academic documentation and execution guides in `README.md` (deferred to Change #5).
- Third-party Python packages (Streamlit, NiceGUI, FastAPI, Flask, Plotly) or external JavaScript CDN dependencies.
- Multi-room scheduling, user authentication, or remote network/cloud hosting.

## Proposed Solution

### Approach
1. **Strict Separation of Tracing and Timing (`src/ui/tracer.py`)**: Production solvers in `src/schedulers/` remain completely untouched so `elapsed_ns` benchmarking (`[RNF-02]`) incurs zero instrumentation overhead. `trace_scheduler_execution` mirrors each algorithm's deterministic steps into immutable `SimulationStep` snapshots (`@dataclass(frozen=True)`) and verifies at completion that traced selections match `scheduler.schedule()`.
2. **Loopback Stdlib HTTP Server + JSON API (`src/ui/server.py`)**: A lightweight `ThreadingHTTPServer` serves static assets from `src/ui/static/` and exposes strictly validated JSON endpoints. All incoming JSON payloads are converted into domain entities (`SurgeryRequest`, `ShiftConfig`, `ShiftWindow`) so every domain invariant is enforced automatically via `InvalidSchedulingInputError` (mapped to HTTP 400).
3. **Native SVG & Safe DOM Rendering (`src/ui/static/app.js`)**: Custom SVG generation renders hatched sterilization patterns, `[A, B]` interdiction bands, `H` cutoff lines, `r_i` release ticks, synchronized array/pointer highlights, and multi-series complexity curves without external chart libraries. Dynamic text (such as user-edited `surgery_id`) is rendered exclusively via `textContent` / safe DOM APIs to prevent XSS.

### Impacted Files
| File | Change Type | Notes |
|------|-------------|-------|
| `src/ui/__init__.py` | Create | Public exports for `src/ui/` package |
| `src/ui/scenarios_catalog.py` | Create | Shared canonical `SC-01`..`SC-05` presets & metadata |
| `src/ui/tracer.py` | Create | Multi-stage execution tracer (`SimulationTrace`, `SimulationStep`) & comparative arena |
| `src/ui/server.py` | Create | Loopback `ThreadingHTTPServer`, static asset serving & validated JSON API |
| `src/ui/static/index.html` | Create | 3-tab presentation UI shell + live input editor |
| `src/ui/static/styles.css` | Create | Responsive classroom-projector theme, hatching styles & array highlights |
| `src/ui/static/app.js` | Create | Playback engine, SVG Gantt, Variable Watch, Array Inspector, Arena & Complexity SVG charts |
| `src/main.py` | Create | CLI & browser launcher entrypoint (`--host`, `--port`, `--no-browser`, `--scenario`, `--benchmark`) |
| `tests/fixtures/scenarios.py` | Modify | Reuse/align scenario builders with `src/ui/scenarios_catalog.py` without breaking existing imports |
| `tests/test_ui_tracer_and_server.py` | Create | Unit & integration tests for tracer parity, comparative arena, HTTP API, security guards, and `src/main.py` |

### Data Model Changes (if applicable)
No changes to core `src/domain/models.py` entities. Introduces immutable presentation/tracing models in `src/ui/tracer.py` (`TracePhase`, `SurgeryVisualStatus`, `SimulationStep`, `SimulationTrace`, `AlgorithmComparisonEntry`) and `ScenarioPreset` in `src/ui/scenarios_catalog.py`.

## Acceptance Criteria

- [x] **Given** any canonical scenario (`SC-01`..`SC-05`) or valid custom input, **When** `trace_scheduler_execution` runs for each of the 5 schedulers (`ClassicGreedyScheduler`, `ClassicDPScheduler`, `NaiveReductionScheduler`, `AdaptedGreedyScheduler`, `AdaptedDPScheduler`), **Then** it emits immutable multi-stage steps with `phase_offsets` (`PREPROCESSING`, `SORTING`, `PREDECESSORS`, `SELECTION_OR_DP`, `BACKTRACKING`, `RESULT`) and its final selected surgery IDs match `scheduler.schedule()` 100% without modifying `src/schedulers/*.py`.
- [x] **Given** `SC-02` traced under `AdaptedDPScheduler` (both general `bisect` mode and `is_presorted=True` two-pointer mode), **When** inspecting `SimulationTrace.steps`, **Then** every predecessor micro-step (`lo`/`mid`/`hi` or `release_ptr`), every DP recurrence transition (`dp[i] = max(dp[i-1], 1 + dp[p[i]])`), and every backtracking step is captured accurately, reconstructing `{"S2", "S3"}`.
- [x] **Given** `SC-02` evaluated by `run_comparative_arena` (or `POST /api/compare`), **When** comparing all 5 algorithms, **Then** `AdaptedGreedyScheduler` and `AdaptedDPScheduler` yield `total_selected == 2`, `NaiveReductionScheduler` yields `1` (`discarded_infeasible_count == 1`), and classic schedule conflict inspection flags any physical sterilization/shift violation when evaluated against real OR rules.
- [x] **Given** the local HTTP server (`src/ui/server.py`) started on loopback `127.0.0.1` (ephemeral port in tests), **When** clients request `GET /`, `GET /api/scenarios`, `POST /api/trace`, `POST /api/compare`, `POST /api/generate`, and `POST /api/benchmark`, **Then** valid requests return HTTP 200 with structured JSON/HTML, oversized bodies return HTTP 413, and malformed JSON, invalid domain values, or out-of-bounds trace/benchmark parameters (`trace n > 200`, `generate n > 5000`, `benchmark max_n > 10000`, `repetitions > 20`) return HTTP 400.
- [x] **Given** `src/main.py` invoked via CLI in headless modes (`--scenario SC-02`, `--benchmark --sizes 50 100 --repetitions 2`), **When** executed as a subprocess or module (`python -m src.main`), **Then** it exits with code 0 and prints structured comparison/benchmark output without requiring a browser.

## Defensive Security & Validation Considerations

### Input Validation
- `src/ui/server.py` enforces `MAX_REQUEST_BODY_BYTES = 262_144` (returning HTTP 413/400 on overflow), validates `Content-Type`/JSON decoding, validates strict integer/string/enum types via domain constructors (`SurgeryRequest`, `ShiftConfig`, `ShiftWindow`, `is_strict_int`), and rejects unknown algorithm keys or malformed parameters with HTTP 400.
- `app.js` uses `textContent` and explicit SVG DOM attribute methods (never `innerHTML` with untrusted/user-supplied strings like `surgery_id`) to eliminate DOM-based XSS vectors.

### Secret Isolation
- N/A — strictly offline local Python Standard Library application with zero credentials, API keys, or external network requests.

### Authorization & Authentication Impact
- N/A — single-user local classroom presentation tool bound exclusively to loopback (`127.0.0.1`) by default (`openspec/specs/testing-benchmark-and-visual-interface.md`).

### Other Security Risks
- **Local Resource Exhaustion (DoS) via HTTP API**: Enforces hard caps on interactive endpoints: `MAX_TRACE_INPUT_SIZE = 200` on `POST /api/trace`, `MAX_GENERATE_SIZE = 5000` on `POST /api/generate`, `MAX_BENCHMARK_SIZE = 10000` and `MAX_BENCHMARK_REPETITIONS = 20` on `POST /api/benchmark`, plus static asset path normalization blocking directory traversal outside `src/ui/static/`.

## Testing Strategy & Shift-Left Plan

### Happy Path Tests
| Test ID | Scenario | Test Type | Expected Result |
|---------|----------|-----------|-----------------|
| TP-01 | `trace_scheduler_execution` parity against `schedule()` across `SC-01`..`SC-05` for all 5 schedulers | Unit / Comparative | Final traced selections and discarded counts match `schedule()` 100% |
| TP-02 | `AdaptedDPScheduler` trace emits `PREPROCESSING`, `SORTING`, `PREDECESSORS` (`lo/mid/hi` and two-pointer), `SELECTION_OR_DP`, and `BACKTRACKING` steps with valid `phase_offsets` | Unit | All phases present, `phase_offsets` point to exact start step of each phase |
| TP-03 | `run_comparative_arena` on `SC-02` and `SC-04a/b/c` | Unit | Returns 5 entries with `AdaptedGreedy == AdaptedDP == 2` on `SC-02` and flags classic physical conflicts |
| TP-04 | `GET /` and `GET /api/scenarios` on live loopback test server (`port=0`) | Integration | HTTP 200 serving `index.html`, `styles.css`, `app.js`, and canonical presets `SC-01`..`SC-05` |
| TP-05 | `POST /api/trace` and `POST /api/compare` with `SC-02` and custom edited surgeries | Integration | HTTP 200 returning valid step payloads, Gantt data, and 5-algorithm comparison |
| TP-06 | `POST /api/generate` and `POST /api/benchmark` with small sizes (`sizes=[50, 100], repetitions=2`) | Integration | HTTP 200 returning synthetic requests and finite `BenchmarkPoint` JSON records |
| TP-07 | `src/main.py` CLI headless execution (`--scenario SC-02`, `--benchmark --sizes 50 100 --repetitions 2`) | Integration | Exits 0 and outputs formatted scenario comparison and benchmark table |

### Edge Case & Failure Mode Tests
| Test ID | Scenario | Test Type | Expected Result |
|---------|----------|-----------|-----------------|
| TE-01 | Tracing empty `[]` and all-infeasible `SC-05` datasets across all 5 schedulers | Unit | Clean trace with `total_selected == 0`, accurate `discarded_infeasible_count`, no index errors |
| TE-02 | Tracing `is_presorted=True` with unsorted input or invalid `presorted_start_indices` | Unit | Raises `InvalidSchedulingInputError` matching production scheduler contract |
| TE-03 | `POST /api/trace`, `POST /api/compare`, `POST /api/benchmark` with malformed JSON, invalid domain constraints ($s_i \ge f_i$), or oversized body | Integration / Security | Returns HTTP 400 (or 413) with structured JSON error, server remains healthy |
| TE-04 | API resource guard limits (`trace n > 200`, `generate n > 5000`, `benchmark size > 10000` or `repetitions > 20`) | Integration / Security | Returns HTTP 400 immediately without executing unbounded loops |
| TE-05 | Path traversal attempt (`GET /static/../server.py`) and unknown routes (`GET /api/unknown`) | Integration / Security | Returns HTTP 404/403 without exposing Python source files |
| TE-06 | Frontend XSS sanity check & JSON serialization safety with `<script>` in `surgery_id` | Unit / Integration | `surgery_id` preserved literally in JSON and `app.js` avoids `innerHTML` interpolation |

### Test Commands
- **Run full suite:** `C:\Python314\python.exe -m pytest -v -p no:cacheprovider`
- **Secret & third-party import check:** `python -c` AST stdlib verification over `src/` + grep secret scan over `src/` and `tests/`

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Drift between `src/schedulers/*.py` and `src/ui/tracer.py` execution logic | Med | High | Assert exact equivalence in `tests/test_ui_tracer_and_server.py` across `SC-01`..`SC-05` and randomized instances |
| Port `8765` conflict during classroom live launch | Med | Med | Support `--port` CLI flag in `src/main.py` and automatic helpful error or fallback message if port is busy |
| Large $n$ step-trace payload freezing browser DOM | Low | High | Enforce `MAX_TRACE_INPUT_SIZE = 200` in tracer/API while allowing $n$ up to `10000` in Tab 3 Benchmark |

## Specification Changes & Delta Stubs

### `specs/algorithms-and-domain-architecture-delta.md`
- **Target Canonical Spec:** `openspec/specs/algorithms-and-domain-architecture.md`
- **Summary of Updates:** Documents `src/ui/` package structure (`scenarios_catalog.py`, `tracer.py`, `server.py`, `static/`), `src/main.py` CLI/UI entrypoint, and strict isolation of `schedule()` timing from tracing.

### `specs/testing-benchmark-and-visual-interface-delta.md`
- **Target Canonical Spec:** `openspec/specs/testing-benchmark-and-visual-interface.md`
- **Summary of Updates:** Finalizes Section 4 (Visual Interface Stack & Architecture) replacing `TBD` with Zero-Dependency Local Stdlib Web + Native SVG, defines the 3-tab UI + live editor, local HTTP JSON API endpoints, security bounds, and `tests/test_ui_tracer_and_server.py`.

## References

- `openspec/specs/sdd-stack-contract.md`
- `openspec/specs/problem-definition-and-mathematical-model.md`
- `openspec/specs/algorithms-and-domain-architecture.md`
- `openspec/specs/testing-benchmark-and-visual-interface.md`
