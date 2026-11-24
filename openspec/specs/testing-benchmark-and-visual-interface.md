---
id: "testing-benchmark-and-visual-interface"
title: "Testing and Visual Interface Requirements"
version: "1.4.0"
status: "active"
owners:
  - "@allysson-assuncao"
scope:
  paths:
    - "tests/**"
    - "src/ui/**"
resources:
  - "openspec/specs/problem-definition-and-mathematical-model.md"
  - "openspec/specs/algorithms-and-domain-architecture.md"
---

# Testing and Visual Interface — Living Specification

> This is the authoritative source of truth for pre-configured didactic test scenarios, exact oracle verification, and visual demonstration requirements for `escalonamento-intervalos-paa`.
> Update this file only after merging a completed change from `openspec/changes/`.

---

## Context & Objectives

The PAA academic assignment requires pre-configured automated test cases, clear verification of equivalence and contrast against classical approaches, concise documentation with execution instructions, and an intuitive visual interface suitable for live classroom presentation. This specification codifies the didactic verification scenarios, oracle invariants, and 2-tab visual presentation architecture.

---

## 1. Pre-Configured Deterministic Test Scenarios (`CASE-01`..`CASE-04`)

All automated tests MUST run under `pytest` and include deterministic, human-readable scenarios shared via `src/ui/scenarios_catalog.py` and `tests/fixtures/scenarios.py` (represented in integer minutes from `00:00`, e.g., `13:00` = `780`, `18:00` = `1080`), verified across `tests/test_preprocessing.py`, `tests/test_classic_schedulers.py`, `tests/test_adapted_schedulers.py`, and `tests/test_ui_tracer_and_server.py`:

- **Fixture Builders (`tests/fixtures/scenarios.py`)**:
  - `build_case01_classic_baseline()` (`CASE-01`)
  - `build_case02_sterilization_and_horizon()` (`CASE-02`)
  - `build_case03_shift_window()` (`CASE-03`)
  - `build_case04_full_mixed_shift()` (`CASE-04`)

### Scenario 1 (`CASE-01`): Classical Homogeneous Baseline
- **Setup**: 4 `CLEAN` surgeries ($c_i = 0$) within $H = 18:00$ (`1080`), `shift_window = None`.
- **Expected Behavior**:
  - `ClassicGreedyScheduler`, `ClassicDPScheduler`, `AdaptedGreedyScheduler`, and `AdaptedDPScheduler` all select `{S1, S3, S4}` (`total_selected == 3`).
  - Demonstrates backward compatibility with textbook Interval Scheduling.

### Scenario 2 (`CASE-02`): Impact of Sterilization ($c_i$) and Horizon ($H$)
- **Setup**: Closing horizon $H = 18:00$ (`1080`), `shift_window = None`:
  - `S1` (`CONTAMINATED`): `13:00–14:00` (`780–840`), $c_1 = 120$ (`2h`) $\implies r_1 = 16:00$ (`960`).
  - `S2` (`CLEAN`): `13:30–15:00` (`810–900`), $c_2 = 0$ $\implies r_2 = 15:00$ (`900`).
  - `S3` (`CONTAMINATED`): `15:00–17:45` (`900–1065`), $c_3 = 60$ (`1h`) $\implies r_3 = 18:45$ (`1125 > H`).
- **Expected Behavior**:
  - `AdaptedGreedyScheduler` and `AdaptedDPScheduler` both select **`{S2, S3}` (`total_selected == 2`)** cleanly.
  - `ClassicGreedyScheduler` and `ClassicDPScheduler` select `{S1, S3}`, triggering a physical conflict because `S3` starts at `15:00` before `S1` finishes sterilization at `16:00`.

### Scenario 3 (`CASE-03`): Shift-Change Window $[A, B]$
- **Setup**: Closing horizon $H = 18:00$ (`1080`), `shift_window = [12:00, 13:00]` (`[720, 780]`):
  - `S1` (`10:00–11:30`, `CONTAMINATED`, $c_1 = 60 \implies e_1 = 12:30 \in (A, B) \implies r_1 = B = 13:00$).
  - `S2` (`11:30–12:30`, `CLEAN`) and `S3` (`12:30–14:00`, `CLEAN`) overlap $[12:00, 13:00)$ actively and are discarded.
  - `S4` (`13:00–15:00`, `CONTAMINATED`, $c_4 = 30 \implies r_4 = 15:30$) and `S5` (`15:30–17:30`, `CLEAN`).
