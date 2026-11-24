---
id: "problem-definition-and-mathematical-model"
title: "Problem Definition and Mathematical Model — Surgical Interval Scheduling"
version: "1.1.0"
status: "active"
owners:
  - "@allysson-assuncao"
scope:
  paths:
    - "src/domain/**"
    - "src/schedulers/**"
resources:
  - "openspec/specs/algorithms-and-domain-architecture.md"
  - "openspec/specs/testing-benchmark-and-visual-interface.md"
---

# Problem Definition and Mathematical Model — Living Specification

> This is the authoritative source of truth for the academic mandate, domain context, mathematical formulation, optimality proofs, non-reducibility justification, and asymptotic complexity parity of `escalonamento-intervalos-paa`.
> Update this file only after merging a completed change from `openspec/changes/`.

---

## Context & Objectives

This project fulfills an academic Design and Analysis of Algorithms (PAA — *Projeto e Análise de Algoritmos*) assignment requiring two exact, polynomial-time optimization algorithms—one **Greedy** and one **Dynamic Programming (DP)**—that solve a non-NP-Hard problem within the **same asymptotic time complexity class**. To introduce an original, non-trivial contribution, the project extends the classical **Interval Scheduling Problem** in an applied **Hospital Operating Room (OR)** context with **asymmetric biological sterilization cooldowns** and **medical shift constraints** (a closing horizon $H$ and an optional shift-change window $[A, B]$), adapting both consolidated textbook algorithms while preserving 100% exact optimality and identical $\mathcal{O}(n \log n)$ time complexity.

---

## 1. Academic Assignment Mandate

The project MUST satisfy all original assignment requirements:

1. **Polynomial Problem Class**: Select a non-NP-Hard optimization problem admitting exact optimal solutions via both **Dynamic Programming** and a **Greedy Strategy** with identical asymptotic time complexity ($\mathcal{O}(n \log n)$).
2. **Authorial Constraint & Adaptation**: Introduce a domain-grounded additional constraint and authorially adapt both consolidated textbook solutions so they continue to obtain the exact global optimum while preserving the same asymptotic complexity class.
3. **Comparative Baseline Retention**: Implement and preserve the classical (unmodified) Greedy and DP solutions alongside the adapted solutions throughout the project lifecycle to compare algorithm structure, decision behavior, and physical validity.
4. **Pre-Configured Tests & Verification**: Provide automated tests with pre-configured scenarios demonstrating correctness, edge cases, and classic-vs-adapted divergence.
5. **Documentation, Execution Instructions & Visual Interface**: Deliver clear project documentation, reproducible execution instructions, and an intuitive visual interface capable of illustrating algorithm execution, data structures, variables, and asymptotic complexity during class presentation.

---

## 2. Classical Baseline Problem (Interval Scheduling / Activity Selection)

### 2.1. Applied Operating Room Formulation
- **Literature Name**: *Interval Scheduling Problem* / *Activity Selection Problem*.
- **Applied Scenario**: A hospital operates a **single surgical room** and receives $n$ surgery requests for a day. The objective is to **maximize the number of non-overlapping surgeries performed**.
- **Classical Inputs**:
  - A sequence of $n$ surgery requests $I = \{1, 2, \dots, n\}$.
  - Each surgery $i$ is defined solely by its start time $s_i$ and finish time $f_i$, with $s_i < f_i$.
- **Classical Compatibility Constraint**:
  - Two surgeries $i$ and $j$ are mutually compatible iff their intervals do not overlap: if surgery $i$ precedes surgery $j$, then $s_j \ge f_i$.
- **Classical Output**:
  - A maximum-cardinality subset $S^* \subseteq I$ of pairwise compatible surgeries.

### 2.2. Consolidated Classical Algorithms ($\mathcal{O}(n \log n)$)
- **Classical Greedy (*Earliest Finish Time*)**:
  1. Sort all surgeries by non-decreasing finish time $f_i$ in $\mathcal{O}(n \log n)$.
  2. Scan linearly in $\mathcal{O}(n)$, greedily selecting each surgery $i$ whose start time satisfies $s_i \ge f_{\text{last}}$.
  - **Total Complexity**: $\mathcal{O}(n \log n)$.
