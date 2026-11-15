"""Contratos de interface e utilitários compartilhados dos escalonadores."""

from collections.abc import Callable, Sequence
from typing import Protocol, runtime_checkable

from src.domain.exceptions import InvalidSchedulingInputError
from src.domain.models import SchedulingResult, ShiftConfig, SurgeryRequest


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


def validate_scheduler_inputs(
    surgeries: Sequence[SurgeryRequest],
    shift_config: ShiftConfig | None,
) -> list[SurgeryRequest]:
    """Valida os argumentos de entrada e cria cópia defensiva da sequência de cirurgias."""
    if surgeries is None or isinstance(surgeries, (str, bytes)) or not isinstance(
        surgeries, Sequence
    ):
        raise InvalidSchedulingInputError(
            "A entrada de cirurgias deve ser uma sequência válida de SurgeryRequest."
        )
    if shift_config is not None and not isinstance(shift_config, ShiftConfig):
        raise InvalidSchedulingInputError(
            "A configuração de turno deve ser ShiftConfig ou None."
        )

    copied: list[SurgeryRequest] = []
    for item in surgeries:
        if not isinstance(item, SurgeryRequest):
            raise InvalidSchedulingInputError(
                "Todos os elementos da sequência devem ser instâncias de SurgeryRequest."
            )
        copied.append(item)
    return copied


def order_surgeries_by_key(
    items: list[SurgeryRequest],
    key_fn: Callable[[SurgeryRequest], tuple[int, ...]],
    *,
    is_presorted: bool,
) -> list[SurgeryRequest]:
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
