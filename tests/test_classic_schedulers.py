"""Testes unitários e comparativos para os algoritmos clássicos (Guloso e PD)."""

import pytest

from src.domain import (
    InvalidSchedulingInputError,
    ShiftConfig,
    ShiftWindow,
    SurgeryRequest,
    SurgeryType,
)
from src.schedulers import (
    ClassicDPScheduler,
    ClassicGreedyScheduler,
    IntervalSchedulerProtocol,
)
from tests.fixtures.scenarios import build_case01_classic_baseline


def _assert_valid_classic_schedule(selected_intervals: list[SurgeryRequest]) -> None:
    """Verifica que a solução selecionada está ordenada e não possui sobreposições."""
    for index in range(1, len(selected_intervals)):
        prev = selected_intervals[index - 1]
        curr = selected_intervals[index]
        assert curr.start_time >= prev.finish_time


class TestClassicSchedulersHappyPath:
    """Casos de caminho feliz e equivalência entre Guloso Clássico e PD Clássica."""

    def test_protocol_conformance(self) -> None:
        """Verifica que ambos os escalonadores clássicos implementam o protocolo comum."""
        greedy = ClassicGreedyScheduler()
        dp = ClassicDPScheduler()

        assert isinstance(greedy, IntervalSchedulerProtocol)
        assert isinstance(dp, IntervalSchedulerProtocol)

    def test_tp01_case01_classic_baseline_equivalence(self) -> None:
        """TP-01: No cenário CASE-01, Guloso e PD clássicos atingem ótimo igual a 3."""
        surgeries, _ = build_case01_classic_baseline()
        greedy = ClassicGreedyScheduler()
        dp = ClassicDPScheduler()

        greedy_result = greedy.schedule(surgeries)
        dp_result = dp.schedule(surgeries)

        assert greedy_result.total_selected == 3
        assert dp_result.total_selected == 3
        assert greedy_result.discarded_infeasible_count == 0
        assert dp_result.discarded_infeasible_count == 0
        assert greedy_result.elapsed_ns >= 0
        assert dp_result.elapsed_ns >= 0

        greedy_requests = [item.request for item in greedy_result.selected_surgeries]
        dp_requests = [item.request for item in dp_result.selected_surgeries]
        _assert_valid_classic_schedule(greedy_requests)
        _assert_valid_classic_schedule(dp_requests)
        assert [s.surgery_id for s in greedy_requests] == ["S1", "S3", "S4"]
        assert [s.surgery_id for s in dp_requests] == ["S1", "S3", "S4"]

    def test_tp02_pure_classic_mode_ignores_sterilization_and_shift_config(self) -> None:
        """TP-02: Modo clássico puro ignora esterilização e configuração de turno."""
        surgeries = [
            SurgeryRequest(
                surgery_id="S1",
                start_time=690,
                finish_time=750,  # Cruza janela 12:00-13:00 (720-780)
                surgery_type=SurgeryType.CONTAMINATED,
                sterilization_duration=120,
            ),
            SurgeryRequest(
                surgery_id="S2",
                start_time=750,  # Começa exatamente no finish_time de S1
                finish_time=1120,  # Ultrapassa horizonte 1080
                surgery_type=SurgeryType.CONTAMINATED,
                sterilization_duration=60,
            ),
        ]
        shift_config = ShiftConfig(
            closing_horizon=1080,
            shift_window=ShiftWindow(start=720, end=780),
        )

        for scheduler in (ClassicGreedyScheduler(), ClassicDPScheduler()):
            result = scheduler.schedule(surgeries, shift_config=shift_config)
            assert result.total_selected == 2
            assert result.discarded_infeasible_count == 0
            assert result.selected_surgeries[0].effective_release_time == 750
            assert result.selected_surgeries[1].effective_release_time == 1120


class TestClassicSchedulersEdgeCases:
    """Casos extremos, empates e validações defensivas."""

    @pytest.mark.parametrize("scheduler_cls", [ClassicGreedyScheduler, ClassicDPScheduler])
    def test_te01_empty_single_and_all_overlapping(
        self, scheduler_cls: type[ClassicGreedyScheduler] | type[ClassicDPScheduler]
    ) -> None:
        """TE-01: Lista vazia, única cirurgia e todas sobrepostas."""
        scheduler = scheduler_cls()

        empty_res = scheduler.schedule([])
        assert empty_res.total_selected == 0
        assert empty_res.selected_surgeries == ()

        single = [SurgeryRequest(surgery_id="ONLY", start_time=10, finish_time=50)]
        single_res = scheduler.schedule(single)
        assert single_res.total_selected == 1
        assert single_res.selected_surgeries[0].request.surgery_id == "ONLY"

        overlapping = [
            SurgeryRequest(surgery_id="O1", start_time=10, finish_time=50),
            SurgeryRequest(surgery_id="O2", start_time=20, finish_time=60),
            SurgeryRequest(surgery_id="O3", start_time=40, finish_time=70),
        ]
        overlap_res = scheduler.schedule(overlapping)
        assert overlap_res.total_selected == 1

    @pytest.mark.parametrize("scheduler_cls", [ClassicGreedyScheduler, ClassicDPScheduler])
    def test_te02_touching_boundaries_and_finish_ties(
        self, scheduler_cls: type[ClassicGreedyScheduler] | type[ClassicDPScheduler]
    ) -> None:
        """TE-02: Fronteiras contíguas (s_j == f_i) são compatíveis; empates mantêm ótimo."""
        scheduler = scheduler_cls()
        surgeries = [
            SurgeryRequest(surgery_id="T2", start_time=10, finish_time=20),
            SurgeryRequest(surgery_id="T1", start_time=0, finish_time=10),
            SurgeryRequest(surgery_id="T1_ALT", start_time=5, finish_time=10),
            SurgeryRequest(surgery_id="T3", start_time=20, finish_time=30),
        ]
        result = scheduler.schedule(surgeries)
        assert result.total_selected == 3
        _assert_valid_classic_schedule([item.request for item in result.selected_surgeries])

    @pytest.mark.parametrize("scheduler_cls", [ClassicGreedyScheduler, ClassicDPScheduler])
    def test_te03_caller_sequence_not_mutated_and_invalid_collection_rejected(
        self, scheduler_cls: type[ClassicGreedyScheduler] | type[ClassicDPScheduler]
    ) -> None:
        """TE-03: Entrada do chamador não é mutada e None/tipos inválidos são rejeitados."""
        scheduler = scheduler_cls()
        original, _ = build_case01_classic_baseline()
        snapshot = list(original)

        scheduler.schedule(original)
        assert original == snapshot

        with pytest.raises(InvalidSchedulingInputError):
            scheduler.schedule(None)  # type: ignore[arg-type]

        with pytest.raises(InvalidSchedulingInputError):
            scheduler.schedule(["not-a-surgery"])  # type: ignore[list-item]
