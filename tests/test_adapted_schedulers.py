"""Testes unitários e comparativos dos escalonadores adaptados."""

import pytest

from src.domain import (
    InvalidSchedulingInputError,
    ProcessedSurgery,
    ShiftConfig,
    ShiftWindow,
    SurgeryRequest,
    SurgeryType,
)
from src.schedulers import (
    AdaptedDPScheduler,
    AdaptedGreedyScheduler,
    BruteForceOracleScheduler,
    ClassicDPScheduler,
    ClassicGreedyScheduler,
    IntervalSchedulerProtocol,
)
from tests.fixtures.scenarios import (
    build_case01_classic_baseline,
    build_case02_sterilization_and_horizon,
    build_case03_shift_window,
    build_case04_full_mixed_shift,
)


def _assert_valid_adapted_schedule(
    selected: tuple[ProcessedSurgery, ...],
    shift_config: ShiftConfig | None,
) -> None:
    """Verifica viabilidade ativa e compatibilidade s_k >= r_{k-1} na solução."""
    for index, item in enumerate(selected):
        req = item.request
        if shift_config is not None:
            assert req.finish_time <= shift_config.closing_horizon
            if shift_config.shift_window is not None:
                win = shift_config.shift_window
                assert req.finish_time <= win.start or req.start_time >= win.end
        if index > 0:
            assert req.start_time >= selected[index - 1].effective_release_time


