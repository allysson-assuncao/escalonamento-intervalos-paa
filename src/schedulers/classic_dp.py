"""Implementação da Programação Dinâmica Clássica (Unweighted Interval Scheduling)."""

from collections.abc import Sequence
import time

from src.domain.models import (
    ProcessedSurgery,
    SchedulingResult,
    ShiftConfig,
    SurgeryRequest,
)
from src.schedulers.protocol import (
    order_processed_surgeries,
    solve_interval_dp,
    validate_scheduler_inputs,
)


class ClassicDPScheduler:
    """Escalonador clássico por Programação Dinâmica operando sobre [s_i, f_i]."""

    @property
    def name(self) -> str:
        """Retorna o nome descritivo do algoritmo clássico com Programação Dinâmica."""
        return "Classic Dynamic Programming"

    def schedule(
        self,
        surgeries: Sequence[SurgeryRequest],
        shift_config: ShiftConfig | None = None,
    ) -> SchedulingResult:
        """Calcula o subconjunto ótimo clássico em O(n log n) com busca binária e backtracking."""
        items = validate_scheduler_inputs(surgeries, shift_config)

        # Modo clássico puro ignora shift_config e sterilization_duration propositalmente
        start_ns = time.perf_counter_ns()
        processed = [
            ProcessedSurgery(request=item, effective_release_time=item.finish_time)
            for item in items
        ]
        ordered = order_processed_surgeries(processed)
        selected = solve_interval_dp(ordered)

        elapsed_ns = time.perf_counter_ns() - start_ns
        return SchedulingResult(
            algorithm_name=self.name,
            selected_surgeries=selected,
            total_selected=len(selected),
            discarded_infeasible_count=0,
            elapsed_ns=elapsed_ns,
        )
