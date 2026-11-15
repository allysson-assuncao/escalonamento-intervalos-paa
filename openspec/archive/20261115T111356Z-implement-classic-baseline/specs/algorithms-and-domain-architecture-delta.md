# Delta Spec: `algorithms-and-domain-architecture`

> **Change ID:** `implement-classic-baseline`
> **Target Canonical Spec:** `openspec/specs/algorithms-and-domain-architecture.md`
> **Change Type:** Modify

## Architectural Updates

### 1. Pure Classic Textbook Mode Scope Clarification
- `ClassicGreedyScheduler` and `ClassicDPScheduler` strictly implement **Pure Classic Textbook Mode**:
  - They evaluate interval compatibility exclusively over $[s_i, f_i]$ ($s_j \ge f_i$).
  - They ignore `sterilization_duration` ($c_i$) and `shift_config` ($H$, $[A, B]$), always setting `effective_release_time = request.finish_time` and `discarded_infeasible_count = 0`.
- The **Naive Static Reduction** comparator ($f'_i = f_i + c_i$ with horizon filtering) is scoped to Change #3 alongside `AdaptedGreedyScheduler` and `AdaptedDPScheduler` so that baseline textbook comparison remains decoupled from authorial domain constraints in Change #2.

### 2. Pre-Sorted $\mathcal{O}(n)$ Safety & Two-Pointer Predecessor Contract (`ClassicDPScheduler`)
- When `is_presorted=True` is passed to `ClassicGreedyScheduler` or `ClassicDPScheduler`:
  - The caller guarantees `surgeries` is already sorted in non-decreasing `(finish_time, start_time)` order.
  - The scheduler verifies this precondition in a single $\mathcal{O}(n)$ pass and raises `InvalidSchedulingInputError` if violated, without incurring $\mathcal{O}(n \log n)$ re-sorting.
- In `ClassicDPScheduler.schedule(...)`, an optional keyword parameter `presorted_start_indices: Sequence[int] | None = None` (consistent with `IntervalSchedulerProtocol`) enables strict $\mathcal{O}(n)$ two-pointer predecessor computation even when start times in finish-sorted order are not monotonically non-decreasing:
  - If `is_presorted=True` and `presorted_start_indices` is provided (validated as a permutation of `0..n-1` sorted by `start_time`), predecessors `p[1..n]` are computed via two pointers in $\mathcal{O}(n)$.
  - Else if `is_presorted=True` and `start_time` is already monotonically non-decreasing in the finish-sorted sequence (checked in $\mathcal{O}(n)$), predecessors are computed via two pointers in $\mathcal{O}(n)$.
  - Otherwise, predecessors are computed via `bisect.bisect_right` in $\mathcal{O}(n \log n)$ to guarantee exact optimality for arbitrary input distributions.
