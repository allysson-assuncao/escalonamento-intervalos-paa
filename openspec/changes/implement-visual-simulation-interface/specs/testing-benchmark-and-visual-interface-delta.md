# Delta Spec: `testing-benchmark-and-visual-interface`

> **Change ID:** `implement-visual-simulation-interface`
> **Target Canonical Spec:** `openspec/specs/testing-benchmark-and-visual-interface.md`
> **Change Type:** Modify

## Architectural Updates

### 1. Finalized Visual Interface Technology Stack (Section 4)
- Replaces `UI Framework TBD` with a **Zero-Dependency Local Web Application**:
  - Backend: Python 3.12+ Standard Library (`http.server.ThreadingHTTPServer`, `json`, `webbrowser`) in `src/ui/server.py` and `src/main.py`, bound to `127.0.0.1:8765` by default.
  - Frontend: Vanilla HTML5, CSS3, ES6 JavaScript, and native interactive SVG in `src/ui/static/`. Zero third-party Python or JS runtime dependencies.

### 2. Multi-Stage Step-by-Step Simulation & 3-Tab Layout
- **Tab 1 — Step-by-Step Debugger**: Full micro-step playback (`⏮`, `◀`, `▶`, `⏯ Auto-Play`, scrubber, and phase-jump shortcuts via `phase_offsets`) across `PREPROCESSING`, `SORTING`, `PREDECESSORS` (`bisect` `lo/mid/hi` or two-pointer `release_ptr`), `SELECTION_OR_DP` (`last_release` or `dp[i]` recurrence), `BACKTRACKING`, and `RESULT`, synchronized with custom SVG Gantt, Real-Time Variable Watch, and Array Inspector (`Ordered[]`, `p[]`, `DP[]`).
- **Tab 2 — Comparative Arena**: Side-by-side execution of all 5 schedulers (`ClassicGreedy`, `ClassicDP`, `NaiveReduction`, `AdaptedGreedy`, `AdaptedDP`) highlighting `SC-02` non-reducibility and flagging physical sterilization/shift violations on classic schedules.
- **Tab 3 — Empirical Complexity Lab**: Interactive benchmark runner and SVG charts plotting $T(n)$, $T(n)/(n \log_2 n)$, and $T(n)/n$ across growing $n$ (plus `is_presorted` mode).
- **Live Scenario Editor**: Preset loading (`SC-01`..`SC-05`), live editing/addition of surgeries and shift parameters ($H$, $[A, B]$), and seeded synthetic workload generation.

### 3. Local HTTP JSON API Contract & Resource Guards
- Endpoints: `GET /api/scenarios`, `POST /api/trace`, `POST /api/compare`, `POST /api/generate`, `POST /api/benchmark`.
- Defensive caps: `MAX_REQUEST_BODY_BYTES = 262_144`, `MAX_TRACE_INPUT_SIZE = 200`, `MAX_GENERATE_SIZE = 5000`, `MAX_BENCHMARK_SIZE = 10000`, `MAX_BENCHMARK_REPETITIONS = 20`, plus directory traversal protection on static files and safe DOM text rendering (`textContent`).

### 4. Automated Verification (`tests/test_ui_tracer_and_server.py`)
- Verifies tracer parity across all 5 schedulers and `SC-01`..`SC-05`, DP micro-step correctness, comparative conflict detection, live HTTP API routes, input/resource bounds, path traversal rejection, and `src/main.py` headless CLI execution.
