# Delta Spec: `testing-benchmark-and-visual-interface`

> **Change ID:** `simplify-core-and-presentation-ui`
> **Target Canonical Spec:** `openspec/specs/testing-benchmark-and-visual-interface.md`
> **Change Type:** Modify

## Architectural Updates

### 1. Didactic Pre-Configured Scenarios (`CASE-01`..`CASE-04`)
- Replace the 8 `SC-*` presets in `src/ui/scenarios_catalog.py` and `tests/fixtures/scenarios.py` with 4 clear didactic scenarios while retaining full unit/edge-case test coverage in `tests/`:
  - `CASE-01`: Classical Homogeneous Baseline (4 `CLEAN` surgeries, $H=18:00$, no window; all 4 solvers select 3 surgeries).
  - `CASE-02`: Impact of Sterilization $c_i$ & Closing Horizon $H$ (the canonical 3-surgery counterexample `S1/S2/S3`; Classic produces conflict `{S1, S3}` while Adapted finds optimal `{S2, S3}`).
  - `CASE-03`: Shift-Change Window $[A, B]$ (`[12:00, 13:00]` with 5 surgeries demonstrating active overlap rejection and $r_1 = B$ jump, selecting `{S1, S4, S5}`).
  - `CASE-04`: Full Mixed Hospital Shift (7 mixed surgeries demonstrating DP binary search, predecessor array `p[i]`, DP table filling, backtracking, and 4 valid selected surgeries).
- Keep edge-case unit tests (empty, singleton, all-infeasible, $r_i$ ties, validation errors) and the 180-instance randomized `BruteForceOracleScheduler` cross-validation in `tests/`.

### 2. Removal of Synthetic Empirical Benchmark Spec
- Remove Section 3 (`src/benchmark/runner.py`, `[RF-03]`, `[RNF-02]`) and `docs/relatorio-testes-benchmark-complexidade.md`, keeping asymptotic complexity verification via per-phase complexity summaries and operation counters in the UI tracer.

### 3. Lean 2-Tab Presentation Web UI (`src/ui/static/`)
- **Tab 1 — Simulador Passo a Passo**:
  - 4-algorithm selector (`adapted_greedy`, `adapted_dp`, `classic_greedy`, `classic_dp`) with no `is_presorted` toggle.
  - Top `#complexity-summary-card` displaying the selected algorithm's mathematical rules (sorting/release key and greedy/DP recurrence), $\mathcal{O}(n \log n)$ time / $\mathcal{O}(n)$ space badges, and real per-phase operation counts.
  - SVG Gantt chart, phase jump pills, clean `HH:MM (min)` variables watch, and `Ordered[i] / r_i / p[i] / DP[i]` array inspector.
- **Tab 2 — Comparativo dos 4 Algoritmos**:
  - Side-by-side table comparing the 4 algorithms (omitting raw `Tempo (ns)` noise) with physical conflict validation, plus 4 mini-Gantt SVGs sharing a single synchronized `[minT, maxT]` horizontal time axis.
- **Sidebar**:
  - Preset loader (`CASE-01`..`CASE-04`), shift constraint controls ($H$ and $[A, B]$), and live `HH:MM` surgery editor (no random instance generator).
- **Documentation & Integrity Tests**:
  - `tests/test_documentation_integrity.py` validates `README.md` and `docs/guia-revisao-arquitetura-e-apresentacao.md` line anchors and markers.
