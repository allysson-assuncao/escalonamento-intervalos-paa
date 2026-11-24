"""Exportações públicas da camada de interface visual e simulação."""

from src.ui.scenarios_catalog import (
    DEFAULT_CLOSING_HORIZON,
    DEFAULT_SHIFT_WINDOW,
    ScenarioPreset,
    get_scenario_by_id,
    get_scenario_presets,
)
from src.ui.server import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    MAX_COMPARE_INPUT_SIZE,
    MAX_REQUEST_BODY_BYTES,
    SimulationRequestHandler,
    create_http_server,
)
from src.ui.tracer import (
    ALGORITHM_KEYS,
    MAX_TRACE_INPUT_SIZE,
    AlgorithmComparisonEntry,
    SimulationStep,
    SimulationTrace,
    SurgeryVisualStatus,
    TracePhase,
    format_minutes_hhmm,
    run_comparative_arena,
    trace_scheduler_execution,
)

__all__ = [
    "ALGORITHM_KEYS",
    "AlgorithmComparisonEntry",
    "DEFAULT_CLOSING_HORIZON",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "DEFAULT_SHIFT_WINDOW",
    "MAX_COMPARE_INPUT_SIZE",
    "MAX_REQUEST_BODY_BYTES",
    "MAX_TRACE_INPUT_SIZE",
    "ScenarioPreset",
    "SimulationRequestHandler",
    "SimulationStep",
    "SimulationTrace",
    "SurgeryVisualStatus",
    "TracePhase",
    "create_http_server",
    "format_minutes_hhmm",
    "get_scenario_by_id",
    "get_scenario_presets",
    "run_comparative_arena",
    "trace_scheduler_execution",
]
