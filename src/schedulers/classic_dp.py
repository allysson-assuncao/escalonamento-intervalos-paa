"""Implementação da Programação Dinâmica Clássica (Unweighted Interval Scheduling)."""

from collections.abc import Sequence
import time

from src.domain.exceptions import InvalidSchedulingInputError
from src.domain.models import (
    ProcessedSurgery,
    SchedulingResult,
    ShiftConfig,
    SurgeryRequest,
)
from src.schedulers.protocol import (
    order_processed_surgeries,
    solve_interval_dp,
    validate_presorted_start_indices,
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
        *,
        is_presorted: bool = False,
        presorted_start_indices: Sequence[int] | None = None,
    ) -> SchedulingResult:
        """Calcula o subconjunto ótimo clássico com busca de predecessores e backtracking."""
        items = validate_scheduler_inputs(surgeries, shift_config)
        if presorted_start_indices is not None and not is_presorted:
            raise InvalidSchedulingInputError(
                "presorted_start_indices só pode ser fornecido quando is_presorted=True."
            )

        # Valida índices de início antes de medir apenas o núcleo do algoritmo
        validated_start_order: Sequence[int] | None = None
        if presorted_start_indices is not None:
            validated_start_order = validate_presorted_start_indices(
                items, presorted_start_indices
            )

        # Modo clássico puro ignora shift_config e sterilization_duration propositalmente
        start_ns = time.perf_counter_ns()
        processed = [
            ProcessedSurgery(request=item, effective_release_time=item.finish_time)
            for item in items
        ]
        ordered = order_processed_surgeries(processed, is_presorted=is_presorted)
        selected = solve_interval_dp(
            ordered,
            is_presorted=is_presorted,
            validated_start_order=validated_start_order,
        )

        elapsed_ns = time.perf_counter_ns() - start_ns
        return SchedulingResult(
            algorithm_name=self.name,
            selected_surgeries=selected,
            total_selected=len(selected),
            discarded_infeasible_count=0,
            elapsed_ns=elapsed_ns,
        )
