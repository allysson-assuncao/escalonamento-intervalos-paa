"""Catálogo canônico compartilhado de cenários determinísticos SC-01 a SC-05."""

from dataclasses import dataclass

from src.domain.exceptions import InvalidSchedulingInputError
from src.domain.models import ShiftConfig, ShiftWindow, SurgeryRequest, SurgeryType

DEFAULT_CLOSING_HORIZON: int = 1080  # 18:00 em minutos
DEFAULT_SHIFT_WINDOW: ShiftWindow = ShiftWindow(start=720, end=780)  # 12:00-13:00


@dataclass(frozen=True)
class ScenarioPreset:
    """Metadados e dados imutáveis de um cenário pré-configurado de apresentação."""

    scenario_id: str
    title: str
    description: str
    surgeries: tuple[SurgeryRequest, ...]
    shift_config: ShiftConfig | None


def build_sc01_classic_homogeneous_surgeries() -> list[SurgeryRequest]:
    """Retorna o cenário SC-01 (cirurgias limpas em ordem embaralhada, ótimo = 5)."""
    return [
        SurgeryRequest(surgery_id="C8", start_time=900, finish_time=1020),   # 15:00-17:00
        SurgeryRequest(surgery_id="C2", start_time=510, finish_time=630),    # 08:30-10:30
        SurgeryRequest(surgery_id="C5", start_time=660, finish_time=780),    # 11:00-13:00
        SurgeryRequest(surgery_id="C1", start_time=480, finish_time=570),    # 08:00-09:30
        SurgeryRequest(surgery_id="C7", start_time=750, finish_time=900),    # 12:30-15:00
        SurgeryRequest(surgery_id="C4", start_time=600, finish_time=750),    # 10:00-12:30
        SurgeryRequest(surgery_id="C6", start_time=690, finish_time=720),    # 11:30-12:00
        SurgeryRequest(surgery_id="C3", start_time=570, finish_time=660),    # 09:30-11:00
    ]


def build_monotonic_start_presorted_surgeries() -> list[SurgeryRequest]:
    """Retorna sequência já ordenada por (finish_time, start_time) com inícios monótonos."""
    return [
        SurgeryRequest(surgery_id="M1", start_time=10, finish_time=30),
        SurgeryRequest(surgery_id="M2", start_time=20, finish_time=50),
        SurgeryRequest(surgery_id="M3", start_time=30, finish_time=60),
        SurgeryRequest(surgery_id="M4", start_time=60, finish_time=90),
        SurgeryRequest(surgery_id="M5", start_time=80, finish_time=110),
        SurgeryRequest(surgery_id="M6", start_time=95, finish_time=120),
    ]


def build_sc02_counterexample_surgeries() -> tuple[list[SurgeryRequest], ShiftConfig]:
    """Retorna o contrexemplo canônico SC-02 de 3 cirurgias (ótimo adaptado = {S2, S3})."""
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


def build_sc03_end_of_shift_boundary() -> tuple[list[SurgeryRequest], ShiftConfig]:
    """Retorna SC-03 testando esterilização passiva após H=18:00 e rejeição de f_i > H."""
    surgeries = [
        SurgeryRequest(
            surgery_id="S_END",
            start_time=1040,   # 17:20
            finish_time=1070,  # 17:50
            surgery_type=SurgeryType.CONTAMINATED,
            sterilization_duration=30,  # e = 18:20 (1100 > 1080), porém f = 17:50 <= H
        ),
        SurgeryRequest(
            surgery_id="S_OVER",
            start_time=1050,   # 17:30
            finish_time=1081,  # 18:01 > H (inviável)
            surgery_type=SurgeryType.CLEAN,
        ),
    ]
    shift_config = ShiftConfig(closing_horizon=DEFAULT_CLOSING_HORIZON)
    return surgeries, shift_config