- **Classical Dynamic Programming (Unweighted Interval Scheduling)**:
  1. Sort all surgeries by non-decreasing finish time $f_i$ in $\mathcal{O}(n \log n)$.
  2. Compute the latest compatible predecessor $p(i) = \max\{j < i \mid f_j \le s_i\}$ (or $0$ if none exists) via binary search in $\mathcal{O}(n \log n)$.
  3. Evaluate the recurrence $DP[0] = 0$ and $DP[i] = \max(DP[i - 1], 1 + DP[p(i)])$ for $i = 1, \dots, n$, and backtrack to reconstruct $S^*$ in $\mathcal{O}(n)$.
  - **Total Complexity**: $\mathcal{O}(n \log n)$.

---

## 3. Authorial Domain Adaptation: Asymmetric Sterilization & Shift Windows

### 3.1. Design Rationale — Avoiding Two Classic Pitfalls
1. **Pitfall 1 — Breaking the Greedy Choice Property**: Most naive extensions (such as arbitrary surgery weights/priorities or arbitrary pairwise setup matrices $s_{i,j}$) destroy the Greedy Choice Property, leaving only DP valid or turning the problem NP-Hard.
2. **Pitfall 2 — Trivial Static Reduction**: Simply adding an unconditional cleanup duration $c_i$ to every finish time reduces trivially to preprocessing $f'_i = f_i + c_i$ on the input and executing the unmodified classical algorithm.

Our adaptation avoids both pitfalls through **asymmetric biological sterilization coupled with passive transition overlap against medical shift boundaries**, which cannot be reduced to a static transformation $f'_i = f_i + c_i$ yet preserves a total order on the room's effective release time.

### 3.2. Extended Inputs
For each surgery request $i \in \{1, \dots, n\}$:
- **$s_i \ge 0$**: Active surgical start time (integer minutes from midnight).
- **$f_i > s_i$**: Active surgical finish time.
- **$t_i \in \{\text{CLEAN}, \text{CONTAMINATED}\}$**: Biological contamination risk class:
  - **$\text{CLEAN}$**: Standard clean procedure; requires no heavy decontamination ($c_i = 0$).
  - **$\text{CONTAMINATED}$**: Infected/contaminated procedure; requires automated ozone/UV room sterilization of strictly positive duration $c_i > 0$ after $f_i$ before any subsequent surgery may begin.
- **$c_i \ge 0$**: Automated sterilization cooldown duration ($c_i = 0$ when $t_i = \text{CLEAN}$; $c_i > 0$ when $t_i = \text{CONTAMINATED}$).

Global Operating Room shift parameters:
- **$H > 0$**: Medical shift closing horizon (e.g., `18:00` / `1080` minutes).
- **$[A, B]$** *(optional)*: Fixed shift-change / maintenance interdiction window with $0 \le A < B \le H$ (e.g., `[12:00, 13:00]` / `[720, 780]` minutes). When no mid-shift break exists, $[A, B]$ is `None`.

### 3.3. Official Business & Operational Rules
1. **Active Medical Execution Rule (Active Feasibility)**:
   - The surgical operation $[s_i, f_i]$ requires the medical team to be actively present in the room.
   - Therefore, surgery $i$ is feasible iff:
     - $0 \le s_i < f_i \le H$, and
     - When a shift-change window $[A, B]$ is configured, the active surgical interval $[s_i, f_i)$ does NOT overlap $[A, B)$, i.e.:
       $$f_i \le A \quad \text{or} \quad s_i \ge B$$
   - Surgeries violating either condition are filtered out during feasibility validation.

2. **Automated Sterilization Rule (Passive Transition Overlap)**:
   - Automated ozone/UV sterilization spans $[f_i, f_i + c_i)$ and operates **without medical personnel**.
   - Consequently, sterilization **MAY extend past the closing horizon $H$** (for example, a contaminated surgery running `15:00–17:45` with $60$ minutes of sterilization until `18:45` when $H = 18:00$ is completely valid as long as no subsequent surgery is scheduled after it) and **MAY execute concurrently during the shift-change window $[A, B]$**.
   - However, any **subsequent surgery $j$** on the same day can only start once the room is **simultaneously sterilized and outside the shift-change window $[A, B)$**.

### 3.4. Closed-Form Effective Release Time ($r_i$)
For each feasible surgery $i$, let its raw sterilization end time be:
$$e_i = f_i + c_i$$

The **Effective Release Time ($r_i$)**—the earliest timestamp at or after $f_i$ when a subsequent valid surgery could possibly begin—is computed in $\mathcal{O}(1)$ per surgery:
- If no shift-change window $[A, B]$ is configured:
  $$r_i = e_i$$
