"""Implementação comparativa por Redução Estática Ingênua (f'_i = f_i + c_i)."""

from collections.abc import Sequence
import time

from src.domain.models import SchedulingResult, ShiftConfig, SurgeryRequest
from src.domain.preprocessing import (
    preprocess_naive_validated_surgeries,
    validate_scheduler_inputs,
)
from src.schedulers.protocol import (
    order_processed_surgeries,
    select_greedy_processed_surgeries,
)


class NaiveReductionScheduler:
    """Comparador ingênuo que reduz estaticamente o término para f'_i = f_i + c_i."""

    @property
    def name(self) -> str:
        """Retorna o nome descritivo da abordagem por redução estática ingênua."""
        return "Naive Static Reduction (f'_i = f_i + c_i)"

    def schedule(
        self,
        surgeries: Sequence[SurgeryRequest],
        shift_config: ShiftConfig | None = None,
        *,
        is_presorted: bool = False,
    ) -> SchedulingResult:
        """Executa escalonamento guloso após aplicar a redução ingênua contra H e [A, B]."""
        items = validate_scheduler_inputs(surgeries, shift_config)

        start_ns = time.perf_counter_ns()
        feasible, discarded_count = preprocess_naive_validated_surgeries(
            items, shift_config
        )
        ordered = order_processed_surgeries(feasible, is_presorted=is_presorted)
        selected = select_greedy_processed_surgeries(ordered)

        elapsed_ns = time.perf_counter_ns() - start_ns
        return SchedulingResult(
            algorithm_name=self.name,
            selected_surgeries=selected,
            total_selected=len(selected),
            discarded_infeasible_count=discarded_count,
            elapsed_ns=elapsed_ns,
        )
