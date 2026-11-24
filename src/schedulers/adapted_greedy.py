"""Implementação do Algoritmo Guloso Adaptado (Earliest Effective Release Time)."""

from collections.abc import Sequence
import time

from src.domain.models import SchedulingResult, ShiftConfig, SurgeryRequest
from src.domain.preprocessing import (
    preprocess_validated_surgeries,
    validate_scheduler_inputs,
)
from src.schedulers.protocol import (
    order_processed_surgeries,
    select_greedy_processed_surgeries,
)


class AdaptedGreedyScheduler:
    """Escalonador guloso adaptado para esterilização assimétrica, H e janela [A, B]."""

    @property
    def name(self) -> str:
        """Retorna o nome descritivo do algoritmo guloso adaptado."""
        return "Adapted Greedy (Earliest Effective Release)"

    def schedule(
        self,
        surgeries: Sequence[SurgeryRequest],
        shift_config: ShiftConfig | None = None,
    ) -> SchedulingResult:
        """Seleciona subconjunto ótimo em O(n log n) priorizando menor liberação efetiva r_i."""
        items = validate_scheduler_inputs(surgeries, shift_config)

        start_ns = time.perf_counter_ns()
        feasible, discarded_count = preprocess_validated_surgeries(items, shift_config)
        ordered = order_processed_surgeries(feasible)
        selected = select_greedy_processed_surgeries(ordered)

        elapsed_ns = time.perf_counter_ns() - start_ns
        return SchedulingResult(
            algorithm_name=self.name,
            selected_surgeries=selected,
            total_selected=len(selected),
            discarded_infeasible_count=discarded_count,
            elapsed_ns=elapsed_ns,
        )
