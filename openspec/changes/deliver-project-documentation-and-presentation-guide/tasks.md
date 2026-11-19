# Tasks: Deliver Project Documentation and Presentation Guide

> **Change ID:** `deliver-project-documentation-and-presentation-guide`
> **Linked Proposal:** [proposal.md](./proposal.md)
> **Status:** in-progress
>
> All tasks must be `[x]` before this change can be archived via `sdd-spec-archive`.

---

## Implementation Tasks

### Phase 1 — Root `README.md`
- [x] Write `README.md` in `pt-BR` explaining the academic PAA problem, classical vs. authorial operating-room extensions ($t_i$, $c_i$, $H$, $[A, B]$), closed-form $r_i$ formula, `SC-02` counterexample, repository layout, setup (`venv`), `pytest` commands, headless CLI usage (`--scenario`, `--benchmark`), local Web UI launch, and links to `docs/`

### Phase 2 — Empirical Test, Benchmark & Complexity Report
- [x] Run real benchmarks (`n = 100, 500, 1000, 2500, 5000, 10000` in general $\mathcal{O}(n \log n)$ and pre-sorted $\mathcal{O}(n)$ modes) and `pytest -v` to capture observed metrics
- [x] Write `docs/relatorio-testes-benchmark-complexidade.md` in `pt-BR` containing observed tables, normalized ratios $T(n)/(n \log_2 n)$ and $T(n)/n$, Mermaid `xychart-beta` plots, `SC-01`..`SC-05b` scenario analysis, 180-instance `BruteForceOracleScheduler` summary, and reproduction commands

### Phase 3 — 5-Module Architecture & Presentation Study Guide
- [x] Map exact `#Lxx-Lyy` line intervals across `src/domain/`, `src/schedulers/`, `src/benchmark/`, `src/ui/`, and `src/main.py`
- [x] Write `docs/guia-revisao-arquitetura-e-apresentacao.md` in `pt-BR` covering all 5 modules: (1) Architecture & SOLID with Mermaid diagrams; (2) Code-by-Code dissection with clickable `#Lxx-Lyy` links; (3) Tracer & SVG UI internals; (4) Live 3-Tab Presentation Walkthrough; (5) Examining-Board Defense FAQ

### Phase 4 — Automated Documentation Integrity Verification
- [x] Implement `tests/test_documentation_integrity.py` verifying file existence, required sections, balanced Markdown code fences, relative file link resolution, `#Lxx-Lyy` line bounds, symbol presence, and absence of machine-specific absolute paths
- [x] Run full `pytest` suite confirming all existing 63 tests and new documentation integrity tests pass within `[RNF-01]` (< 5s)

## Security Validation Tasks

- [x] Verify `tests/test_documentation_integrity.py` confines all checked relative paths within repository root (`is_relative_to`)
- [x] Confirm zero hardcoded secrets, API keys, or absolute local machine paths (`C:\Users\...`, `file:///`) exist in `README.md` or `docs/*.md`

## Shift-Left Test Suite Tasks

### Happy Path
- [x] Verify `TP-01`: `README.md`, `docs/relatorio-testes-benchmark-complexidade.md`, and `docs/guia-revisao-arquitetura-e-apresentacao.md` exist and contain all required sections
- [x] Verify `TP-02`: All relative Markdown links across `README.md` and `docs/*.md` resolve to existing files
- [x] Verify `TP-03`: All `#L<line>` / `#L<start>-L<end>` anchors fall within `[1, total_lines]` and match cited symbols
- [x] Verify `TP-04`: Full `pytest` suite completes cleanly in under 5 seconds

### Edge Cases & Failure Modes
- [x] Verify `TE-01`: Integrity helper rejects inverted ranges (`#L50-L10`), out-of-bounds line numbers, and missing files
- [x] Verify `TE-02`: No absolute host paths or secret tokens exist in `README.md` or `docs/*.md`
- [x] Verify `TE-03`: All Markdown fenced code/Mermaid blocks are properly closed

## Documentation Tasks

- [ ] Merge `specs/algorithms-and-domain-architecture-delta.md` into `openspec/specs/algorithms-and-domain-architecture.md` upon archive
- [ ] Merge `specs/testing-benchmark-and-visual-interface-delta.md` into `openspec/specs/testing-benchmark-and-visual-interface.md` upon archive

## Review Gate

- [x] All implementation tasks complete
- [x] All security validation tasks complete
- [x] All tests passing (`C:\Python314\python.exe -m pytest -v -p no:cacheprovider`)
- [x] Proposal acceptance criteria verified
- [ ] Ready for `sdd-spec-archive`
