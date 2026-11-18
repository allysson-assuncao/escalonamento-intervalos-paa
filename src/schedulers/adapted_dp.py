"""Implementação da Programação Dinâmica Adaptada para escalonamento cirúrgico."""

from collections.abc import Sequence
import time

from src.domain.exceptions import InvalidSchedulingInputError
from src.domain.models import SchedulingResult, ShiftConfig, SurgeryRequest
from src.domain.preprocessing import (
    preprocess_validated_surgeries,
    validate_scheduler_inputs,
)
from src.schedulers.protocol import (
    order_processed_surgeries,
    solve_interval_dp,
    validate_presorted_start_indices,
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
        *,
        is_presorted: bool = False,
        presorted_start_indices: Sequence[int] | None = None,
    ) -> SchedulingResult:
        """Calcula subconjunto ótimo adaptado via predecessores sobre r_i e backtracking."""
        items = validate_scheduler_inputs(surgeries, shift_config)
        if presorted_start_indices is not None and not is_presorted:
            raise InvalidSchedulingInputError(
                "presorted_start_indices só pode ser fornecido quando is_presorted=True."
            )

        start_ns = time.perf_counter_ns()
        feasible, discarded_count = preprocess_validated_surgeries(items, shift_config)

        validated_start_order: Sequence[int] | None = None
        if presorted_start_indices is not None:
            if discarded_count > 0:
                raise InvalidSchedulingInputError(
                    "presorted_start_indices não pode ser fornecido quando cirurgias são descartadas por inviabilidade."
                )
            validated_start_order = validate_presorted_start_indices(
                feasible, presorted_start_indices
            )

        ordered = order_processed_surgeries(feasible, is_presorted=is_presorted)
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
            discarded_infeasible_count=discarded_count,
            elapsed_ns=elapsed_ns,
        )
