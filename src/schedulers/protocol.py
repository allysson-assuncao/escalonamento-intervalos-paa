"""Contratos de interface, ordenação e núcleo compartilhado de escalonamento."""

import bisect
from collections.abc import Callable, Sequence
from typing import Protocol, TypeVar, runtime_checkable

from src.domain.exceptions import InvalidSchedulingInputError
from src.domain.models import (
    ProcessedSurgery,
    SchedulingResult,
    ShiftConfig,
    SurgeryRequest,
    is_strict_int,
)
from src.domain.preprocessing import validate_scheduler_inputs

_ItemT = TypeVar("_ItemT")


@runtime_checkable
class IntervalSchedulerProtocol(Protocol):
    """Contrato comum (Dependency Inversion) para todos os algoritmos de escalonamento."""

    @property
    def name(self) -> str:
        """Retorna o nome identificador do algoritmo."""
        ...

    def schedule(
        self,
        surgeries: Sequence[SurgeryRequest],
        shift_config: ShiftConfig | None = None,
        *,
        is_presorted: bool = False,
    ) -> SchedulingResult:
        """Executa o escalonamento sobre a lista de cirurgias e retorna o resultado."""
        ...


def _order_sequence_by_key(
    items: list[_ItemT],
    key_fn: Callable[[_ItemT], tuple[int, ...]],
    *,
    is_presorted: bool,
) -> list[_ItemT]:
    """Ordena ou valida pré-ordenação em O(n) conforme o critério informado."""
    if not is_presorted:
        items.sort(key=key_fn)
        return items

    for index in range(1, len(items)):
        if key_fn(items[index]) < key_fn(items[index - 1]):
            raise InvalidSchedulingInputError(
                "A sequência fornecida com is_presorted=True não está devidamente ordenada."
            )
    return items


def order_surgeries_by_key(
    items: list[SurgeryRequest],
    key_fn: Callable[[SurgeryRequest], tuple[int, ...]],
    *,
    is_presorted: bool,
) -> list[SurgeryRequest]:
    """Ordena ou valida pré-ordenação de SurgeryRequest conforme a chave informada."""
    return _order_sequence_by_key(items, key_fn, is_presorted=is_presorted)


def order_processed_surgeries(
    items: list[ProcessedSurgery],
    *,
    is_presorted: bool,
) -> list[ProcessedSurgery]:
    """Ordena ou valida pré-ordenação por (effective_release_time, finish_time, start_time)."""
    return _order_sequence_by_key(
        items,
        key_fn=lambda item: (
            item.effective_release_time,
            item.request.finish_time,
            item.request.start_time,
        ),
        is_presorted=is_presorted,
    )


def select_greedy_processed_surgeries(
    ordered: Sequence[ProcessedSurgery],
) -> tuple[ProcessedSurgery, ...]:
    """Executa varredura gulosa linear sobre itens já ordenados por liberação efetiva."""
    selected: list[ProcessedSurgery] = []
    last_release = -1
    for item in ordered:
        if item.request.start_time >= last_release:
            selected.append(item)
            last_release = item.effective_release_time
    return tuple(selected)


def _extract_start_time(item: SurgeryRequest | ProcessedSurgery) -> int:
    """Obtém o horário de início de SurgeryRequest ou ProcessedSurgery."""
    if isinstance(item, ProcessedSurgery):
        return item.request.start_time
    return item.start_time


def validate_presorted_start_indices(
    items: Sequence[SurgeryRequest | ProcessedSurgery],
    start_indices: Sequence[int],
) -> Sequence[int]:
    """Valida que start_indices é permutação de 0..n-1 em ordem não decrescente de início."""
    if (
        isinstance(start_indices, (str, bytes))
        or not isinstance(start_indices, Sequence)
        or len(start_indices) != len(items)
    ):
        raise InvalidSchedulingInputError(
            "presorted_start_indices deve ser uma sequência com o mesmo tamanho dos itens viáveis."
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
        curr_start = _extract_start_time(items[idx])
        if curr_start < prev_start:
            raise InvalidSchedulingInputError(
                "Os índices fornecidos em presorted_start_indices não estão ordenados por início."
            )
        prev_start = curr_start
    return start_indices


def _are_starts_monotonic(items: Sequence[ProcessedSurgery]) -> bool:
    """Verifica em O(n) se start_time já é não decrescente na ordem atual."""
    for index in range(1, len(items)):
        if items[index].request.start_time < items[index - 1].request.start_time:
            return False
    return True


def _compute_predecessors_two_pointers(
    ordered: Sequence[ProcessedSurgery],
    start_order: Sequence[int],
) -> list[int]:
    """Calcula p(i) em O(n) utilizando varredura monótona com dois ponteiros."""
    predecessors = [0] * (len(ordered) + 1)
    release_ptr = 0
    for idx in start_order:
        start_val = ordered[idx].request.start_time
        while (
            release_ptr < idx
            and ordered[release_ptr].effective_release_time <= start_val
        ):
            release_ptr += 1
        predecessors[idx + 1] = release_ptr
    return predecessors


def _compute_predecessors_binary_search(
    ordered: Sequence[ProcessedSurgery],
) -> list[int]:
    """Calcula p(i) em O(n log n) com busca binária sobre as liberações ordenadas."""
    n = len(ordered)
    release_times = [item.effective_release_time for item in ordered]
    predecessors = [0] * (n + 1)
    for idx in range(n):
        predecessors[idx + 1] = bisect.bisect_right(
            release_times, ordered[idx].request.start_time, lo=0, hi=idx
        )
    return predecessors


def _resolve_predecessors(
    ordered: Sequence[ProcessedSurgery],
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


def solve_interval_dp(
    ordered: Sequence[ProcessedSurgery],
    *,
    is_presorted: bool = False,
    validated_start_order: Sequence[int] | None = None,
) -> tuple[ProcessedSurgery, ...]:
    """Resolve PD não ponderada de intervalos e reconstrói a solução ótima iterativamente."""
    n = len(ordered)
    if n == 0:
        return ()

    predecessors = _resolve_predecessors(
        ordered,
        is_presorted=is_presorted,
        validated_start_order=validated_start_order,
    )

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
    return tuple(ordered[idx] for idx in selected_indices)


__all__ = [
    "IntervalSchedulerProtocol",
    "order_processed_surgeries",
    "order_surgeries_by_key",
    "select_greedy_processed_surgeries",
    "solve_interval_dp",
    "validate_presorted_start_indices",
    "validate_scheduler_inputs",
]
