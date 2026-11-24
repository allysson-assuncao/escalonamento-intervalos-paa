"""Exportações públicas da camada de domínio."""

from src.domain.exceptions import InvalidSchedulingInputError
from src.domain.models import (
    ProcessedSurgery,
    SchedulingResult,
    ShiftConfig,
    ShiftWindow,
    SurgeryRequest,
    SurgeryType,
    is_strict_int,
)
from src.domain.preprocessing import (
    compute_effective_release_time,
    is_actively_feasible,
    preprocess_feasible_surgeries,
    validate_scheduler_inputs,
)

__all__ = [
    "InvalidSchedulingInputError",
    "ProcessedSurgery",
    "SchedulingResult",
    "ShiftConfig",
    "ShiftWindow",
    "SurgeryRequest",
    "SurgeryType",
    "compute_effective_release_time",
    "is_actively_feasible",
    "is_strict_int",
    "preprocess_feasible_surgeries",
    "validate_scheduler_inputs",
]
