"""Contratos de interface, ordenação e núcleo compartilhado de escalonamento."""

import bisect
from collections.abc import Callable, Sequence
from typing import Protocol, TypeVar, runtime_checkable

from src.domain.models import (
    ProcessedSurgery,
    SchedulingResult,
    ShiftConfig,
    SurgeryRequest,
)
from src.domain.preprocessing import validate_scheduler_inputs

_ItemT = TypeVar("_ItemT")


@runtime_checkable
class IntervalSchedulerProtocol(Protocol):
    """Contrato comum (Inversão de Dependência) para todos os algoritmos de escalonamento."""

    @property
    def name(self) -> str:
        """Retorna o nome identificador do algoritmo."""
        ...

    def schedule(
        self,
        surgeries: Sequence[SurgeryRequest],
        shift_config: ShiftConfig | None = None,
    ) -> SchedulingResult:
        """Executa o escalonamento sobre a lista de cirurgias e retorna o resultado."""
        ...


def _order_sequence_by_key(
    items: list[_ItemT],
    key_fn: Callable[[_ItemT], tuple[int, ...]],
) -> list[_ItemT]:
    """Ordena uma lista de elementos em O(n log n) conforme a chave informada."""
    return sorted(items, key=key_fn)


def order_surgeries_by_key(
    items: list[SurgeryRequest],
    key_fn: Callable[[SurgeryRequest], tuple[int, ...]],
) -> list[SurgeryRequest]:
    """Ordena instâncias de SurgeryRequest em O(n log n) conforme a chave informada."""
    return _order_sequence_by_key(items, key_fn)


def order_processed_surgeries(
    items: list[ProcessedSurgery],
) -> list[ProcessedSurgery]:
    """Ordena cirurgias processadas em O(n log n) por (effective_release_time, finish_time, start_time)."""
    return _order_sequence_by_key(
        items,
        key_fn=lambda item: (
            item.effective_release_time,
            item.request.finish_time,
            item.request.start_time,
        ),
    )


def select_greedy_processed_surgeries(
    ordered: Sequence[ProcessedSurgery],
) -> tuple[ProcessedSurgery, ...]:
    """Executa varredura gulosa linear em O(n) sobre itens ordenados por liberação efetiva."""
    selected: list[ProcessedSurgery] = []
    last_release = -1
    for item in ordered:
        if item.request.start_time >= last_release:
            selected.append(item)
            last_release = item.effective_release_time
    return tuple(selected)


def compute_predecessors_binary_search(
    ordered: Sequence[ProcessedSurgery],
) -> list[int]:
    """Calcula o vetor de predecessores p[1..n] em O(n log n) via busca binária (bisect_right)."""
    n = len(ordered)
    release_times = [item.effective_release_time for item in ordered]
    predecessors = [0] * (n + 1)
    for idx in range(n):
        predecessors[idx + 1] = bisect.bisect_right(
            release_times, ordered[idx].request.start_time, lo=0, hi=idx
        )
    return predecessors


def solve_interval_dp(
    ordered: Sequence[ProcessedSurgery],
) -> tuple[ProcessedSurgery, ...]:
    """Resolve PD não ponderada de intervalos em O(n log n) e reconstrói a solução ótima."""
    n = len(ordered)
    if n == 0:
        return ()

    predecessors = compute_predecessors_binary_search(ordered)

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
    "compute_predecessors_binary_search",
    "order_processed_surgeries",
    "order_surgeries_by_key",
    "select_greedy_processed_surgeries",
    "solve_interval_dp",
    "validate_scheduler_inputs",
]