class TestAdaptedSchedulersHappyPath:
    """Casos principais e provas comparativas entre abordagens clássica e adaptada."""

    def test_protocol_conformance(self) -> None:
        """Verifica que todos os escalonadores aderem a IntervalSchedulerProtocol."""
        for scheduler in (
            AdaptedGreedyScheduler(),
            AdaptedDPScheduler(),
            BruteForceOracleScheduler(),
        ):
            assert isinstance(scheduler, IntervalSchedulerProtocol)

    def test_tp01_case01_backward_compatibility_with_classic(self) -> None:
        """TP-01: Em CASE-01 (CLEAN, sem janela), adaptados igualam clássicos (3)."""
        surgeries, shift_config = build_case01_classic_baseline()

        classic_g = ClassicGreedyScheduler().schedule(surgeries, shift_config)
        classic_dp = ClassicDPScheduler().schedule(surgeries, shift_config)
        adapted_g = AdaptedGreedyScheduler().schedule(surgeries, shift_config)
        adapted_dp = AdaptedDPScheduler().schedule(surgeries, shift_config)

        assert adapted_g.total_selected == 3
        assert adapted_dp.total_selected == 3
        assert adapted_g.discarded_infeasible_count == 0
        assert adapted_dp.discarded_infeasible_count == 0
        assert [x.request.surgery_id for x in adapted_g.selected_surgeries] == [
            x.request.surgery_id for x in classic_g.selected_surgeries
        ]
        assert [x.request.surgery_id for x in adapted_dp.selected_surgeries] == [
            x.request.surgery_id for x in classic_dp.selected_surgeries
        ]

    def test_shift_config_none_enforces_biological_sterilization(self) -> None:
        """Garante que shift_config=None pula H/[A, B], mas aplica r_i = f_i + c_i."""
        surgeries = [
            SurgeryRequest(
                surgery_id="CONTAM_1",
                start_time=100,
                finish_time=200,
                surgery_type=SurgeryType.CONTAMINATED,
                sterilization_duration=50,  # r_i = 250
            ),
            SurgeryRequest(
                surgery_id="CLEAN_CONFLICT",
                start_time=210,  # >= 200 (clássico aceitaria), porém < 250
                finish_time=240,
            ),
            SurgeryRequest(
                surgery_id="CLEAN_VALID",
                start_time=250,
                finish_time=300,
            ),
        ]

        classic_res = ClassicGreedyScheduler().schedule(surgeries, shift_config=None)
        assert classic_res.total_selected == 3

        for scheduler in (AdaptedGreedyScheduler(), AdaptedDPScheduler()):
            result = scheduler.schedule(surgeries, shift_config=None)
            assert result.discarded_infeasible_count == 0
            assert result.total_selected == 2
            assert [s.request.surgery_id for s in result.selected_surgeries] == [
                "CLEAN_CONFLICT",
                "CLEAN_VALID",
            ]
            _assert_valid_adapted_schedule(result.selected_surgeries, None)

    def test_tp02_case02_counterexample_defeats_classic(self) -> None:
        """TP-02: Em CASE-02, Adaptados e Oráculo escolhem {S2, S3} (2); Clássicos erram."""
        surgeries, shift_config = build_case02_sterilization_and_horizon()

        adapted_g = AdaptedGreedyScheduler().schedule(surgeries, shift_config)
        adapted_dp = AdaptedDPScheduler().schedule(surgeries, shift_config)
        oracle = BruteForceOracleScheduler().schedule(surgeries, shift_config)
        classic_g = ClassicGreedyScheduler().schedule(surgeries, shift_config)

        assert adapted_g.total_selected == 2
        assert adapted_dp.total_selected == 2
        assert oracle.total_selected == 2
        assert [s.request.surgery_id for s in adapted_g.selected_surgeries] == ["S2", "S3"]
        assert [s.request.surgery_id for s in adapted_dp.selected_surgeries] == ["S2", "S3"]
        assert [s.request.surgery_id for s in oracle.selected_surgeries] == ["S2", "S3"]
        _assert_valid_adapted_schedule(adapted_g.selected_surgeries, shift_config)
        _assert_valid_adapted_schedule(adapted_dp.selected_surgeries, shift_config)

        # Guloso clássico escolhe S1 primeiro (f_1 = 14:00 < f_2 = 15:00), gerando conflito com S3
        assert classic_g.selected_surgeries[0].request.surgery_id == "S1"

    def test_tp03_case03_shift_window_absorption_and_filtering(self) -> None:
        """TP-03: Em CASE-03, descarta S2/S3, absorve esterilização de S1 e escolhe {S1, S4, S5}."""
        surgeries, shift_config = build_case03_shift_window()
        for scheduler in (
            AdaptedGreedyScheduler(),
            AdaptedDPScheduler(),
            BruteForceOracleScheduler(),
        ):
            res = scheduler.schedule(surgeries, shift_config)
            assert res.discarded_infeasible_count == 2
            assert res.total_selected == 3
            assert [x.request.surgery_id for x in res.selected_surgeries] == [
                "S1",
                "S4",
                "S5",
            ]
            assert res.selected_surgeries[0].effective_release_time == 780
            _assert_valid_adapted_schedule(res.selected_surgeries, shift_config)

    def test_tp04_case04_full_mixed_shift_equivalence(self) -> None:
        """TP-04: Em CASE-04 (7 cirurgias mistas), Adaptados e Oráculo selecionam {S2, S3, S6, S7}."""
        surgeries, shift_config = build_case04_full_mixed_shift()
        for scheduler in (
            AdaptedGreedyScheduler(),
            AdaptedDPScheduler(),
            BruteForceOracleScheduler(),
        ):
            res = scheduler.schedule(surgeries, shift_config)
            assert res.discarded_infeasible_count == 1
            assert res.total_selected == 4
            assert [x.request.surgery_id for x in res.selected_surgeries] == [
                "S2",
                "S3",
                "S6",
                "S7",
            ]
            _assert_valid_adapted_schedule(res.selected_surgeries, shift_config)


