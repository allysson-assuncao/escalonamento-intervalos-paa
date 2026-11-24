"""Implementação da Programação Dinâmica Adaptada para escalonamento cirúrgico."""

from collections.abc import Sequence
import time

from src.domain.models import SchedulingResult, ShiftConfig, SurgeryRequest
from src.domain.preprocessing import (
    preprocess_validated_surgeries,
    validate_scheduler_inputs,
)
from src.schedulers.protocol import (
    order_processed_surgeries,
    solve_interval_dp,
)


class AdaptedDPScheduler:
    """Escalonador por Programação Dinâmica adaptado para esterilização e turno [A, B]."""

    @property
    def name(self) -> str:
        """Retorna o nome descritivo da Programação Dinâmica adaptada."""
        return "Adapted Dynamic Programming"

    def schedule(
        self,
        surgeries: Sequence[SurgeryRequest],
        shift_config: ShiftConfig | None = None,
    ) -> SchedulingResult:
        """Calcula subconjunto ótimo adaptado em O(n log n) com busca binária sobre r_i e backtracking."""
        items = validate_scheduler_inputs(surgeries, shift_config)

        start_ns = time.perf_counter_ns()
        feasible, discarded_count = preprocess_validated_surgeries(items, shift_config)
        ordered = order_processed_surgeries(feasible)
        selected = solve_interval_dp(ordered)

        elapsed_ns = time.perf_counter_ns() - start_ns
        return SchedulingResult(
            algorithm_name=self.name,
            selected_surgeries=selected,
            total_selected=len(selected),
            discarded_infeasible_count=discarded_count,
            elapsed_ns=elapsed_ns,
        )