- **Expected Behavior**:
  - `AdaptedGreedyScheduler` and `AdaptedDPScheduler` discard `2` surgeries (`S2`, `S3`) and select **`{S1, S4, S5}` (`total_selected == 3`)**.

### Scenario 4 (`CASE-04`): Full Mixed Hospital Shift (7 Mixed Surgeries)
- **Setup**: 7 mixed surgeries (`S1`..`S7`) under $H = 18:00$ and `[12:00, 13:00]`.
- **Expected Behavior**:
  - `AdaptedGreedyScheduler` and `AdaptedDPScheduler` discard `S4` (`1` discarded) and select **`{S2, S3, S6, S7}` (`total_selected == 4`)**, showcasing DP binary search (`[lo, mid, hi]`), `p[i]`, `DP[i]`, and backtracking.

### Edge Cases & Domain Validation Coverage (`tests/`)
- Unit tests additionally verify empty input, single surgery, all-infeasible inputs, end-of-shift passive sterilization boundary (`17:20–17:50 + 30m` vs `17:30–18:01`), $r_i$ ties, and malformed domain inputs raising `InvalidSchedulingInputError`.

---

## 2. Exact Brute-Force Oracle & Cross-Validation

1. **Brute-Force Exact Oracle (`BruteForceOracleScheduler`)**:
   - Enumerates feasible subsets (branch-and-bound over $n \le 20$) respecting active feasibility against $H$ and $[A, B]$ and compatibility $s_j \ge r_i$.
   - **Hard Safety Guard**: Raises `InvalidSchedulingInputError` immediately if `len(surgeries) > 20`.
2. **Randomized Property Cross-Validation (`tests/test_oracle_and_comparison.py`)**:
   - Generates deterministic-seed (`random.Random(20261118)`) random hospital instances across 180 trials with $n \in [0, 16]$, mixed `CLEAN` and `CONTAMINATED` ratios, varied $c_i$, and varied $[A, B]$ / $H$.
   - Asserts $\text{len}(\text{AdaptedGreedy}) == \text{len}(\text{AdaptedDP}) == \text{len}(\text{BruteForceOracle})$ and checks physical non-overlap and shift invariants on every schedule.

---

## 3. Visual Interface & Presentation Architecture (Zero-Dependency Local Web + Native SVG)

The visual interface uses a **Zero-Dependency Local Web Application** (`http.server.ThreadingHTTPServer` bound to `127.0.0.1:8765` by default + Vanilla HTML5/CSS3/ES6 JS and interactive native SVG in `src/ui/static/`):

1. **Interactive 2-Tab Presentation Layout + Live `HH:MM` Editor**:
   - **Tab 1 — Step-by-Step Simulator**:
     - Selector across the 4 primary algorithms (`adapted_greedy`, `adapted_dp`, `classic_greedy`, `classic_dp`).
     - Collapsible `#complexity-summary-card` showing sorting/decision mathematical rules, overall $\mathcal{O}(n \log n)$ time / $\mathcal{O}(n)$ space pills, and per-phase asymptotic complexity + real operation counters (`complexity_summary`).
     - Multi-stage micro-step playback (`PREPROCESSING`, `SORTING`, `PREDECESSORS` with binary search `lo/mid/hi`, `SELECTION_OR_DP`, `BACKTRACKING`, `RESULT`), phase-jump pills, custom SVG Gantt (solid `[s_i, f_i]` active bars, hatched sterilization `[f_i, f_i + c_i]`, `[A, B]` shaded band, `H` cutoff, `r_i` tick, and `last_release_minutes` line), clean `HH:MM (min)` variable cards, and Array Inspector (`Ordered[i]`, `r_i`, `p[i]`, `DP[i]`).
   - **Tab 2 — Side-by-Side Comparison of the 4 Algorithms**:
     - Summary table comparing cardinality, discarded count, chosen schedule, asymptotic complexity, and physical conflict audit across all 4 schedulers, plus 4 mini-Gantt SVGs sharing a synchronized horizontal `[minT, maxT]` scale (`computeGanttDomain`).
   - **Sidebar Input Editor**: Preset selector (`CASE-01`..`CASE-04`), shift constraint toggles ($H$, $[A, B]$), and automatic `HH:MM` masked manual surgery form (`attachHhmmInputMask`, `parseHhmmToMinutes`) enforcing `startTime < finishTime`.
