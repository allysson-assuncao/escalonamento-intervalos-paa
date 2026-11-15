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

__all__ = [
    "InvalidSchedulingInputError",
    "ProcessedSurgery",
    "SchedulingResult",
    "ShiftConfig",
    "ShiftWindow",
    "SurgeryRequest",
    "SurgeryType",
    "is_strict_int",
]
