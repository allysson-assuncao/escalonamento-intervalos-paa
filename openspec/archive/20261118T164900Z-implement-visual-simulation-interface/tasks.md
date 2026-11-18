# Tasks: Implement Visual Simulation Interface

> **Change ID:** `implement-visual-simulation-interface`
> **Linked Proposal:** [proposal.md](./proposal.md)
> **Status:** completed
>
> All tasks must be `[x]` before this change can be archived via `sdd-spec-archive`.

---

## Implementation Tasks

### Phase 1 — Shared Scenario Catalog & Multi-Stage Execution Tracer
- [x] Create `src/ui/__init__.py` and `src/ui/scenarios_catalog.py` exposing `ScenarioPreset` and canonical `SC-01`..`SC-05` builders (`get_scenario_presets`, `get_scenario_by_id`), and align `tests/fixtures/scenarios.py` to reuse shared definitions without breaking existing fixture imports
- [x] Implement `TracePhase`, `SurgeryVisualStatus`, `SimulationStep`, `SimulationTrace`, and `trace_scheduler_execution` in `src/ui/tracer.py` supporting `ClassicGreedyScheduler`, `ClassicDPScheduler`, `NaiveReductionScheduler`, `AdaptedGreedyScheduler`, and `AdaptedDPScheduler`
- [x] Capture micro-steps across `PREPROCESSING`, `SORTING`, `PREDECESSORS` (`bisect` `lo/mid/hi` and two-pointer `release_ptr`), `SELECTION_OR_DP` (`last_release` and `dp[i]` recurrence), `BACKTRACKING`, and `RESULT`, with `phase_offsets` and `MAX_TRACE_INPUT_SIZE = 200` guard

### Phase 2 — Comparative Arena & Local Loopback HTTP Server
- [x] Implement `AlgorithmComparisonEntry` and `run_comparative_arena` in `src/ui/tracer.py` comparing all 5 algorithms side by side and reporting physical sterilization/shift conflicts on classic schedules
- [x] Implement `src/ui/server.py` with loopback `ThreadingHTTPServer` (`127.0.0.1` default), static asset handler with directory-traversal protection, and JSON API routes (`GET /api/scenarios`, `POST /api/trace`, `POST /api/compare`, `POST /api/generate`, `POST /api/benchmark`)
- [x] Enforce HTTP payload limits (`MAX_REQUEST_BODY_BYTES`), domain validation (`InvalidSchedulingInputError` -> HTTP 400), and interactive API bounds (`trace n <= 200`, `generate n <= 5000`, `benchmark n <= 10000`, `repetitions <= 20`)

### Phase 3 — 3-Tab Presentation Frontend (`src/ui/static/`)
- [x] Create `src/ui/static/index.html` and `src/ui/static/styles.css` with high-contrast classroom-projector styling, hatched/dashed sterilization visual patterns, live scenario/surgery/shift editor, and 3 navigation tabs
- [x] Implement Tab 1 in `src/ui/static/app.js`: Playback controls (`⏮`, `◀`, `▶`, `⏯ Auto-Play`, speed selector, scrubber, phase-jump buttons), interactive SVG Gantt (`[s_i, f_i]`, `[f_i, f_i + c_i]`, `[A, B]`, `H`, `r_i`), Real-Time Variable Watch, and Array Inspector (`Ordered[]`, `p[]`, `DP[]`)
- [x] Implement Tab 2 (5-Algorithm Comparative Arena with side-by-side results, conflict badges, and SVG timelines) and Tab 3 (Benchmark Lab with SVG curves for $T(n)$, $T(n)/(n \log_2 n)$, $T(n)/n$ and metrics table) in `src/ui/static/app.js`

### Phase 4 — Entrypoint `src/main.py` & Package Verification
- [x] Create `src/main.py` supporting web UI launch (`--host`, `--port`, `--no-browser`) and headless CLI modes (`--scenario`, `--benchmark`)
- [x] Write `tests/test_ui_tracer_and_server.py` covering tracer parity, DP micro-steps, comparative conflicts, HTTP endpoints, security guards, and `src/main.py` CLI
- [x] Verify all identifiers use English (`en-US`), all docstrings/comments/UI presentation labels use Brazilian Portuguese (`pt-BR`), and `src/` uses zero third-party runtime dependencies

## Security Validation Tasks

- [x] Verify `src/ui/server.py` binds to `127.0.0.1` by default, blocks path traversal outside `src/ui/static/`, and caps request body size (`MAX_REQUEST_BODY_BYTES`)
- [x] Verify interactive API guards reject `trace n > 200`, `generate n > 5000`, `benchmark max_n > 10000`, and `repetitions > 20` with HTTP 400
- [x] Verify `app.js` escapes/assigns dynamic strings (e.g., `surgery_id`) via safe DOM APIs (`textContent`) with zero raw `innerHTML` user-input interpolation, and confirm zero hardcoded secrets exist across `src/` and `tests/`

## Shift-Left Test Suite Tasks

### Happy Path
- [x] Verify `TP-01`: `trace_scheduler_execution` matches `schedule()` outputs across `SC-01`..`SC-05` for all 5 schedulers
- [x] Verify `TP-02`: `AdaptedDPScheduler` trace records `PREPROCESSING`, `SORTING`, `PREDECESSORS` (`bisect` and two-pointer), `SELECTION_OR_DP`, `BACKTRACKING`, and accurate `phase_offsets`
- [x] Verify `TP-03`: `run_comparative_arena` returns 5 entries on `SC-02` and `SC-04` and identifies classic physical sterilization/shift violations
- [x] Verify `TP-04`: `GET /` and `GET /api/scenarios` return HTTP 200 with static assets and presets `SC-01`..`SC-05`
- [x] Verify `TP-05`: `POST /api/trace` and `POST /api/compare` return HTTP 200 with structured JSON steps and comparison results
- [x] Verify `TP-06`: `POST /api/generate` and `POST /api/benchmark` return HTTP 200 with valid synthetic requests and `BenchmarkPoint` records
- [x] Verify `TP-07`: `src/main.py` headless CLI (`--scenario`, `--benchmark`) executes cleanly with exit code 0

### Edge Cases & Failure Modes
- [x] Verify `TE-01`: Tracing empty `[]` and all-infeasible `SC-05` inputs works across all 5 schedulers without index errors
- [x] Verify `TE-02`: Tracing `is_presorted=True` with unsorted inputs or mismatched `presorted_start_indices` raises `InvalidSchedulingInputError`
- [x] Verify `TE-03`: HTTP API rejects malformed JSON, invalid domain inputs, and oversized request bodies with HTTP 400/413
- [x] Verify `TE-04`: HTTP API enforces `trace n <= 200`, `generate n <= 5000`, `benchmark max_n <= 10000`, and `repetitions <= 20`
- [x] Verify `TE-05`: Path traversal attempts and unknown endpoints return HTTP 403/404 without leaking Python source files
- [x] Verify `TE-06`: Special characters / `<script>` payloads in `surgery_id` round-trip safely in JSON and UI rendering logic

## Documentation Tasks

- [x] Merge `specs/algorithms-and-domain-architecture-delta.md` into `openspec/specs/algorithms-and-domain-architecture.md` upon archive
- [x] Merge `specs/testing-benchmark-and-visual-interface-delta.md` into `openspec/specs/testing-benchmark-and-visual-interface.md` upon archive

## Review Gate

- [x] All implementation tasks complete
- [x] All security validation tasks complete
- [x] All tests passing (`C:\Python314\python.exe -m pytest -v -p no:cacheprovider`)
- [x] Proposal acceptance criteria verified
- [x] Ready for `sdd-spec-archive`
