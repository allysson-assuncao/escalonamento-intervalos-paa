# Project Conventions & Engineering Rules — escalonamento-intervalos-paa

## 1. Language & Communication Constraints
- **User Interaction**: All agent communication, explanations, questions, and reports to the user MUST be written in Brazilian Portuguese (`pt-BR`).
- **Source Code Identifiers**: All code syntax, module names, class names, method names, variables, and type hints MUST be written in English (`en-US`).
- **Code Comments & Git Commits**: All inline code comments, docstrings, and Git commit messages MUST be written in Brazilian Portuguese (`pt-BR`).
- **OpenSpec Documentation**: All files inside `openspec/` (`specs/`, `changes/`, `proposal.md`, `tasks.md`, and `sdd-stack-contract.md`) MUST be written 100% in English (`en-US`).

## 2. Technology Stack & Dependencies
- **Primary Language**: Python 3.12+ using the Python Standard Library for core algorithms and data structures (`dataclasses`, `bisect`, `typing`, `enum`, `time`).
- **Testing Framework**: `pytest` for automated unit, comparative, and property/oracle testing.
- **Visual Interface**: To be defined in the dedicated UI specification/change before adding external UI dependencies.

## 3. Architecture, Clean Code & SOLID Principles
- **Coexistence for Comparison**: Maintain both **Classic (Baseline)** and **Adapted (Surgical Sterilization & Shift Window)** implementations of Greedy and Dynamic Programming algorithms side by side under common interfaces/protocols to allow direct comparison of code structure, optimality, and execution time.
- **SOLID & Clean Code**: Enforce Single Responsibility Principle (separate validation/preprocessing, scheduling algorithms, and benchmarking), Dependency Inversion (shared scheduler contracts), immutable domain models (`@dataclass(frozen=True)`), and explicit complexity guarantees ($\mathcal{O}(n \log n)$ general case, $\mathcal{O}(n)$ pre-sorted).

## 4. Shift-Left Testing & Verification
- Every algorithm implementation MUST be accompanied by automated tests with pre-configured scenarios covering:
  1. Classic baseline equivalence cases;
  2. Counterexamples where Classic Greedy or Naive Reduction ($f'_i = f_i + c_i$) fail while Adapted Greedy and Adapted DP find the exact optimum;
  3. Shift-change window $[A, B]$ and closing horizon $H$ boundary cases;
  4. Cross-validation ensuring `Adapted Greedy == Adapted DP == Brute-Force Oracle` on small instances.
