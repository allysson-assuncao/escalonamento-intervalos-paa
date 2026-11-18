"""Testes unitários para pré-processamento, viabilidade ativa, r_i e redução ingênua."""

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
    preprocess_naive_static_reduction,
)
from tests.fixtures.scenarios import (
    build_sc02_counterexample_surgeries,
    build_sc03_end_of_shift_boundary,
    build_sc04_shift_window_scenarios,
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

    def test_sc03_passive_sterilization_past_horizon_accepted(self) -> None:
        """TP-04: Cirurgia válida até 17:50 com esterilização até 18:20 é aceita sob H=18:00."""
        surgeries, shift_config = build_sc03_end_of_shift_boundary()
        feasible, discarded = preprocess_feasible_surgeries(surgeries, shift_config)

        assert discarded == 1
        assert len(feasible) == 1
        assert feasible[0].request.surgery_id == "S_END"
        assert feasible[0].effective_release_time == 1100

        # Redução estática ingênua descarta erroneamente S_END e S_OVER
        naive_feasible, naive_discarded = preprocess_naive_static_reduction(
            surgeries, shift_config
        )
        assert naive_feasible == []
        assert naive_discarded == 2

    def test_sc02_naive_reduction_falsely_discards_s3(self) -> None:
        """TP-03: Pré-processamento adaptado mantém S3 enquanto redução ingênua a descarta."""
        surgeries, shift_config = build_sc02_counterexample_surgeries()
        adapted_feasible, adapted_discarded = preprocess_feasible_surgeries(
            surgeries, shift_config
        )
        naive_feasible, naive_discarded = preprocess_naive_static_reduction(
            surgeries, shift_config
        )

        assert adapted_discarded == 0
        assert [item.request.surgery_id for item in adapted_feasible] == ["S1", "S2", "S3"]
        assert [item.effective_release_time for item in adapted_feasible] == [960, 900, 1125]

        assert naive_discarded == 1
        assert [item.request.surgery_id for item in naive_feasible] == ["S1", "S2"]


class TestPreprocessingEdgeCases:
    """Testes de fronteira de janela [A, B], não mutação e entradas inválidas."""

    def test_te01_sc04a_active_overlap_vs_boundary_touching(self) -> None:
        """TE-01: Sobreposição ativa em [12:00, 13:00) é rejeitada; fronteiras exatas aceitas."""
        scenarios, shift_config = build_sc04_shift_window_scenarios()
        feasible, discarded = preprocess_feasible_surgeries(
            scenarios["SC-04a"], shift_config
        )

        assert discarded == 2
        assert [item.request.surgery_id for item in feasible] == [
            "TOUCH_PRE",
            "TOUCH_POST",
        ]
        assert [item.effective_release_time for item in feasible] == [720, 840]

    def test_te03_exact_sterilization_boundaries_at_a_and_b(self) -> None:
        """TE-03: Esterilização terminando exatamente em A ou em B preserva r_i = e_i."""
        shift_config = ShiftConfig(
            closing_horizon=1080,
            shift_window=ShiftWindow(start=720, end=780),
        )
        ends_at_a = SurgeryRequest(
            surgery_id="EXACT_A",
            start_time=660,   # 11:00
            finish_time=690,  # 11:30
            surgery_type=SurgeryType.CONTAMINATED,
            sterilization_duration=30,  # e = 720 == A
        )
        absorbed_in_window = SurgeryRequest(
            surgery_id="IN_AB",
            start_time=675,   # 11:15
            finish_time=705,  # 11:45
            surgery_type=SurgeryType.CONTAMINATED,
            sterilization_duration=30,  # e = 735 in (A, B) -> r = 780
        )
        ends_at_b = SurgeryRequest(
            surgery_id="EXACT_B",
            start_time=660,   # 11:00
            finish_time=720,  # 12:00 == A
            surgery_type=SurgeryType.CONTAMINATED,
            sterilization_duration=60,  # e = 780 == B
        )

        assert compute_effective_release_time(ends_at_a, shift_config) == 720
        assert compute_effective_release_time(absorbed_in_window, shift_config) == 780
        assert compute_effective_release_time(ends_at_b, shift_config) == 780

    def test_te06_non_mutation_and_invalid_inputs(self) -> None:
        """TE-06: Entrada não é mutada e parâmetros None/inválidos disparam erro."""
        surgeries, shift_config = build_sc02_counterexample_surgeries()
        snapshot = list(surgeries)

        preprocess_feasible_surgeries(surgeries, shift_config)
        preprocess_naive_static_reduction(surgeries, shift_config)
        assert surgeries == snapshot

        with pytest.raises(InvalidSchedulingInputError):
            preprocess_feasible_surgeries(None)  # type: ignore[arg-type]
        with pytest.raises(InvalidSchedulingInputError):
            preprocess_naive_static_reduction("invalid")  # type: ignore[arg-type]
        with pytest.raises(InvalidSchedulingInputError):
            is_actively_feasible("bad", shift_config)  # type: ignore[arg-type]
        with pytest.raises(InvalidSchedulingInputError):
            compute_effective_release_time(surgeries[0], "bad")  # type: ignore[arg-type]