2. **Local Loopback HTTP JSON API & Defensive Resource Guards (`src/ui/server.py`)**:
   - Endpoints: `GET /api/scenarios`, `POST /api/trace`, `POST /api/compare` (removed `/api/generate` and `/api/benchmark` return HTTP 404).
   - Security bounds: `MAX_REQUEST_BODY_BYTES = 262_144` (with bounded TCP drain on Windows before HTTP 413), `MAX_TRACE_INPUT_SIZE = 200`, `MAX_COMPARE_INPUT_SIZE = 500`, static directory-traversal protection confined to `src/ui/static/`, and XSS-safe DOM rendering (`textContent`, zero `innerHTML`).
3. **Automated UI, Tracer & CLI Verification (`tests/test_ui_tracer_and_server.py`)**:
   - Validates tracer parity across all 4 schedulers and `CASE-01`..`CASE-04`, `complexity_summary`, `HH:MM (min)` variables, comparative conflict detection, live HTTP endpoints, 404 on removed routes, resource/security guards, `HH:MM` validation, and `src/main.py` headless CLI (`--scenario`, `--algorithm`).
4. **Documentation & Integrity Checks (`README.md`, `docs/guia-revisao-arquitetura-e-apresentacao.md`, `tests/test_documentation_integrity.py`)**:
   - `README.md` covers problem definition, extensions ($t_i, c_i, H, [A, B]$), closed-form $r_i$, `CASE-02` counterexample, complexity comparison, setup, `pytest -v`, and CLI/Web launch.
   - `docs/guia-revisao-arquitetura-e-apresentacao.md` provides a concise 5-module study & oral defense guide with verified `#Lxx-Lyy` line anchors.

---

## Functional Requirements

- **[RF-01]** Automated tests MUST cover all didactic scenarios (`CASE-01` through `CASE-04`) and edge cases.
- **[RF-02]** Randomized cross-validation MUST assert `AdaptedGreedy == AdaptedDP == BruteForceOracle` for $n \le 20$ using reproducible RNG seeds.
- **[RF-03]** The visual interface MUST render active surgical bars, hatched sterilization extensions, shift window $[A, B]$, horizon $H$, an in-app mathematical/phase-complexity summary card, and aligned 4-algorithm comparisons.

## Non-Functional Requirements

- **[RNF-01]** Full `pytest` suite (including seeded oracle cross-validation) MUST execute deterministically and complete in under 5 seconds on standard hardware.
- **[RNF-02]** Tracer complexity summaries MUST report accurate per-phase asymptotic classes and observed instance operation counts without instrumenting `src/schedulers/`.

## Out of Scope

- Cloud hosting or multi-user authentication for the local presentation UI.
- External third-party Python or JavaScript UI frameworks.

## Revision History

| Version | Date | Author | Summary |
|---------|------|--------|---------|
| 1.0.0 | 2026-11-15 | `@allysson-assuncao` | Initial specification of pre-configured scenarios, brute-force oracle, complexity benchmark, and presentation UI guidelines |
| 1.1.0 | 2026-11-18 | `@allysson-assuncao` | Consolidated `implement-adapted-surgical-scheduling` |
| 1.2.0 | 2026-11-18 | `@allysson-assuncao` | Consolidated `implement-visual-simulation-interface` |
| 1.3.0 | 2026-11-19 | `@allysson-assuncao` | Consolidated `deliver-project-documentation-and-presentation-guide` |
| 1.4.0 | 2026-11-24 | `@allysson-assuncao` | Consolidated `simplify-core-and-presentation-ui`: consolidated scenarios to `CASE-01`..`CASE-04`, removed synthetic benchmark suite/tab and random generator, added complexity summary card and aligned shared-scale mini-Gantts |