- If a shift-change window $[A, B]$ is configured:
  $$r_i = \begin{cases} B, & \text{if } f_i \le A \text{ and } A < e_i < B \\ e_i, & \text{otherwise} \end{cases}$$

Compatibility between a feasible surgery $i$ and a subsequent feasible surgery $j$ reduces cleanly to the single scalar inequality:
$$s_j \ge r_i$$

---

## 4. Non-Reducibility Proof & Canonical 3-Surgery Counterexample (`CASE-02`)

To prove mathematically that the adapted problem is **not** trivially reducible to the classical problem via static input transformation $f'_i = f_i + c_i$, consider an Operating Room with closing horizon $H = 18:00$ (no mid-shift break) and three afternoon surgery requests (`CASE-02`):

| Surgery | Type ($t_i$) | Active Interval $[s_i, f_i]$ | Sterilization ($c_i$) | Active Valid ($f_i \le 18:00$)? | Raw End ($e_i = f_i + c_i$) | Effective Release ($r_i$) |
|---------|--------------|------------------------------|-----------------------|----------------------------------|------------------------------|-------------------------|
| **S1** | `CONTAMINATED` | `13:00` – `14:00` | `2h` (`120` min) | Yes (`14:00 <= 18:00`) | `16:00` | `16:00` |
| **S2** | `CLEAN` | `13:30` – `15:00` | `0h` (`0` min) | Yes (`15:00 <= 18:00`) | `15:00` | `15:00` |
| **S3** | `CONTAMINATED` | `15:00` – `17:45` | `1h` (`60` min) | Yes (`17:45 <= 18:00`) | `18:45` | `18:45` |

### Behavior Comparison Across Strategies
1. **Classical Greedy & Classical DP (sort solely by active finish $f_i$)**:
   - Select **S1** (`14:00 < 15:00`) and **S3** (`15:00 >= 14:00`), ignoring `S1`'s 2h sterilization until `16:00`, resulting in an **invalid physical conflict** (or yielding only `{S1}` = 1 when sterilization is enforced).
2. **Hypothetical Naive Static Reduction ($f'_i = f_i + c_i \le H$)**:
   - Computes $f'_3 = 17:45 + 1\text{h} = 18:45 > 18:00$ and **falsely discards S3 as infeasible**, yielding at most `1` surgery.
3. **Adapted Authorial Greedy & Adapted Authorial DP**:
   - Separate **active validity** ($f_i \le H$, keeping S3) from **effective room release** ($r_i$).
   - Recognize $r_2 = 15:00 < r_1 = 16:00$, selecting **`{S2, S3}` (count = 2 — Exact Global Optimum)**.

---

## 5. Optimality Proofs & Asymptotic Complexity Parity

### 5.1. Adapted Greedy Optimality Proof (*Exchange Argument*)
Let $F$ be the set of active-feasible surgeries sorted in non-decreasing order of Effective Release Time $r_i$ (tie-breaking by non-decreasing $f_i$). Let $G = \{g_1, g_2, \dots, g_k\}$ be the schedule produced by Adapted Greedy (`Earliest Effective Release Time`), and let $O = \{o_1, o_2, \dots, o_m\}$ be any optimal feasible schedule sorted in chronological order.

- **Base Claim ($k \ge 1$)**: Since $g_1$ minimizes $r_i$ over all feasible surgeries in $F$, $r_{g_1} \le r_{o_1}$. Replacing $o_1$ with $g_1$ in $O$ yields $O' = \{g_1, o_2, \dots, o_m\}$, which remains valid because $s_{o_2} \ge r_{o_1} \ge r_{g_1}$ and $g_1$ is active-feasible against $H$ and $[A, B]$.
- **Inductive Step ("Greedy Stays Ahead")**: Assume $g_1, \dots, g_t$ have been selected with $r_{g_t} \le r_{o_t}$. Because $s_{o_{t+1}} \ge r_{o_t} \ge r_{g_t}$, surgery $o_{t+1}$ is available to Adapted Greedy at step $t + 1$. Therefore Adapted Greedy selects a surgery $g_{t+1}$ satisfying $r_{g_{t+1}} \le r_{o_{t+1}}$.
- **Conclusion**: By induction, $k = m$, proving $G$ is 100% optimal.

### 5.2. Adapted Dynamic Programming Optimality Proof (*Optimal Substructure*)
After sorting the $n' \le n$ active-feasible surgeries by non-decreasing $r_i$, define for each $i \in \{1, \dots, n'\}$:
$$p(i) = \max\big(\{0\} \cup \{j \in \{1, \dots, i-1\} \mid r_j \le s_i\}\big)$$

