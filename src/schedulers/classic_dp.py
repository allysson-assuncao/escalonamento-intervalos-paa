"""Implementação da Programação Dinâmica Clássica (Unweighted Interval Scheduling)."""

import bisect
from collections.abc import Sequence
import time

from src.domain.exceptions import InvalidSchedulingInputError
from src.domain.models import (
    ProcessedSurgery,
    SchedulingResult,
    ShiftConfig,
    SurgeryRequest,
    is_strict_int,
)
from src.schedulers.protocol import order_surgeries_by_key, validate_scheduler_inputs


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
            validated_start_order = _validate_presorted_start_indices(
                items, presorted_start_indices
            )

        # Modo clássico puro ignora shift_config e sterilization_duration propositalmente
        start_ns = time.perf_counter_ns()
        ordered = order_surgeries_by_key(
            items,
            key_fn=lambda item: (item.finish_time, item.start_time),
            is_presorted=is_presorted,
        )

        if not ordered:
            elapsed_ns = time.perf_counter_ns() - start_ns
            return SchedulingResult(
                algorithm_name=self.name,
                selected_surgeries=(),
                total_selected=0,
                discarded_infeasible_count=0,
                elapsed_ns=elapsed_ns,
            )

        predecessors = _resolve_predecessors(
            ordered,
            is_presorted=is_presorted,
            validated_start_order=validated_start_order,
        )
        selected = _solve_dp_and_reconstruct(ordered, predecessors)

        elapsed_ns = time.perf_counter_ns() - start_ns
        return SchedulingResult(
            algorithm_name=self.name,
            selected_surgeries=selected,
            total_selected=len(selected),
            discarded_infeasible_count=0,
            elapsed_ns=elapsed_ns,
        )


def _validate_presorted_start_indices(
    items: Sequence[SurgeryRequest],
    start_indices: Sequence[int],
) -> Sequence[int]:
    """Valida que start_indices é permutação de 0..n-1 em ordem não decrescente de início."""
    if (
        isinstance(start_indices, (str, bytes))
        or not isinstance(start_indices, Sequence)
        or len(start_indices) != len(items)
    ):
        raise InvalidSchedulingInputError(
            "presorted_start_indices deve ser uma sequência com o mesmo tamanho de surgeries."
        )

    n = len(items)
    seen = [False] * n
    prev_start = -1
    for idx in start_indices:
        if not is_strict_int(idx) or idx < 0 or idx >= n or seen[idx]:
            raise InvalidSchedulingInputError(
                "presorted_start_indices deve conter uma permutação válida de 0 a n-1."
            )
        seen[idx] = True
        curr_start = items[idx].start_time
        if curr_start < prev_start:
            raise InvalidSchedulingInputError(
                "Os índices fornecidos em presorted_start_indices não estão ordenados por início."
            )
        prev_start = curr_start
    return start_indices


def _are_starts_monotonic(items: Sequence[SurgeryRequest]) -> bool:
    """Verifica em O(n) se start_time já é não decrescente na ordem atual."""
    for index in range(1, len(items)):
        if items[index].start_time < items[index - 1].start_time:
            return False
    return True


def _resolve_predecessors(
    ordered: Sequence[SurgeryRequest],
    *,
    is_presorted: bool,
    validated_start_order: Sequence[int] | None,
) -> list[int]:
    """Seleciona cálculo de predecessores em O(n) com dois ponteiros ou O(n log n) via bisect."""
    if is_presorted and validated_start_order is not None:
        return _compute_predecessors_two_pointers(ordered, validated_start_order)
    if is_presorted and _are_starts_monotonic(ordered):
        return _compute_predecessors_two_pointers(ordered, range(len(ordered)))
    return _compute_predecessors_binary_search(ordered)


def _compute_predecessors_two_pointers(
    ordered: Sequence[SurgeryRequest],
    start_order: Sequence[int],
) -> list[int]:
    """Calcula p(i) em O(n) utilizando varredura monótona com dois ponteiros."""
    predecessors = [0] * (len(ordered) + 1)
    finish_ptr = 0
    for idx in start_order:
        start_val = ordered[idx].start_time
        while finish_ptr < idx and ordered[finish_ptr].finish_time <= start_val:
            finish_ptr += 1
        predecessors[idx + 1] = finish_ptr
    return predecessors


def _compute_predecessors_binary_search(
    ordered: Sequence[SurgeryRequest],
) -> list[int]:
    """Calcula p(i) em O(n log n) com busca binária sobre os términos ordenados."""
    n = len(ordered)
    finish_times = [item.finish_time for item in ordered]
    predecessors = [0] * (n + 1)
    for idx in range(n):
        predecessors[idx + 1] = bisect.bisect_right(
            finish_times, ordered[idx].start_time, lo=0, hi=idx
        )
    return predecessors


def _solve_dp_and_reconstruct(
    ordered: Sequence[SurgeryRequest],
    predecessors: Sequence[int],
) -> tuple[ProcessedSurgery, ...]:
    """Preenche a tabela DP[0..n] e reconstrói a solução ótima de forma iterativa."""
    n = len(ordered)
    dp = [0] * (n + 1)
    for i in range(1, n + 1):
        include_count = 1 + dp[predecessors[i]]
        exclude_count = dp[i - 1]
        dp[i] = include_count if include_count > exclude_count else exclude_count

    selected_indices: list[int] = []
    current = n
    while current > 0:
        if 1 + dp[predecessors[current]] > dp[current - 1]:
            selected_indices.append(current - 1)
            current = predecessors[current]
        else:
            current -= 1

    selected_indices.reverse()
    return tuple(
        ProcessedSurgery(
            request=ordered[idx],
            effective_release_time=ordered[idx].finish_time,
        )
        for idx in selected_indices
    )
