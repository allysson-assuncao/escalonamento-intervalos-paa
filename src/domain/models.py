"""Modelos de domínio imutáveis para o problema de escalonamento de cirurgias."""

from dataclasses import dataclass
from enum import Enum

from src.domain.exceptions import InvalidSchedulingInputError


def is_strict_int(value: object) -> bool:
    """Verifica se o valor é um inteiro estrito (excluindo booleanos)."""
    return isinstance(value, int) and not isinstance(value, bool)


class SurgeryType(str, Enum):
    """Classificação de risco biológico da cirurgia."""

    CLEAN = "CLEAN"
    CONTAMINATED = "CONTAMINATED"


@dataclass(frozen=True)
class ShiftWindow:
    """Janela fixa de troca de plantão ou interdição [start, end)."""

    start: int
    end: int

    def __post_init__(self) -> None:
        """Valida que os limites da janela são inteiros não negativos com start < end."""
        if not is_strict_int(self.start) or not is_strict_int(self.end):
            raise InvalidSchedulingInputError(
                "Os limites da janela de turno devem ser números inteiros."
            )
        if self.start < 0:
            raise InvalidSchedulingInputError(
                "O início da janela de turno não pode ser negativo."
            )
        if self.start >= self.end:
            raise InvalidSchedulingInputError(
                "O início da janela de turno deve ser estritamente menor que o fim."
            )


@dataclass(frozen=True)
class ShiftConfig:
    """Configuração de expediente médico e janela opcional de troca de plantão."""

    closing_horizon: int
    shift_window: ShiftWindow | None = None

    def __post_init__(self) -> None:
        """Valida o horizonte de fechamento H e a consistência da janela [A, B]."""
        if not is_strict_int(self.closing_horizon):
            raise InvalidSchedulingInputError(
                "O horizonte de fechamento deve ser um número inteiro."
            )
        if self.closing_horizon <= 0:
            raise InvalidSchedulingInputError(
                "O horizonte de fechamento deve ser estritamente positivo."
            )
        if self.shift_window is not None:
            if not isinstance(self.shift_window, ShiftWindow):
                raise InvalidSchedulingInputError(
                    "A janela de troca de plantão deve ser uma instância de ShiftWindow."
                )
            if self.shift_window.end > self.closing_horizon:
                raise InvalidSchedulingInputError(
                    "O fim da janela de turno não pode ultrapassar o horizonte de fechamento."
                )


@dataclass(frozen=True)
class SurgeryRequest:
    """Solicitação imutável de cirurgia com intervalo ativo e protocolo biológico."""

    surgery_id: str
    start_time: int
    finish_time: int
    surgery_type: SurgeryType = SurgeryType.CLEAN
    sterilization_duration: int = 0

    def __post_init__(self) -> None:
        """Valida invariantes temporais, identificador e coerência biológica."""
        if not isinstance(self.surgery_id, str) or not self.surgery_id.strip():
            raise InvalidSchedulingInputError(
                "O identificador da cirurgia (surgery_id) deve ser uma string não vazia."
            )
        if not is_strict_int(self.start_time) or not is_strict_int(self.finish_time):
            raise InvalidSchedulingInputError(
                "Os horários de início e término da cirurgia devem ser números inteiros."
            )
        if self.start_time < 0:
            raise InvalidSchedulingInputError(
                "O horário de início da cirurgia não pode ser negativo."
            )
        if self.start_time >= self.finish_time:
            raise InvalidSchedulingInputError(
                "O horário de início deve ser estritamente menor que o horário de término."
            )
        if not isinstance(self.surgery_type, SurgeryType):
            raise InvalidSchedulingInputError(
                "O tipo da cirurgia deve ser um membro válido de SurgeryType."
            )
        if not is_strict_int(self.sterilization_duration):
            raise InvalidSchedulingInputError(
                "A duração de esterilização deve ser um número inteiro."
            )
        if self.sterilization_duration < 0:
            raise InvalidSchedulingInputError(
                "A duração de esterilização não pode ser negativa."
            )
        if self.surgery_type == SurgeryType.CLEAN and self.sterilization_duration != 0:
            raise InvalidSchedulingInputError(
                "Cirurgias limpas (CLEAN) devem ter duração de esterilização igual a zero."
            )
        if (
            self.surgery_type == SurgeryType.CONTAMINATED
            and self.sterilization_duration <= 0
        ):
            raise InvalidSchedulingInputError(
                "Cirurgias contaminadas (CONTAMINATED) exigem esterilização maior que zero."
            )


@dataclass(frozen=True)
class ProcessedSurgery:
    """Cirurgia processada com seu instante de liberação efetiva da sala."""

    request: SurgeryRequest
    effective_release_time: int

    def __post_init__(self) -> None:
        """Valida que o instante de liberação efetiva não antecede o término médico."""
        if not isinstance(self.request, SurgeryRequest):
            raise InvalidSchedulingInputError(
                "O campo request deve ser uma instância de SurgeryRequest."
            )
        if not is_strict_int(self.effective_release_time):
            raise InvalidSchedulingInputError(
                "O instante de liberação efetiva deve ser um número inteiro."
            )
        if self.effective_release_time < self.request.finish_time:
            raise InvalidSchedulingInputError(
                "O instante de liberação efetiva não pode ser menor que o término da cirurgia."
            )


@dataclass(frozen=True)
class SchedulingResult:
    """Resultado consolidado da execução de um algoritmo de escalonamento."""

    algorithm_name: str
    selected_surgeries: tuple[ProcessedSurgery, ...]
    total_selected: int
    discarded_infeasible_count: int
    elapsed_ns: int

    def __post_init__(self) -> None:
        """Valida consistência entre contagem, itens selecionados e métricas."""
        if not isinstance(self.algorithm_name, str) or not self.algorithm_name.strip():
            raise InvalidSchedulingInputError(
                "O nome do algoritmo deve ser uma string não vazia."
            )
        if not isinstance(self.selected_surgeries, tuple) or not all(
            isinstance(item, ProcessedSurgery) for item in self.selected_surgeries
        ):
            raise InvalidSchedulingInputError(
                "Os itens selecionados devem formar uma tupla de ProcessedSurgery."
            )
        if not is_strict_int(self.total_selected) or self.total_selected != len(
            self.selected_surgeries
        ):
            raise InvalidSchedulingInputError(
                "O total selecionado deve coincidir com a quantidade de cirurgias selecionadas."
            )
        if (
            not is_strict_int(self.discarded_infeasible_count)
            or self.discarded_infeasible_count < 0
        ):
            raise InvalidSchedulingInputError(
                "A contagem de cirurgias inviáveis descartadas não pode ser negativa."
            )
        if not is_strict_int(self.elapsed_ns) or self.elapsed_ns < 0:
            raise InvalidSchedulingInputError(
                "O tempo de execução em nanossegundos não pode ser negativo."
            )
