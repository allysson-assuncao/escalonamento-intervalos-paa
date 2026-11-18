# Delta Spec: `algorithms-and-domain-architecture`

> **Change ID:** `implement-visual-simulation-interface`
> **Target Canonical Spec:** `openspec/specs/algorithms-and-domain-architecture.md`
> **Change Type:** Modify

## Architectural Updates

### 1. Visual Simulation & Presentation Layer (`src/ui/`, `src/main.py`)
- Add `src/ui/` using strictly Python 3.12+ Standard Library modules (`http.server`, `json`, `urllib.parse`, `pathlib`, `dataclasses`, `enum`, `argparse`, `webbrowser`):
  - `src/ui/scenarios_catalog.py`: Single source of truth for canonical deterministic scenarios (`SC-01`..`SC-05`) consumed by both the UI API and `tests/fixtures/scenarios.py`.
  - `src/ui/tracer.py`: Decoupled multi-stage execution tracer (`TracePhase`, `SurgeryVisualStatus`, `SimulationStep`, `SimulationTrace`, `trace_scheduler_execution`) and 5-algorithm side-by-side comparator (`AlgorithmComparisonEntry`, `run_comparative_arena`).
  - `src/ui/server.py`: Loopback `ThreadingHTTPServer` (`127.0.0.1` default) serving `src/ui/static/` assets (`index.html`, `styles.css`, `app.js`) and validated JSON API endpoints.
- Add `src/main.py` as the unified CLI/UI entrypoint supporting web server launch (`--host`, `--port`, `--no-browser`) and headless CLI execution (`--scenario`, `--benchmark`).

### 2. Timing Isolation Invariant (`[RNF-02]`)
- Production `IntervalSchedulerProtocol.schedule()` implementations in `src/schedulers/` MUST NOT be instrumented with UI tracing hooks; `src/ui/tracer.py` executes independently for step-by-step visualization and cross-validates parity against `schedule()`.
