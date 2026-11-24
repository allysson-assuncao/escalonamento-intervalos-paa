"""Testes unitários para pré-processamento, viabilidade ativa e liberação efetiva r_i."""

import pytest

from src.domain import (
    InvalidSchedulingInputError,
    ShiftConfig,
    ShiftWindow,
    SurgeryRequest,
    SurgeryType,
    compute_effective_release_time,
    is_actively_feasible,
    preprocess_feasible_surgeries,
)
from tests.fixtures.scenarios import (
    build_case02_sterilization_and_horizon,
    build_case03_shift_window,
    build_case04_full_mixed_shift,
)


class TestPreprocessingHappyPath:
    """Testes de caminho feliz para viabilidade ativa e liberação efetiva r_i."""

    def test_tp01_active_feasibility_and_effective_release_time(self) -> None:
        """TP-01: Verifica is_actively_feasible e compute_effective_release_time."""
        shift_config = ShiftConfig(
            closing_horizon=1080,
            shift_window=ShiftWindow(start=720, end=780),
        )
        clean_morning = SurgeryRequest("CL1", start_time=480, finish_time=540)
        contam_morning = SurgeryRequest(
            "CT1",
            start_time=540,
            finish_time=600,
            surgery_type=SurgeryType.CONTAMINATED,
            sterilization_duration=45,
        )
        over_horizon = SurgeryRequest("OVH", start_time=1020, finish_time=1081)

        # Sem shift_config, todas são ativamente viáveis e r_i = f_i + c_i
        assert is_actively_feasible(over_horizon, None) is True
        assert compute_effective_release_time(clean_morning, None) == 540
        assert compute_effective_release_time(contam_morning, None) == 645

        # Com shift_config, f_i > H é rejeitado
        assert is_actively_feasible(clean_morning, shift_config) is True
        assert is_actively_feasible(contam_morning, shift_config) is True
        assert is_actively_feasible(over_horizon, shift_config) is False
        assert compute_effective_release_time(contam_morning, shift_config) == 645

    def test_tp02_case02_preserves_s3_with_passive_sterilization_after_horizon(self) -> None:
        """TP-02: CASE-02 mantém S3 (f_3 <= H, e_3 > H) e calcula r_i corretos."""
        surgeries, shift_config = build_case02_sterilization_and_horizon()
        feasible, discarded = preprocess_feasible_surgeries(surgeries, shift_config)

        assert discarded == 0
        assert [item.request.surgery_id for item in feasible] == ["S1", "S2", "S3"]
        assert [item.effective_release_time for item in feasible] == [960, 900, 1125]

    def test_tp03_case03_window_discard_and_effective_release_jump_to_b(self) -> None:
        """TP-03: CASE-03 descarta S2/S3 na troca [12:00, 13:00] e ajusta r_1 = 780."""
        surgeries, shift_config = build_case03_shift_window()
        feasible, discarded = preprocess_feasible_surgeries(surgeries, shift_config)

        assert discarded == 2
        assert [item.request.surgery_id for item in feasible] == ["S1", "S4", "S5"]
        assert [item.effective_release_time for item in feasible] == [780, 930, 1050]

    def test_tp04_case04_full_shift_preprocessing(self) -> None:
        """TP-04: CASE-04 descarta apenas S4 e preserva S1..S3, S5..S7 com r_3 = B."""
        surgeries, shift_config = build_case04_full_mixed_shift()
        feasible, discarded = preprocess_feasible_surgeries(surgeries, shift_config)

        assert discarded == 1
        assert [item.request.surgery_id for item in feasible] == [
            "S1",
            "S2",
            "S3",
            "S5",
            "S6",
            "S7",
        ]
        assert [item.effective_release_time for item in feasible] == [
            630,
            615,
            780,
            960,
            930,
            1100,
        ]


