"""Cenários determinísticos pré-configurados reexportados do catálogo compartilhado."""

from src.ui.scenarios_catalog import (
    DEFAULT_CLOSING_HORIZON,
    DEFAULT_SHIFT_WINDOW,
    build_case01_classic_baseline,
    build_case02_sterilization_and_horizon,
    build_case03_shift_window,
    build_case04_full_mixed_shift,
)

__all__ = [
    "DEFAULT_CLOSING_HORIZON",
    "DEFAULT_SHIFT_WINDOW",
    "build_case01_classic_baseline",
    "build_case02_sterilization_and_horizon",
    "build_case03_shift_window",
    "build_case04_full_mixed_shift",
]
