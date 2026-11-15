# Tasks: Implement Classic Baseline

> **Change ID:** `implement-classic-baseline`
> **Linked Proposal:** [proposal.md](./proposal.md)
> **Status:** complete
>
> All tasks must be `[x]` before this change can be archived via `sdd-spec-archive`.

---

## Implementation Tasks

- [x] Create `.gitignore` and `pyproject.toml` with Python 3.12+ metadata and `pytest` configuration
- [x] Create package initializers (`src/__init__.py`, `src/domain/__init__.py`, `src/schedulers/__init__.py`, `tests/__init__.py`, `tests/fixtures/__init__.py`)
- [x] Implement `InvalidSchedulingInputError` in `src/domain/exceptions.py`
- [x] Implement immutable domain dataclasses (`SurgeryType`, `ShiftWindow`, `ShiftConfig`, `SurgeryRequest`, `ProcessedSurgery`, `SchedulingResult`) with `__post_init__` validation in `src/domain/models.py`
- [x] Implement `IntervalSchedulerProtocol` in `src/schedulers/protocol.py`
- [x] Implement `ClassicGreedyScheduler` in `src/schedulers/classic_greedy.py` ($\mathcal{O}(n \log n)$ general, $\mathcal{O}(n)$ pre-sorted, Pure Classic Textbook Mode)
- [x] Implement `ClassicDPScheduler` in `src/schedulers/classic_dp.py` ($\mathcal{O}(n \log n)$ with `bisect_right`, $\mathcal{O}(n)$ two-pointer pre-sorted mode, iterative DP table + backtracking)

## Security Validation Tasks

- [x] Verify all domain validation invariants raise `InvalidSchedulingInputError` and reject `None` inputs
- [x] Verify schedulers do not mutate caller-supplied sequences and use iterative loops without unbounded recursion
- [x] Confirm zero hardcoded secrets, tokens, or external network dependencies across `src/` and `tests/`

## Shift-Left Test Suite Tasks

### Happy Path
- [x] Create `tests/fixtures/scenarios.py` with pre-configured `SC-01` classical dataset and boundary fixtures
- [x] Write `TP-01` in `tests/test_domain_models.py`: valid model construction and frozen immutability
- [x] Write `TP-02` in `tests/test_classic_schedulers.py`: `ClassicGreedyScheduler` == `ClassicDPScheduler` optimal cardinality and non-overlap on `SC-01`
- [x] Write `TP-03` in `tests/test_classic_schedulers.py`: `is_presorted=True` (including monotonic start and `presorted_start_indices`) matches `is_presorted=False`
- [x] Write `TP-04` in `tests/test_classic_schedulers.py`: Pure Classic Textbook Mode ignores `sterilization_duration` and `shift_config`

### Edge Cases & Failure Modes
- [x] Write `TE-01` in `tests/test_domain_models.py`: invalid `SurgeryRequest`, `ShiftWindow`, and `ShiftConfig` raise `InvalidSchedulingInputError`
- [x] Write `TE-02` in `tests/test_classic_schedulers.py`: empty list, single surgery, and fully overlapping intervals
- [x] Write `TE-03` in `tests/test_classic_schedulers.py`: touching interval boundaries ($s_j == f_i$) and finish-time ties
- [x] Write `TE-04` in `tests/test_classic_schedulers.py`: unsorted sequence with `is_presorted=True` raises `InvalidSchedulingInputError`
- [x] Write `TE-05` in `tests/test_classic_schedulers.py`: caller list non-mutation and `None` input error handling

## Documentation Tasks

- [x] Ensure all identifiers are in English (`en-US`) and all docstrings and inline comments are in Brazilian Portuguese (`pt-BR`)
- [x] Merge `specs/algorithms-and-domain-architecture-delta.md` into `openspec/specs/algorithms-and-domain-architecture.md` upon archive

## Review Gate

- [x] All implementation tasks complete
- [x] All security validation tasks complete
- [x] All tests passing (`pytest -v`)
- [x] Proposal acceptance criteria verified (run `sdd-spec-validate`)
- [x] Ready for `sdd-spec-archive`
