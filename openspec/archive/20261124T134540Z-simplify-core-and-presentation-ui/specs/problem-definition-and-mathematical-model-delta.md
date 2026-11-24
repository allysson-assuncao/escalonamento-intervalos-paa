# Delta Spec: `problem-definition-and-mathematical-model`

> **Change ID:** `simplify-core-and-presentation-ui`
> **Target Canonical Spec:** `openspec/specs/problem-definition-and-mathematical-model.md`
> **Change Type:** Modify

## Architectural Updates

### 1. Focus Asymptotic Complexity & Solvers on the Core $\mathcal{O}(n \log n)$ Formulations
- Update Section 2.2, Section 3.1, Section 4, Section 5.3, and Requirements (`[RNF-01]`) to standardize exclusively on the $\mathcal{O}(n \log n)$ general-case algorithms (`ClassicGreedyScheduler`, `ClassicDPScheduler`, `AdaptedGreedyScheduler`, `AdaptedDPScheduler`):
  - Sorting takes $\mathcal{O}(n \log n)$ by $f_i$ (Classic) or $r_i$ (Adapted).
  - Dynamic Programming computes $p(i)$ via binary search in $\mathcal{O}(n \log n)$ and executes DP table evaluation + backtracking in $\mathcal{O}(n)$.
  - Auxiliary space remains $\mathcal{O}(n)$.
- Remove references to a separate pre-sorted $\mathcal{O}(n)$ two-pointer DP permutation mode and remove references to a fifth `NaiveReductionScheduler` implementation (while keeping the conceptual discussion of why static transformation $f'_i = f_i + c_i \le H$ fails on the 3-surgery counterexample `CASE-02`).

### 2. Align Counterexample Identifier with Didactic Scenario Catalog
- Refer to the canonical 3-surgery non-reducibility counterexample (`S1` 13:00–14:00 + 120m, `S2` 13:30–15:00 + 0m, `S3` 15:00–17:45 + 60m, $H=18:00$) as `CASE-02`.