class TestAdaptedSchedulersEdgeCases:
    """Casos extremos, fronteira de turno, empates em r_i e imutabilidade."""

    def test_te01_end_of_shift_passive_sterilization_boundary(self) -> None:
        """TE-01: Cirurgia terminando até H com esterilização após H é aceita; f_i > H falha."""
        shift_config = ShiftConfig(closing_horizon=1080)
        surgeries = [
            SurgeryRequest(
                surgery_id="S_END",
                start_time=1040,
                finish_time=1070,
                surgery_type=SurgeryType.CONTAMINATED,
                sterilization_duration=30,  # e = 1100 > H
            ),
            SurgeryRequest(
                surgery_id="S_OVER",
                start_time=1050,
                finish_time=1081,
                surgery_type=SurgeryType.CLEAN,
            ),
        ]
        for scheduler in (AdaptedGreedyScheduler(), AdaptedDPScheduler()):
            res = scheduler.schedule(surgeries, shift_config)
            assert res.total_selected == 1
            assert res.discarded_infeasible_count == 1
            assert res.selected_surgeries[0].request.surgery_id == "S_END"
            assert res.selected_surgeries[0].effective_release_time == 1100

    def test_te02_empty_single_all_infeasible_and_release_ties(self) -> None:
        """TE-02: Valida entrada vazia, unitária, todas inviáveis e empates em r_i."""
        shift_config = ShiftConfig(
            closing_horizon=1080,
            shift_window=ShiftWindow(start=720, end=780),
        )
        all_infeasible = [
            SurgeryRequest(surgery_id="INF_WIN_1", start_time=700, finish_time=740),
            SurgeryRequest(surgery_id="INF_WIN_2", start_time=720, finish_time=760),
            SurgeryRequest(surgery_id="INF_HORIZON", start_time=1020, finish_time=1090),
        ]
        ties = [
            SurgeryRequest(
                surgery_id="TIE_ABSORBED",
                start_time=675,
                finish_time=705,
                surgery_type=SurgeryType.CONTAMINATED,
                sterilization_duration=45,  # e = 750 -> r_i = 780
            ),
            SurgeryRequest(
                surgery_id="TIE_EXACT_B",
                start_time=660,
                finish_time=720,
                surgery_type=SurgeryType.CONTAMINATED,
                sterilization_duration=60,  # e = 780 -> r_i = 780
            ),
            SurgeryRequest(
                surgery_id="FOLLOWUP",
                start_time=780,
                finish_time=840,
            ),
        ]

        for scheduler in (AdaptedGreedyScheduler(), AdaptedDPScheduler()):
            empty_res = scheduler.schedule([], shift_config)
            assert empty_res.total_selected == 0
            assert empty_res.discarded_infeasible_count == 0

            single_res = scheduler.schedule(
                [SurgeryRequest("ONE", start_time=100, finish_time=200)], shift_config
            )
            assert single_res.total_selected == 1
            assert single_res.discarded_infeasible_count == 0

            all_inf_res = scheduler.schedule(all_infeasible, shift_config)
            assert all_inf_res.total_selected == 0
            assert all_inf_res.discarded_infeasible_count == 3

            tie_res = scheduler.schedule(ties, shift_config)
            assert tie_res.total_selected == 2
            _assert_valid_adapted_schedule(tie_res.selected_surgeries, shift_config)

    @pytest.mark.parametrize("scheduler_cls", [AdaptedGreedyScheduler, AdaptedDPScheduler])
    def test_te03_caller_non_mutation_and_invalid_inputs(
        self,
        scheduler_cls: type[AdaptedGreedyScheduler] | type[AdaptedDPScheduler],
    ) -> None:
        """TE-03: Lista original não é mutada e None/tipos inválidos disparam exceção."""
        scheduler = scheduler_cls()
        surgeries, shift_config = build_case02_sterilization_and_horizon()
        snapshot = list(surgeries)

        scheduler.schedule(surgeries, shift_config)
        assert surgeries == snapshot

        with pytest.raises(InvalidSchedulingInputError):
            scheduler.schedule(None)  # type: ignore[arg-type]
        with pytest.raises(InvalidSchedulingInputError):
            scheduler.schedule(["invalid"])  # type: ignore[list-item]
