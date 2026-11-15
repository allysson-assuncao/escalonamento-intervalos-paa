"""Implementação do Algoritmo Guloso Clássico (Earliest Finish Time)."""

from collections.abc import Sequence
import time

from src.domain.models import (
    ProcessedSurgery,
    SchedulingResult,
    ShiftConfig,
    SurgeryRequest,
)
from src.schedulers.protocol import order_surgeries_by_key, validate_scheduler_inputs


class ClassicGreedyScheduler:
    """Escalonador guloso clássico baseado apenas no término médico [s_i, f_i]."""

    @property
    def name(self) -> str:
        """Retorna o nome descritivo do algoritmo clássico guloso."""
        return "Classic Greedy (Earliest Finish Time)"

    def schedule(
        self,
        surgeries: Sequence[SurgeryRequest],
        shift_config: ShiftConfig | None = None,
        *,
        is_presorted: bool = False,
    ) -> SchedulingResult:
        """Seleciona o maior subconjunto compatível priorizando menor término f_i."""
        # Valida e copia a entrada para preservar imutabilidade da coleção do chamador
        items = validate_scheduler_inputs(surgeries, shift_config)

        # Modo clássico puro ignora shift_config e sterilization_duration propositalmente
        start_ns = time.perf_counter_ns()
        ordered = order_surgeries_by_key(
            items,
            key_fn=lambda item: (item.finish_time, item.start_time),
            is_presorted=is_presorted,
        )

        selected: list[ProcessedSurgery] = []
        last_finish = -1
        for surgery in ordered:
            if surgery.start_time >= last_finish:
                selected.append(
                    ProcessedSurgery(
                        request=surgery,
                        effective_release_time=surgery.finish_time,
                    )
                )
                last_finish = surgery.finish_time

        elapsed_ns = time.perf_counter_ns() - start_ns
        return SchedulingResult(
            algorithm_name=self.name,
            selected_surgeries=tuple(selected),
            total_selected=len(selected),
            discarded_infeasible_count=0,
            elapsed_ns=elapsed_ns,
        )
