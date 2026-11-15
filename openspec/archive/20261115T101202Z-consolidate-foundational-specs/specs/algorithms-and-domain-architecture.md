---
id: "algorithms-and-domain-architecture"
title: "Algorithms and Domain Architecture — Classic vs. Adapted Solvers"
version: "1.0.0"
status: "active"
owners:
  - "@allysson-assuncao"
scope:
  paths:
    - "src/**"
resources:
  - "openspec/specs/sdd-stack-contract.md"
  - "openspec/specs/problem-definition-and-mathematical-model.md"
---

# Algorithms and Domain Architecture — Living Specification

> This is the authoritative source of truth for domain data structures, input validation invariants, solver contracts, algorithmic steps for all four schedulers (Classic Greedy, Classic DP, Adapted Greedy, Adapted DP), and the Python modular architecture.
> Update this file only after merging a completed change from `openspec/changes/`.

---

## Context & Objectives

To uphold SOLID principles, Clean Code, and side-by-side comparability between textbook baselines and authorial adaptations, the codebase separates immutable domain modeling, shift/interval validation, scheduling strategies, and empirical benchmarking into distinct, single-responsibility Python 3.12+ modules relying solely on the Python Standard Library for core algorithms.

---

## 1. Domain Data Models & Validation Invariants

All core data structures MUST be immutable (`@dataclass(frozen=True)`) and typed with strict Python type annotations.

### 1.1. Enumerations & Value Objects
- **`SurgeryType(Enum)`**:
  - `CLEAN = "CLEAN"`
  - `CONTAMINATED = "CONTAMINATED"`
- **`ShiftWindow`**:
  - `start: int` ($A$, in integer time units such as minutes from day start)
  - `end: int` ($B$)
  - **Invariant**: $0 \le A < B$.
- **`ShiftConfig`**:
  - `closing_horizon: int` ($H$)
  - `shift_window: ShiftWindow | None = None` ($[A, B]$)
  - **Invariants**:
    - $H > 0$.
    - If `shift_window is not None`: $0 \le A < B \le H$.
- **`SurgeryRequest`**:
  - `surgery_id: str` (non-empty unique/traceable identifier)
  - `start_time: int` ($s_i$)
  - `finish_time: int` ($f_i$)
  - `surgery_type: SurgeryType = SurgeryType.CLEAN` ($t_i$)
  - `sterilization_duration: int = 0` ($c_i$)
  - **Invariants**:
    - `surgery_id.strip() != ""`
    - $0 \le s_i < f_i$
    - $c_i \ge 0$
    - If $t_i == \text{CLEAN}$, then $c_i == 0$ (enforced on construction)
    - If $t_i == \text{CONTAMINATED}$, then $c_i > 0$ (enforced on construction)
- **`ProcessedSurgery`**:
  - `request: SurgeryRequest`
  - `effective_release_time: int` ($r_i$)
- **`SchedulingResult`**:
  - `algorithm_name: str`
  - `selected_surgeries: tuple[ProcessedSurgery, ...]` (chronologically ordered)
  - `total_selected: int`
  - `discarded_infeasible_count: int`
  - `elapsed_ns: int` (high-resolution execution timing via `time.perf_counter_ns()`)

### 1.2. Defensive Input Validation
- Invalid structural inputs (e.g., $s_i \ge f_i$, negative timestamps, `CLEAN` surgery with $c_i > 0$, `CONTAMINATED` surgery with $c_i \le 0$, or `ShiftWindow` outside $[0, H]$) MUST raise a dedicated domain exception (`InvalidSchedulingInputError(ValueError)`).
- Validation MUST happen explicitly at construction/entry boundaries without mutating caller-owned collections.

---

## 2. Unified Strategy Contract (Dependency Inversion)

All schedulers MUST implement a shared Python `Protocol` so benchmarking harnesses, comparative tests, and the visual interface depend only on the abstraction:

```python
class IntervalSchedulerProtocol(Protocol):
    @property
    def name(self) -> str: ...

    def schedule(
        self,
        surgeries: Sequence[SurgeryRequest],
        shift_config: ShiftConfig | None = None,
        *,
        is_presorted: bool = False,
    ) -> SchedulingResult: ...
```

---

## 3. Baseline Classic Solvers (Retained for Comparison)

Both classic algorithms serve as permanent comparative baselines reflecting standard textbook behavior before authorial adaptation.

