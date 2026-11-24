"""Pré-processamento de viabilidade ativa e cálculo da liberação efetiva r_i."""

from collections.abc import Sequence

from src.domain.exceptions import InvalidSchedulingInputError
from src.domain.models import (
    ProcessedSurgery,
    ShiftConfig,
    SurgeryRequest,
)


def validate_scheduler_inputs(
    surgeries: Sequence[SurgeryRequest],
    shift_config: ShiftConfig | None,
) -> list[SurgeryRequest]:
    """Valida os argumentos de entrada e cria cópia defensiva da sequência de cirurgias."""
    if (
        surgeries is None
        or isinstance(surgeries, (str, bytes))
        or not isinstance(surgeries, Sequence)
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


def is_actively_feasible(
    surgery: SurgeryRequest,
    shift_config: ShiftConfig | None,
) -> bool:
    """Verifica se a atuação médica [s_i, f_i] respeita H e a janela [A, B]."""
    if not isinstance(surgery, SurgeryRequest):
        raise InvalidSchedulingInputError(
            "A cirurgia informada deve ser uma instância de SurgeryRequest."
        )
    if shift_config is None:
        return True
    if not isinstance(shift_config, ShiftConfig):
        raise InvalidSchedulingInputError(
            "A configuração de turno deve ser ShiftConfig ou None."
        )

    if surgery.finish_time > shift_config.closing_horizon:
        return False

    window = shift_config.shift_window
    if window is not None:
        return surgery.finish_time <= window.start or surgery.start_time >= window.end
    return True


def compute_effective_release_time(
    surgery: SurgeryRequest,
    shift_config: ShiftConfig | None,
) -> int:
    """Calcula r_i em O(1) considerando esterilização passiva e absorção por [A, B]."""
    if not isinstance(surgery, SurgeryRequest):
        raise InvalidSchedulingInputError(
            "A cirurgia informada deve ser uma instância de SurgeryRequest."
        )
    if shift_config is not None and not isinstance(shift_config, ShiftConfig):
        raise InvalidSchedulingInputError(
            "A configuração de turno deve ser ShiftConfig ou None."
        )

    raw_end = surgery.finish_time + surgery.sterilization_duration
    if shift_config is not None and shift_config.shift_window is not None:
        window = shift_config.shift_window
        if (
            surgery.finish_time <= window.start
            and window.start < raw_end < window.end
        ):
            return window.end
    return raw_end


def preprocess_validated_surgeries(
    items: Sequence[SurgeryRequest],
    shift_config: ShiftConfig | None = None,
) -> tuple[list[ProcessedSurgery], int]:
    """Filtra cirurgias ativamente viáveis e calcula r_i para sequência já validada."""
    feasible: list[ProcessedSurgery] = []
    discarded_count = 0

    for surgery in items:
        if is_actively_feasible(surgery, shift_config):
            release_time = compute_effective_release_time(surgery, shift_config)
            feasible.append(
                ProcessedSurgery(
                    request=surgery,
                    effective_release_time=release_time,
                )
            )
        else:
            discarded_count += 1

    return feasible, discarded_count


def preprocess_feasible_surgeries(
    surgeries: Sequence[SurgeryRequest],
    shift_config: ShiftConfig | None = None,
) -> tuple[list[ProcessedSurgery], int]:
    """Valida entradas, filtra cirurgias viáveis e calcula r_i em O(n)."""
    items = validate_scheduler_inputs(surgeries, shift_config)
    return preprocess_validated_surgeries(items, shift_config)
