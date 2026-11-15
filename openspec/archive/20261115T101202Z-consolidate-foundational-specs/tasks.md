# Tasks: Consolidate Foundational Specs

> **Change ID:** `consolidate-foundational-specs`
> **Linked Proposal:** [proposal.md](./proposal.md)
> **Status:** complete
>
> All tasks must be `[x]` before this change can be archived via `sdd-spec-archive`.

---

## Implementation Tasks

- [x] Initialize `.agents/` (`rules/`, `agents/`, `skills/`) and `openspec/` (`specs/`, `changes/`, `archive/`) directories
- [x] Populate `openspec/specs/sdd-stack-contract.md` with Python 3.12+ / `pytest` / `pip` + `venv` contract and `TBD` UI placeholder
- [x] Seed `openspec/specs/_template.md` from the official SDD specification template
- [x] Create `.agents/rules/AGENTS.md` enforcing language rules (`pt-BR` interaction/comments/commits, `en-US` code/specs), SOLID/Clean Code, baseline coexistence, and shift-left testing
- [x] Author canonical spec `specs/problem-definition-and-mathematical-model.md` in 100% English preserving all details from the legacy Portuguese files
- [x] Author canonical spec `specs/algorithms-and-domain-architecture.md` in 100% English defining domain entities, Classic Baseline solvers, Adapted solvers, and SOLID architecture
- [x] Author canonical spec `specs/testing-benchmark-and-visual-interface.md` in 100% English defining pre-configured scenarios, brute-force oracle, benchmarks, and visual presentation requirements
- [x] Remove legacy root draft files (`enunciado.txt`, `resumo_tema_e_viabilidade.md`, `definicao_problema_e_decisoes.md`) after confirming complete English consolidation

## Security Validation Tasks

- [x] Verify domain validation invariants and brute-force oracle upper bound ($n \le 20$) are documented in canonical specifications
- [x] Confirm no secrets, tokens, or hardcoded credentials appear in any `.agents/` or `openspec/` file

## Shift-Left Test Suite Tasks

### Happy Path
- [x] Verify `TP-01`: Run pre-implementation audit via `sdd-spec-auditor` and achieve `Approved` verdict
- [x] Verify `TP-02`: Cross-check mathematical notation ($s_i, f_i, t_i, c_i, H, A, B, r_i, p(i)$) and the 3-surgery counterexample across all three specifications

### Edge Cases & Failure Modes
- [x] Verify `TE-01`: Confirm zero `*-delta.md` files exist in `openspec/specs/` and zero Portuguese prose remains inside `openspec/`
- [x] Verify `TE-02`: Confirm `.agents/rules/AGENTS.md` has no YAML frontmatter and stays strictly under 50 lines

## Documentation Tasks

- [x] Consolidate all three canonical specs into `openspec/specs/` and archive this change under `openspec/archive/`

## Review Gate

- [x] All implementation tasks complete
- [x] All security validation tasks complete
- [x] All verification checks passing
- [x] Proposal acceptance criteria verified (run `sdd-spec-validate`)
- [x] Ready for `sdd-spec-archive`