### 3.1. `ClassicGreedyScheduler` ($\mathcal{O}(n \log n)$ / $\mathcal{O}(n)$ pre-sorted)
- **Compatibility Criterion**: Standard interval overlap only ($s_j \ge f_i$); ignores biological contamination ($c_i$) and shift-change rules, or operates on `[s_i, f_i]` directly (with optional horizon filter $f_i \le H$ only when comparing classic boundary handling—explicitly documented as ignoring sterilization/shift rules or documented as two explicit comparison modes: pure textbook classic vs. naive static reduction $f'_i = f_i + c_i$).
  - Specifically, the repository exposes:
    1. **Pure Classic Textbook Mode** (`ClassicGreedyScheduler`, `ClassicDPScheduler`): Uses strictly $[s_i, f_i]$ (respecting $f_i \le H$ if `shift_config` is supplied, without awareness of $c_i$ or passive sterilization overlap) to contrast textbook behavior directly against adapted behavior.
    2. **Naive Static Reduction Helper** (optional comparative baseline mode or helper in comparative tests): Applies $f'_i = f_i + c_i$ before invoking classical scheduling, empirically demonstrating why static reduction fails the 3-surgery end-of-shift counterexample.
- **Steps**:
  1. Unless `is_presorted=True`, sort surgeries by $(f_i, s_i)$ in $\mathcal{O}(n \log n)$.
  2. Maintain `last_finish = -1`.
  3. Linearly scan in $\mathcal{O}(n)$: if $s_i \ge \text{last\_finish}$, append surgery and update `last_finish = f_i`.

### 3.2. `ClassicDPScheduler` ($\mathcal{O}(n \log n)$ / $\mathcal{O}(n)$ pre-sorted)
- **Steps**:
  1. Unless `is_presorted=True`, sort surgeries by $(f_i, s_i)$ in $\mathcal{O}(n \log n)$.
  2. Build finish-time array $F = [f_1, \dots, f_n]$.
  3. Compute predecessor array `p[1..n]`:
     - Standard mode: For each $i$, find largest $j < i$ with $f_j \le s_i$ using `bisect.bisect_right(F, s_i, hi=i-1)` in $\mathcal{O}(n \log n)$.
     - Pre-sorted mode (`is_presorted=True` when paired with start-order indices or monotonic pointer scan): Compute `p` in $\mathcal{O}(n)$.
  4. Fill `dp[0..n]` where `dp[i] = max(dp[i - 1], 1 + dp[p[i]])` in $\mathcal{O}(n)$.
  5. Reconstruct optimal subset by backtracking from $i = n$ to $1$ in $\mathcal{O}(n)$.

---

## 4. Authorial Adapted Solvers

Both adapted algorithms share a pure preprocessing helper (`preprocess_feasible_surgeries`) running in $\mathcal{O}(n)$ time:

### 4.1. Preprocessing: Feasibility Filter & Effective Release Evaluator ($\mathcal{O}(n)$)
For each `SurgeryRequest` $i$:
1. Check active feasibility against `shift_config` (if provided):
   - Reject if $f_i > H$.
   - If `shift_window` $[A, B]$ exists, reject if active interval $[s_i, f_i)$ overlaps $[A, B)$ (i.e., reject unless $f_i \le A$ or $s_i \ge B$).
2. Compute Effective Release Time $r_i$ in $\mathcal{O}(1)$:
   - Let $e_i = f_i + c_i$.
   - If `shift_window` $[A, B]$ exists and $f_i \le A$ and $A < e_i < B$, set $r_i = B$; otherwise set $r_i = e_i$.
3. Wrap in `ProcessedSurgery(request=i, effective_release_time=r_i)`.

### 4.2. `AdaptedGreedyScheduler` ($\mathcal{O}(n \log n)$ / $\mathcal{O}(n)$ pre-sorted)
1. Preprocess feasible surgeries and compute $r_i$ in $\mathcal{O}(n)$.
2. Unless `is_presorted=True`, sort feasible items by `(effective_release_time, request.finish_time, request.start_time)` in $\mathcal{O}(n \log n)$.
3. Initialize `last_release = -1` and `selected = []`.
4. Linear scan in $\mathcal{O}(n)$:
   - For each item, if `item.request.start_time >= last_release`:
     - Append `item` to `selected`.
     - Update `last_release = item.effective_release_time`.
5. Return `SchedulingResult`.

### 4.3. `AdaptedDPScheduler` ($\mathcal{O}(n \log n)$ / $\mathcal{O}(n)$ pre-sorted)
1. Preprocess feasible surgeries and compute $r_i$ in $\mathcal{O}(n)$.
2. Unless `is_presorted=True`, sort $n'$ feasible items by `(effective_release_time, request.finish_time, request.start_time)` in $\mathcal{O}(n \log n)$.
3. Build release-time array $R = [r_1, \dots, r_{n'}]$.
4. Compute predecessor indices `p[0..n'-1]` (1-based DP offset `dp[0..n']`):
   - **Standard mode (`is_presorted=False`)**: For each $i \in \{0, \dots, n'-1\}$, compute `count_compatible = bisect.bisect_right(R, s_i, lo=0, hi=i)` in $\mathcal{O}(\log n')$, giving $p(i+1) = \text{count\_compatible}$ in $\mathcal{O}(n \log n)$ total.
   - **Pre-sorted mode (`is_presorted=True`)**: If start-sorted indices are available or sorted via auxiliary pass only when unsorted, compute all predecessors via monotonic two-pointer scan in $\mathcal{O}(n')$ without binary search (specifically, when inputs are already pre-sorted by $r_i$ and start order is provided or tracked, two pointers achieve strict $\mathcal{O}(n)$ total time; in standard `is_presorted=True` calls without pre-sorted start times, sorting by start time takes $\mathcal{O}(n \log n)$, so the API explicitly supports pre-sorted `(by_release, by_start)` or falls back safely while preserving exactness).
5. Fill DP table in $\mathcal{O}(n')$:
   - `dp = [0] * (n' + 1)`
   - For $k = 1 \dots n'$: `dp[k] = max(dp[k - 1], 1 + dp[p[k]])`.
6. Backtrack from $k = n'$ down to $1$ in $\mathcal{O}(n')$:
   - If `1 + dp[p[k]] >= dp[k - 1]`, pick item $k - 1$ and jump to `k = p[k]`; else `k -= 1`.
   - Reverse collected items to restore chronological order.
7. Return `SchedulingResult`.

---

## 5. Planned Repository Layout

```text
escalonamento-intervalos-paa/
├── .agents/
│   └── rules/AGENTS.md
├── openspec/
│   ├── specs/
│   ├── changes/
│   └── archive/
├── src/
│   ├── __init__.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── exceptions.py          # InvalidSchedulingInputError
│   │   ├── models.py              # Enums, ShiftConfig, SurgeryRequest, SchedulingResult
│   │   └── preprocessing.py       # Feasibility validation & Effective Release Time (r_i)
│   ├── schedulers/
│   │   ├── __init__.py
│   │   ├── protocol.py            # IntervalSchedulerProtocol
│   │   ├── classic_greedy.py      # ClassicGreedyScheduler (Baseline)
│   │   ├── classic_dp.py          # ClassicDPScheduler (Baseline)
│   │   ├── adapted_greedy.py      # AdaptedGreedyScheduler (Authorial)
│   │   ├── adapted_dp.py          # AdaptedDPScheduler (Authorial)
│   │   └── brute_force_oracle.py  # Exact oracle (n <= 20) for test cross-validation
│   ├── benchmark/
│   │   ├── __init__.py
│   │   └── runner.py              # Comparative runtime & optimality benchmark runner
│   └── main.py                    # CLI / Visual interface entry point (TBD)
├── tests/
│   ├── fixtures/
│   │   └── scenarios.py           # Pre-configured deterministic hospital scenarios
│   ├── test_domain_and_preprocessing.py
│   ├── test_classic_schedulers.py
│   ├── test_adapted_schedulers.py
│   └── test_oracle_and_comparison.py
├── pyproject.toml / requirements.txt
├── README.md
└── LICENSE
```

---

## Functional Requirements

- **[RF-01]** All domain models MUST enforce validation invariants at creation time and remain immutable.
- **[RF-02]** All four primary schedulers (`ClassicGreedyScheduler`, `ClassicDPScheduler`, `AdaptedGreedyScheduler`, `AdaptedDPScheduler`) MUST implement `IntervalSchedulerProtocol`.
- **[RF-03]** Both DP implementations MUST reconstruct and return the exact optimal subset of surgeries (not only the numeric cardinality).
- **[RF-04]** Both Classic and Adapted solvers MUST measure and expose execution timing (`elapsed_ns`) excluding external I/O.
- **[RF-05]** All Python identifiers (packages, modules, classes, methods, attributes, variables) MUST be written in English (`en-US`), while all comments and docstrings MUST be written in Brazilian Portuguese (`pt-BR`).

## Non-Functional Requirements

- **[RNF-01]** Core scheduling modules (`src/domain/`, `src/schedulers/`) MUST have zero third-party runtime dependencies, relying strictly on Python 3.12+ Standard Library modules.
- **[RNF-02]** Each scheduler module MUST adhere to Single Responsibility and remain concise, readable, and strictly typed.
- **[RNF-03]** Brute-force oracle execution MUST reject any input with $n > 20$ to prevent exponential execution lockups.

## Out of Scope

- Parallelizing or multi-threading scheduler runs across CPU cores.
- Persisting schedules to an external relational or NoSQL database.

## Revision History

| Version | Date | Author | Summary |
|---------|------|--------|---------|
| 1.0.0 | 2026-11-15 | `@allysson-assuncao` | Initial specification of domain models, SOLID contracts, classic baselines, adapted algorithms, and package layout |
