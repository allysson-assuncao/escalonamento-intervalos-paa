"""Cenários determinísticos pré-configurados para validação dos algoritmos clássicos."""

from src.domain.models import SurgeryRequest


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