def build_sc04_shift_window_scenarios() -> tuple[dict[str, list[SurgeryRequest]], ShiftConfig]:
    """Retorna subcenários SC-04a, SC-04b e SC-04c sob janela de troca [12:00, 13:00]."""
    shift_config = ShiftConfig(
        closing_horizon=DEFAULT_CLOSING_HORIZON,
        shift_window=DEFAULT_SHIFT_WINDOW,
    )
    scenarios = {
        "SC-04a": [
            SurgeryRequest(surgery_id="OVER_LEFT", start_time=690, finish_time=735),   # 11:30-12:15
            SurgeryRequest(surgery_id="OVER_RIGHT", start_time=750, finish_time=810),  # 12:30-13:30
            SurgeryRequest(surgery_id="TOUCH_PRE", start_time=660, finish_time=720),   # 11:00-12:00
            SurgeryRequest(surgery_id="TOUCH_POST", start_time=780, finish_time=840),  # 13:00-14:00
        ],
        "SC-04b": [
            SurgeryRequest(
                surgery_id="ABSORBED",
                start_time=675,   # 11:15
                finish_time=705,  # 11:45
                surgery_type=SurgeryType.CONTAMINATED,
                sterilization_duration=30,
            ),
            SurgeryRequest(
                surgery_id="NEXT_AT_B",
                start_time=780,   # 13:00
                finish_time=840,  # 14:00
            ),
        ],
        "SC-04c": [
            SurgeryRequest(
                surgery_id="OVERFLOW",
                start_time=675,   # 11:15
                finish_time=705,  # 11:45
                surgery_type=SurgeryType.CONTAMINATED,
                sterilization_duration=90,
            ),
            SurgeryRequest(
                surgery_id="BLOCKED_AT_B",
                start_time=780,   # 13:00 < 13:15
                finish_time=840,  # 14:00
            ),
            SurgeryRequest(
                surgery_id="VALID_AFTER_RELEASE",
                start_time=795,   # 13:15 >= 13:15
                finish_time=855,  # 14:15
            ),
        ],
    }
    return scenarios, shift_config


def build_sc05_edge_case_scenarios() -> tuple[
    tuple[list[SurgeryRequest], ShiftConfig],
    tuple[list[SurgeryRequest], ShiftConfig],
]:
    """Retorna subcasos de borda SC-05 (todas inviáveis e empate em r_i)."""
    shift_config = ShiftConfig(
        closing_horizon=DEFAULT_CLOSING_HORIZON,
        shift_window=DEFAULT_SHIFT_WINDOW,
    )
    all_infeasible = [
        SurgeryRequest(surgery_id="INF_WIN_1", start_time=700, finish_time=740),
        SurgeryRequest(surgery_id="INF_WIN_2", start_time=720, finish_time=760),
        SurgeryRequest(surgery_id="INF_HORIZON", start_time=1020, finish_time=1090),
    ]
    tie_on_release = [
        SurgeryRequest(
            surgery_id="TIE_ABSORBED",
            start_time=675,   # 11:15
            finish_time=705,  # 11:45
            surgery_type=SurgeryType.CONTAMINATED,
            sterilization_duration=45,  # e = 12:30 -> clamp r_i = 780
        ),
        SurgeryRequest(
            surgery_id="TIE_EXACT_B",
            start_time=660,   # 11:00
            finish_time=720,  # 12:00
            surgery_type=SurgeryType.CONTAMINATED,
            sterilization_duration=60,  # e = 13:00 -> r_i = 780
        ),
        SurgeryRequest(
            surgery_id="FOLLOWUP",
            start_time=780,   # 13:00
            finish_time=840,  # 14:00
        ),
    ]
    return (all_infeasible, shift_config), (tie_on_release, shift_config)


