"""Exportações públicas do módulo de benchmark empírico."""

from src.benchmark.runner import (
    BenchmarkPoint,
    format_benchmark_table,
    generate_synthetic_surgeries,
    run_scaling_benchmark,
)

__all__ = [
    "BenchmarkPoint",
    "format_benchmark_table",
    "generate_synthetic_surgeries",
    "run_scaling_benchmark",
]
