# SDD Stack Contract

> This file declares the technology stack and architectural constraints of this project.
> It is read by skills and subagents to make stack-aware decisions.
> Fill in each section and commit this file to version control.

---

## Stack Identity

- **Project Name:** `escalonamento-intervalos-paa`
- **Primary Language:** Python
- **Runtime / Platform:** Python 3.12+
- **Framework:** Python Standard Library (`dataclasses`, `bisect`, `typing`, `enum`, `time`, `math`, `random`, `statistics`) for core scheduling algorithms and benchmarking; Python Standard Library local web server (`http.server`, `json`, `urllib.parse`, `webbrowser`, `argparse`) + zero-dependency Vanilla HTML5/CSS3/ES6 JavaScript and native interactive SVG for the visual simulation interface (`src/ui/` and `src/main.py`).
- **Package Manager:** `pip` + `venv` (`pyproject.toml` / `requirements.txt`)

---

## Project Structure

- **Source Root:** `src/`
- **Test Root:** `tests/`
- **Entry Point:** `src/main.py`
- **Build Output:** N/A (interpreted Python package)

---

## Test Runner

- **Command:** `pytest`
- **Test Framework:** `pytest`
- **Coverage Command:** `pytest -v`

---

## Code Style

- **Linter:** `ruff` (optional) / standard PEP 8 compliance
- **Formatter:** PEP 8 standard formatting with strict type annotations (`typing`)
- **Format Command:** `ruff format .` (if installed)

---

## API Contract (if applicable)

- **API Type:** Internal Python Domain & Strategy Contracts + Local Loopback HTTP JSON API (`GET /api/scenarios`, `POST /api/trace`, `POST /api/compare`, `POST /api/generate`, `POST /api/benchmark`) served by `src/ui/server.py`
- **Spec Location:** `openspec/specs/algorithms-and-domain-architecture.md`
- **Base URL (dev):** `http://127.0.0.1:8765` (configurable via `--host` and `--port` in `src/main.py`)

---

## Database (if applicable)

- **Engine:** N/A (in-memory algorithmic processing and pre-configured test fixtures)
- **Migration Tool:** N/A
- **Migration Command:** N/A

---

## Notes

- All source code identifiers (modules, classes, methods, functions, variables, type hints) MUST be written in English (`en-US`).
- All inline code comments, docstrings, and Git commit messages MUST be written in Brazilian Portuguese (`pt-BR`).
- All specifications and change artifacts inside `openspec/` MUST be written 100% in English (`en-US`).
- All agent-user interactions MUST be conducted in Brazilian Portuguese (`pt-BR`).
- Both **Classic (Baseline)** and **Adapted (Surgical Sterilization & Shift Window)** implementations of Greedy and Dynamic Programming algorithms must coexist in the codebase for comparative complexity, runtime, and optimality analysis.
