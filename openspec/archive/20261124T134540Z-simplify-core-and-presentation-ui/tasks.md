# Tasks: Simplify Core and Presentation UI

> **Change ID:** `simplify-core-and-presentation-ui`
> **Linked Proposal:** [proposal.md](./proposal.md)
> **Status:** completed
>
> All tasks must be `[x]` before this change can be archived via `sdd-spec-archive`.

---

## Implementation Tasks

- [x] Remove `src/schedulers/naive_reduction.py`, `src/benchmark/` (`__init__.py`, `runner.py`), and `docs/relatorio-testes-benchmark-complexidade.md`.
- [x] Simplify `src/domain/preprocessing.py` and `src/domain/__init__.py` by removing naive static-reduction functions (`_is_naive_interval_feasible`, `preprocess_naive_validated_surgeries`, `preprocess_naive_static_reduction`).
- [x] Simplify `src/schedulers/protocol.py` and all scheduler classes (`ClassicGreedyScheduler`, `ClassicDPScheduler`, `AdaptedGreedyScheduler`, `AdaptedDPScheduler`, `BruteForceOracleScheduler`, `src/schedulers/__init__.py`) to remove `is_presorted`, `presorted_start_indices`, `validate_presorted_start_indices`, and the two-pointer DP predecessor branch, standardizing on clean $\mathcal{O}(n \log n)$ sorting and `bisect_right`.
- [x] Clean up `src/main.py` by removing `--benchmark`, `--sizes`, `--repetitions`, `--seed`, `--presorted`, `_run_benchmark_cli`, and `naive_reduction`.
- [x] Consolidate `src/ui/scenarios_catalog.py` into the 4 didactic scenarios (`CASE-01`..`CASE-04`).
- [x] Update `src/ui/tracer.py` to support only the 4 core algorithms, remove `is_presorted` / two-pointer tracing, add `complexity_summary`, format variables with clean Portuguese/math labels and `HH:MM (min)` timestamps, and expose `last_release_minutes` on `SimulationStep`.
- [x] Update `src/ui/server.py` and `src/ui/__init__.py` to remove `/api/generate` and `/api/benchmark` while preserving `/api/scenarios`, `/api/trace`, `/api/compare`, and strict DoS/validation guards.
- [x] Simplify `src/ui/static/index.html`, `styles.css`, and `app.js` to the 2-tab UI (`1. Simulador Passo a Passo` with `#complexity-summary-card`, `2. Comparativo dos 4 Algoritmos` with shared-axis aligned mini-Gantts), removing the random generator, `#presorted-checkbox`, and benchmark tab.

## Test Tasks

- [x] Update `tests/fixtures/scenarios.py`, `tests/test_preprocessing.py`, `tests/test_classic_schedulers.py`, `tests/test_adapted_schedulers.py`, and `tests/test_oracle_and_comparison.py` to reflect the 4 schedulers, `CASE-01`..`CASE-04`, and removal of `src/benchmark/` and `is_presorted`, while preserving 180-instance oracle cross-validation.
- [x] Update `tests/test_ui_tracer_and_server.py` to verify `CASE-01`..`CASE-04`, `complexity_summary`, `HH:MM (min)` variable labels, 404 on `/api/generate` and `/api/benchmark`, and XSS/security invariants.
- [x] Update `tests/test_documentation_integrity.py` to validate the updated `README.md` and `docs/guia-revisao-arquitetura-e-apresentacao.md`.

## Documentation Tasks

- [x] Update `README.md` and `docs/guia-revisao-arquitetura-e-apresentacao.md` to reflect the simplified 4-algorithm, 4-scenario, 2-tab system with verified `#Lxx-Lyy` line anchors.
- [x] Sync `openspec/specs/sdd-stack-contract.md` via `specs/sdd-stack-contract-delta.md` upon `sdd-spec-archive` to remove `src/benchmark/`, `POST /api/generate`, and `POST /api/benchmark`.

## Review Gate

- [x] All implementation tasks complete
- [x] All tests passing (`pytest -v`)
- [x] Proposal acceptance criteria verified
- [x] Ready for `sdd-spec-archive`
