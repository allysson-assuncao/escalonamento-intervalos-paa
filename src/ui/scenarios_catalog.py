"""Catálogo canônico compartilhado de cenários didáticos CASE-01 a CASE-04."""

from dataclasses import dataclass

from src.domain.exceptions import InvalidSchedulingInputError
from src.domain.models import ShiftConfig, ShiftWindow, SurgeryRequest, SurgeryType

DEFAULT_CLOSING_HORIZON: int = 1080  # 18:00 em minutos
DEFAULT_SHIFT_WINDOW: ShiftWindow = ShiftWindow(start=720, end=780)  # 12:00-13:00


@dataclass(frozen=True)
class ScenarioPreset:
    """Metadados e dados imutáveis de um cenário didático pré-configurado."""

    scenario_id: str
    title: str
    description: str
    surgeries: tuple[SurgeryRequest, ...]
    shift_config: ShiftConfig | None


def build_case01_classic_baseline() -> tuple[list[SurgeryRequest], ShiftConfig]:
    """Retorna CASE-01: apenas cirurgias limpas (todos os 4 algoritmos empatam em 3)."""
    surgeries = [
        SurgeryRequest(surgery_id="S2", start_time=540, finish_time=720),   # 09:00-12:00
        SurgeryRequest(surgery_id="S4", start_time=690, finish_time=810),   # 11:30-13:30
        SurgeryRequest(surgery_id="S1", start_time=480, finish_time=600),   # 08:00-10:00
        SurgeryRequest(surgery_id="S3", start_time=600, finish_time=690),   # 10:00-11:30
    ]
    shift_config = ShiftConfig(closing_horizon=DEFAULT_CLOSING_HORIZON)
    return surgeries, shift_config


def build_case02_sterilization_and_horizon() -> tuple[list[SurgeryRequest], ShiftConfig]:
    """Retorna CASE-02: contrexemplo de esterilização c_i e horizonte H (ótimo = {S2, S3})."""
    surgeries = [
        SurgeryRequest(
            surgery_id="S1",
            start_time=780,   # 13:00
            finish_time=840,  # 14:00
            surgery_type=SurgeryType.CONTAMINATED,
            sterilization_duration=120,  # r_1 = 16:00 (960)
        ),
        SurgeryRequest(
            surgery_id="S2",
            start_time=810,   # 13:30
            finish_time=900,  # 15:00
            surgery_type=SurgeryType.CLEAN,
            sterilization_duration=0,    # r_2 = 15:00 (900)
        ),
        SurgeryRequest(
            surgery_id="S3",
            start_time=900,    # 15:00
            finish_time=1065,  # 17:45
            surgery_type=SurgeryType.CONTAMINATED,
            sterilization_duration=60,   # r_3 = 18:45 (1125 > H)
        ),
    ]
    shift_config = ShiftConfig(closing_horizon=DEFAULT_CLOSING_HORIZON)
    return surgeries, shift_config


def build_case03_shift_window() -> tuple[list[SurgeryRequest], ShiftConfig]:
    """Retorna CASE-03: janela de troca de plantão [12:00, 13:00] e salto r_1 = B."""
    surgeries = [
        SurgeryRequest(
            surgery_id="S1",
            start_time=600,   # 10:00
            finish_time=690,  # 11:30
            surgery_type=SurgeryType.CONTAMINATED,
            sterilization_duration=60,  # e_1 = 12:30 dentro de [12:00, 13:00) -> r_1 = 13:00
        ),
        SurgeryRequest(
            surgery_id="S2",
            start_time=690,   # 11:30
            finish_time=750,  # 12:30 (invade [12:00, 13:00) -> descartada)
            surgery_type=SurgeryType.CLEAN,
        ),
        SurgeryRequest(
            surgery_id="S3",
            start_time=750,   # 12:30
            finish_time=840,  # 14:00 (invade [12:00, 13:00) -> descartada)
            surgery_type=SurgeryType.CLEAN,
        ),
        SurgeryRequest(
            surgery_id="S4",
            start_time=780,   # 13:00 (>= r_1 = 13:00)
            finish_time=900,  # 15:00
            surgery_type=SurgeryType.CONTAMINATED,
            sterilization_duration=30,  # r_4 = 15:30
        ),
        SurgeryRequest(
            surgery_id="S5",
            start_time=930,   # 15:30 (>= r_4 = 15:30)
            finish_time=1050, # 17:30
            surgery_type=SurgeryType.CLEAN,
        ),
    ]
    shift_config = ShiftConfig(
        closing_horizon=DEFAULT_CLOSING_HORIZON,
        shift_window=DEFAULT_SHIFT_WINDOW,
    )
    return surgeries, shift_config