Because any valid surgery selected before $i$ must have $r_j \le s_i$ and the sequence is ordered by $r_1 \le r_2 \le \dots \le r_{n'}$, all compatible predecessors of $i$ lie in the contiguous prefix $\{1, \dots, p(i)\}$. Thus, the maximum cardinality over $\{1, \dots, i\}$ satisfies:
$$DP[0] = 0, \qquad DP[i] = \max\big(DP[i - 1],\; 1 + DP[p(i)]\big)$$
Backtracking from $i = n'$ down to $1$ recovers an exact optimal subset.

### 5.3. Comparative Complexity Summary

| Execution Phase | Adapted Greedy | Adapted Dynamic Programming |
|-----------------|----------------|-----------------------------|
| **1. Active Feasibility Validation & $r_i$ Computation** | $\mathcal{O}(n)$ | $\mathcal{O}(n)$ |
| **2. Sorting by Effective Release Time ($r_i$)** | $\mathcal{O}(n \log n)$ | $\mathcal{O}(n \log n)$ |
| **3. Predecessor Computation $p(i)$** | *Not applicable* | $\mathcal{O}(n \log n)$ via binary search (`bisect_right`) |
| **4. Selection / DP Transition & Reconstruction** | $\mathcal{O}(n)$ linear scan | $\mathcal{O}(n)$ table fill + $\mathcal{O}(n)$ backtracking |
| **Total Time Complexity** | **$\mathcal{O}(n \log n)$** | **$\mathcal{O}(n \log n)$** |
| **Auxiliary Space Complexity** | **$\mathcal{O}(n)$** | **$\mathcal{O}(n)$** (`DP[0..n']` and `p[1..n']`) |

---

## Functional Requirements

- **[RF-01]** The system MUST model Operating Room surgery requests with active interval $[s_i, f_i]$, biological classification $t_i \in \{\text{CLEAN}, \text{CONTAMINATED}\}$, and automated sterilization duration $c_i \ge 0$.
- **[RF-02]** The adapted model MUST enforce active medical feasibility against closing horizon $H$ ($f_i \le H$) and optional shift-change window $[A, B]$ ($f_i \le A$ or $s_i \ge B$).
- **[RF-03]** The adapted model MUST allow automated sterilization $[f_i, f_i + c_i)$ to execute during $[A, B]$ or extend beyond $H$, computing $r_i = B$ when $f_i \le A$ and $A < f_i + c_i < B$, and $r_i = f_i + c_i$ otherwise.
- **[RF-04]** Both Adapted Greedy and Adapted DP MUST yield exact optimal solutions of equal maximum cardinality for every valid problem instance.
- **[RF-05]** Classical Greedy and Classical DP solvers MUST be retained on the same inputs (using $[s_i, f_i]$ compatibility) for side-by-side comparison.

## Non-Functional Requirements

- **[RNF-01]** All four primary solvers (Classic Greedy, Classic DP, Adapted Greedy, Adapted DP) MUST run in $\mathcal{O}(n \log n)$ time complexity using sorting and binary search (`bisect_right`).
- **[RNF-02]** Auxiliary space complexity MUST remain bounded by $\mathcal{O}(n)$ for both approaches.
- **[RNF-03]** All domain specifications and mathematical definitions MUST be 100% documented in English (`en-US`).

## Out of Scope

- Supporting multiple simultaneous operating rooms (parallel machine scheduling).
- Supporting weighted surgery priorities or arbitrary pairwise setup matrices $s_{i,j}$ (which violate the Greedy Choice Property).
- Supporting multiple simultaneous shift-change interdiction windows $[a_k, b_k]$ in v1 (explicitly simplified to closing horizon $H$ plus at most one shift-change window $[A, B]$).

## Revision History

| Version | Date | Author | Summary |
|---------|------|--------|---------|
| 1.0.0 | 2026-11-15 | `@allysson-assuncao` | Initial canonical consolidation of PAA assignment mandate, mathematical model, proofs, and counterexample |
| 1.1.0 | 2026-11-24 | `@allysson-assuncao` | Consolidated `simplify-core-and-presentation-ui`: streamlined complexity model around the 4 core $\mathcal{O}(n \log n)$ solvers and `CASE-02` counterexample |
