"""Oráculo exato por força bruta com poda (branch-and-bound) limitado a n <= 20."""

from collections.abc import Sequence
import time

from src.domain.exceptions import InvalidSchedulingInputError
from src.domain.models import (
    ProcessedSurgery,
    SchedulingResult,
    ShiftConfig,
    SurgeryRequest,
)
from src.domain.preprocessing import (
    preprocess_validated_surgeries,
    validate_scheduler_inputs,
)
from src.schedulers.protocol import order_processed_surgeries

MAX_ORACLE_INPUT_SIZE: int = 20


class BruteForceOracleScheduler:
    """Oráculo exato limitado a entradas pequenas (n <= 20) para validação cruzada."""

    @property
    def name(self) -> str:
        """Retorna o nome descritivo do oráculo exato por força bruta."""
        return "Brute-Force Exact Oracle"

    def schedule(
        self,
        surgeries: Sequence[SurgeryRequest],
        shift_config: ShiftConfig | None = None,
        *,
        is_presorted: bool = False,
    ) -> SchedulingResult:
        """Enumera subconjuntos viáveis com poda para certificar a otimalidade global."""
        items = validate_scheduler_inputs(surgeries, shift_config)
        if len(items) > MAX_ORACLE_INPUT_SIZE:
            raise InvalidSchedulingInputError(
                f"O oráculo exato suporta no máximo {MAX_ORACLE_INPUT_SIZE} cirurgias por execução."
            )

        start_ns = time.perf_counter_ns()
        feasible, discarded_count = preprocess_validated_surgeries(items, shift_config)
        ordered = order_processed_surgeries(feasible, is_presorted=is_presorted)
        selected = _search_exact_optimum(ordered)

        elapsed_ns = time.perf_counter_ns() - start_ns
        return SchedulingResult(
            algorithm_name=self.name,
            selected_surgeries=selected,
            total_selected=len(selected),
            discarded_infeasible_count=discarded_count,
            elapsed_ns=elapsed_ns,
        )


def _search_exact_optimum(
    ordered: Sequence[ProcessedSurgery],
) -> tuple[ProcessedSurgery, ...]:
    """Busca exata por branch-and-bound sobre sequência ordenada por r_i."""
    n = len(ordered)
    best_indices: list[int] = []
    current_indices: list[int] = []

    def _dfs(idx: int, last_release: int) -> None:
        nonlocal best_indices
        if len(current_indices) > len(best_indices):
            best_indices = current_indices.copy()
        if idx == n:
            return
        # Poda se nem selecionando todos os restantes seria possível superar o melhor atual
        if len(current_indices) + (n - idx) <= len(best_indices):
            return

        candidate = ordered[idx]
        if candidate.request.start_time >= last_release:
            current_indices.append(idx)
            _dfs(idx + 1, candidate.effective_release_time)
            current_indices.pop()

        _dfs(idx + 1, last_release)

    _dfs(0, -1)
    return tuple(ordered[idx] for idx in best_indices)
