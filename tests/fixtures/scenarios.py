"""Cenários determinísticos pré-configurados reexportados do catálogo compartilhado."""

from src.ui.scenarios_catalog import (
    DEFAULT_CLOSING_HORIZON,
    DEFAULT_SHIFT_WINDOW,
    build_monotonic_start_presorted_surgeries,
    build_sc01_classic_homogeneous_surgeries,
    build_sc02_counterexample_surgeries,
    build_sc03_end_of_shift_boundary,
    build_sc04_shift_window_scenarios,
    build_sc05_edge_case_scenarios,
)

__all__ = [
    "DEFAULT_CLOSING_HORIZON",
    "DEFAULT_SHIFT_WINDOW",
    "build_monotonic_start_presorted_surgeries",
    "build_sc01_classic_homogeneous_surgeries",
    "build_sc02_counterexample_surgeries",
    "build_sc03_end_of_shift_boundary",
    "build_sc04_shift_window_scenarios",
    "build_sc05_edge_case_scenarios",
]
