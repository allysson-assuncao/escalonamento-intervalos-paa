"""Cenários determinísticos pré-configurados para validação clássica e adaptada."""

from src.domain.models import ShiftConfig, ShiftWindow, SurgeryRequest, SurgeryType

DEFAULT_CLOSING_HORIZON: int = 1080  # 18:00 em minutos
DEFAULT_SHIFT_WINDOW: ShiftWindow = ShiftWindow(start=720, end=780)  # 12:00-13:00


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
            # Sobrepõem [12:00, 13:00) -> descartadas
            SurgeryRequest(surgery_id="OVER_LEFT", start_time=690, finish_time=735),   # 11:30-12:15
            SurgeryRequest(surgery_id="OVER_RIGHT", start_time=750, finish_time=810),  # 12:30-13:30
            # Tangenciam [12:00, 13:00) externamente -> aceitas
            SurgeryRequest(surgery_id="TOUCH_PRE", start_time=660, finish_time=720),   # 11:00-12:00
            SurgeryRequest(surgery_id="TOUCH_POST", start_time=780, finish_time=840),  # 13:00-14:00
        ],
        "SC-04b": [
            # Esterilização 11:45 + 30m = 12:15 é absorvida pela janela -> r_i = 13:00 (780)
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
            # Esterilização 11:45 + 90m = 13:15 transborda janela -> r_i = 13:15 (795)
            SurgeryRequest(
                surgery_id="OVERFLOW",
                start_time=675,   # 11:15
                finish_time=705,  # 11:45
                surgery_type=SurgeryType.CONTAMINATED,
                sterilization_duration=90,
            ),
            SurgeryRequest(
                surgery_id="BLOCKED_AT_B",
                start_time=780,   # 13:00 < 13:15 (incompatível com OVERFLOW)
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
        # Ambas liberam em r_i = 780 (13:00), com f_i distintos (11:45 vs 12:00)
        SurgeryRequest(
            surgery_id="TIE_CONTAM",
            start_time=675,   # 11:15
            finish_time=705,  # 11:45
            surgery_type=SurgeryType.CONTAMINATED,
            sterilization_duration=45,  # e = 12:30 -> clamp r_i = 13:00 (780)
        ),
        SurgeryRequest(
            surgery_id="TIE_CLEAN",
            start_time=690,   # 11:30
            finish_time=720,  # 12:00
            surgery_type=SurgeryType.CLEAN,
            sterilization_duration=0,   # r_i = 12:00 (720) -> se colocarmos 12:00-13:00 não pode; ajustado:
        ),
    ]
    # Ajusta TIE_CLEAN para também ter r_i = 780 via esterilização até 13:00 (11:30-12:00 + 60m = 13:00)
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