def build_case04_full_mixed_shift() -> tuple[list[SurgeryRequest], ShiftConfig]:
    """Retorna CASE-04: turno hospitalar completo com 7 cirurgias mistas (ótimo = 4)."""
    surgeries = [
        SurgeryRequest(
            surgery_id="S1",
            start_time=480,   # 08:00
            finish_time=570,  # 09:30
            surgery_type=SurgeryType.CONTAMINATED,
            sterilization_duration=60,  # r_1 = 10:30
        ),
        SurgeryRequest(
            surgery_id="S2",
            start_time=540,   # 09:00
            finish_time=615,  # 10:15
            surgery_type=SurgeryType.CLEAN,  # r_2 = 10:15 (< r_1)
        ),
        SurgeryRequest(
            surgery_id="S3",
            start_time=615,   # 10:15
            finish_time=705,  # 11:45
            surgery_type=SurgeryType.CONTAMINATED,
            sterilization_duration=45,  # e_3 = 12:30 -> r_3 = 13:00
        ),
        SurgeryRequest(
            surgery_id="S4",
            start_time=705,   # 11:45
            finish_time=765,  # 12:45 (sobrepõe [12:00, 13:00) -> descartada)
            surgery_type=SurgeryType.CLEAN,
        ),
        SurgeryRequest(
            surgery_id="S5",
            start_time=780,   # 13:00
            finish_time=870,  # 14:30
            surgery_type=SurgeryType.CONTAMINATED,
            sterilization_duration=90,  # r_5 = 16:00
        ),
        SurgeryRequest(
            surgery_id="S6",
            start_time=840,   # 14:00
            finish_time=930,  # 15:30
            surgery_type=SurgeryType.CLEAN,  # r_6 = 15:30 (< r_5)
        ),
        SurgeryRequest(
            surgery_id="S7",
            start_time=930,   # 15:30
            finish_time=1060, # 17:40
            surgery_type=SurgeryType.CONTAMINATED,
            sterilization_duration=40,  # r_7 = 18:20 (> H, mas f_7 <= H)
        ),
    ]
    shift_config = ShiftConfig(
        closing_horizon=DEFAULT_CLOSING_HORIZON,
        shift_window=DEFAULT_SHIFT_WINDOW,
    )
    return surgeries, shift_config


def get_scenario_presets() -> tuple[ScenarioPreset, ...]:
    """Retorna os 4 cenários didáticos prontos para demonstração na interface."""
    case01_surgeries, case01_cfg = build_case01_classic_baseline()
    case02_surgeries, case02_cfg = build_case02_sterilization_and_horizon()
    case03_surgeries, case03_cfg = build_case03_shift_window()
    case04_surgeries, case04_cfg = build_case04_full_mixed_shift()

    return (
        ScenarioPreset(
            scenario_id="CASE-01",
            title="1. Baseline Clássico (Apenas Cirurgias Limpas)",
            description=(
                "4 cirurgias limpas (c_i = 0) sem janela de plantão. "
                "Mostra o funcionamento idêntico dos 4 algoritmos convergindo para {S1, S3, S4} (3 cirurgias)."
            ),
            surgeries=tuple(case01_surgeries),
            shift_config=case01_cfg,
        ),
        ScenarioPreset(
            scenario_id="CASE-02",
            title="2. Impacto da Esterilização (c_i) e Horizonte (H)",
            description=(
                "Contrexemplo principal: S1 (13:00-14:00 + 2h de ozônio) engana os clássicos, "
                "gerando conflito com S3 (15:00-17:45 + 1h após H=18:00). "
                "Os adaptados encontram o ótimo válido {S2, S3} (2 cirurgias)."
            ),
            surgeries=tuple(case02_surgeries),
            shift_config=case02_cfg,
        ),
        ScenarioPreset(
            scenario_id="CASE-03",
            title="3. Janela de Troca de Plantão [A, B]",
            description=(
                "Janela [12:00, 13:00]: S2 e S3 invadem a troca com equipe ativa e são descartadas; "
                "a esterilização de S1 termina às 12:30 dentro da pausa, ajustando r_1 para 13:00 e liberando {S1, S4, S5}."
            ),
            surgeries=tuple(case03_surgeries),
            shift_config=case03_cfg,
        ),
        ScenarioPreset(
            scenario_id="CASE-04",
            title="4. Turno Hospitalar Completo (7 Cirurgias Mistas)",
            description=(
                "Turno de 08:00 às 18:00 com pausa [12:00, 13:00] e 7 cirurgias mistas: "
                "evidencia busca binária p[i], preenchimento de DP[i], backtracking e 4 cirurgias válidas ({S2, S3, S6, S7})."
            ),
            surgeries=tuple(case04_surgeries),
            shift_config=case04_cfg,
        ),
    )


def get_scenario_by_id(scenario_id: str) -> ScenarioPreset:
    """Busca um cenário pré-configurado pelo identificador (insensível a maiúsculas)."""
    if not isinstance(scenario_id, str) or not scenario_id.strip():
        raise InvalidSchedulingInputError(
            "O identificador do cenário deve ser uma string não vazia."
        )
    normalized = scenario_id.strip().lower()
    for preset in get_scenario_presets():
        if preset.scenario_id.lower() == normalized:
            return preset
    available = ", ".join(preset.scenario_id for preset in get_scenario_presets())
    raise InvalidSchedulingInputError(
        f"Cenário '{scenario_id}' não encontrado. Opções válidas: {available}."
    )