def get_scenario_presets() -> tuple[ScenarioPreset, ...]:
    """Retorna todos os cenários canônicos SC-01 a SC-05 prontos para exibição na UI."""
    sc01_surgeries = build_sc01_classic_homogeneous_surgeries()
    sc02_surgeries, sc02_cfg = build_sc02_counterexample_surgeries()
    sc03_surgeries, sc03_cfg = build_sc03_end_of_shift_boundary()
    sc04_map, sc04_cfg = build_sc04_shift_window_scenarios()
    (sc05a_surgeries, sc05a_cfg), (sc05b_surgeries, sc05b_cfg) = (
        build_sc05_edge_case_scenarios()
    )

    return (
        ScenarioPreset(
            scenario_id="SC-01",
            title="SC-01 — Linha de Base Clássica (Homogêneo)",
            description=(
                "8 cirurgias limpas (c_i = 0) sem janela de plantão; "
                "clássicos e adaptados convergem para o ótimo igual a 5."
            ),
            surgeries=tuple(sc01_surgeries),
            shift_config=None,
        ),
        ScenarioPreset(
            scenario_id="SC-02",
            title="SC-02 — Contrexemplo Canônico de 3 Cirurgias",
            description=(
                "Prova de não-redutibilidade: S1 (13:00-14:00 + 2h) engana o Guloso "
                "Clássico, S3 (15:00-17:45 + 1h) engana a Redução Ingênua; "
                "apenas os adaptados atingem o ótimo {S2, S3} = 2."
            ),
            surgeries=tuple(sc02_surgeries),
            shift_config=sc02_cfg,
        ),
        ScenarioPreset(
            scenario_id="SC-03",
            title="SC-03 — Esterilização Passiva Além do Horizonte H",
            description=(
                "S_END encerra atuação médica às 17:50 (<= 18:00) com esterilização até "
                "18:20 e é aceita; S_OVER termina às 18:01 e é descartada."
            ),
            surgeries=tuple(sc03_surgeries),
            shift_config=sc03_cfg,
        ),
        ScenarioPreset(
            scenario_id="SC-04a",
            title="SC-04a — Sobreposição Ativa na Janela [12:00, 13:00]",
            description=(
                "Cirurgias com equipe ativa dentro de [12:00, 13:00) são descartadas, "
                "enquanto toques exatos nas fronteiras (11:00-12:00 e 13:00-14:00) são aceitos."
            ),
            surgeries=tuple(sc04_map["SC-04a"]),
            shift_config=sc04_cfg,
        ),
        ScenarioPreset(
            scenario_id="SC-04b",
            title="SC-04b — Esterilização Absorvida pela Pausa [12:00, 13:00]",
            description=(
                "Cirurgia 11:15-11:45 com 30m de ozônio termina esterilização às 12:15 "
                "(dentro da troca de plantão); liberação efetiva ajustada para r_i = 13:00."
            ),
            surgeries=tuple(sc04_map["SC-04b"]),
            shift_config=sc04_cfg,
        ),
        ScenarioPreset(
            scenario_id="SC-04c",
            title="SC-04c — Esterilização Transbordando a Pausa [12:00, 13:00]",
            description=(
                "Cirurgia 11:15-11:45 com 90m de esterilização libera a sala somente às "
                "13:15 (r_i = 795), bloqueando 13:00-14:00 e permitindo 13:15-14:15."
            ),
            surgeries=tuple(sc04_map["SC-04c"]),
            shift_config=sc04_cfg,
        ),
        ScenarioPreset(
            scenario_id="SC-05a",
            title="SC-05a — Borda: Todas as Cirurgias Inviáveis",
            description=(
                "Todas as cirurgias violam [12:00, 13:00) ou H=18:00, resultando em "
                "cardinalidade 0 e contagem precisa de descartes."
            ),
            surgeries=tuple(sc05a_surgeries),
            shift_config=sc05a_cfg,
        ),
        ScenarioPreset(
            scenario_id="SC-05b",
            title="SC-05b — Borda: Empate em Liberação Efetiva r_i",
            description=(
                "TIE_ABSORBED e TIE_EXACT_B possuem r_i idêntico (13:00 = 780) com f_i "
                "distintos, permitindo desempate determinístico seguido de FOLLOWUP."
            ),
            surgeries=tuple(sc05b_surgeries),
            shift_config=sc05b_cfg,
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