class TestPreprocessingEdgeCases:
    """Testes de fronteira de janela [A, B], horizonte H, não mutação e entradas inválidas."""

    def test_te01_active_overlap_vs_exact_window_and_horizon_boundaries(self) -> None:
        """TE-01: Sobreposição ativa em [A, B) ou f_i > H falha; toques exatos passam."""
        shift_config = ShiftConfig(
            closing_horizon=1080,
            shift_window=ShiftWindow(start=720, end=780),
        )
        surgeries = [
            SurgeryRequest(surgery_id="OVER_LEFT", start_time=690, finish_time=735),
            SurgeryRequest(surgery_id="OVER_RIGHT", start_time=750, finish_time=810),
            SurgeryRequest(surgery_id="OVER_HORIZON", start_time=1050, finish_time=1081),
            SurgeryRequest(surgery_id="TOUCH_PRE", start_time=660, finish_time=720),
            SurgeryRequest(surgery_id="TOUCH_POST", start_time=780, finish_time=840),
            SurgeryRequest(
                surgery_id="END_PASSIVE",
                start_time=1040,
                finish_time=1070,
                surgery_type=SurgeryType.CONTAMINATED,
                sterilization_duration=30,  # e = 1100 > H, f = 1070 <= H
            ),
        ]
        feasible, discarded = preprocess_feasible_surgeries(surgeries, shift_config)

        assert discarded == 3
        assert [item.request.surgery_id for item in feasible] == [
            "TOUCH_PRE",
            "TOUCH_POST",
            "END_PASSIVE",
        ]
        assert [item.effective_release_time for item in feasible] == [720, 840, 1100]

    def test_te02_exact_sterilization_boundaries_at_a_b_and_overflow(self) -> None:
        """TE-02: Esterilização terminando em A, dentro de (A, B), em B ou após B."""
        shift_config = ShiftConfig(
            closing_horizon=1080,
            shift_window=ShiftWindow(start=720, end=780),
        )
        ends_at_a = SurgeryRequest(
            surgery_id="EXACT_A",
            start_time=660,
            finish_time=690,
            surgery_type=SurgeryType.CONTAMINATED,
            sterilization_duration=30,  # e = 720 == A
        )
        absorbed_in_window = SurgeryRequest(
            surgery_id="IN_AB",
            start_time=675,
            finish_time=705,
            surgery_type=SurgeryType.CONTAMINATED,
            sterilization_duration=30,  # e = 735 in (A, B) -> r = 780
        )
        ends_at_b = SurgeryRequest(
            surgery_id="EXACT_B",
            start_time=660,
            finish_time=720,
            surgery_type=SurgeryType.CONTAMINATED,
            sterilization_duration=60,  # e = 780 == B
        )
        overflow_b = SurgeryRequest(
            surgery_id="OVER_B",
            start_time=675,
            finish_time=705,
            surgery_type=SurgeryType.CONTAMINATED,
            sterilization_duration=90,  # e = 795 > B
        )

        assert compute_effective_release_time(ends_at_a, shift_config) == 720
        assert compute_effective_release_time(absorbed_in_window, shift_config) == 780
        assert compute_effective_release_time(ends_at_b, shift_config) == 780
        assert compute_effective_release_time(overflow_b, shift_config) == 795

    def test_te03_non_mutation_and_invalid_inputs(self) -> None:
        """TE-03: Entrada não é mutada e parâmetros None/inválidos disparam erro."""
        surgeries, shift_config = build_case02_sterilization_and_horizon()
        snapshot = list(surgeries)

        preprocess_feasible_surgeries(surgeries, shift_config)
        assert surgeries == snapshot

        with pytest.raises(InvalidSchedulingInputError):
            preprocess_feasible_surgeries(None)  # type: ignore[arg-type]
        with pytest.raises(InvalidSchedulingInputError):
            is_actively_feasible("bad", shift_config)  # type: ignore[arg-type]
        with pytest.raises(InvalidSchedulingInputError):
            compute_effective_release_time(surgeries[0], "bad")  # type: ignore[arg-type]
