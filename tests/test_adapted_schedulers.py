"""Testes unitários e comparativos dos escalonadores adaptados e redução ingênua."""

import pytest

from src.domain import (
    InvalidSchedulingInputError,
    ProcessedSurgery,
    ShiftConfig,
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
    NaiveReductionScheduler,
)
from tests.fixtures.scenarios import (
    build_monotonic_start_presorted_surgeries,
    build_sc01_classic_homogeneous_surgeries,
    build_sc02_counterexample_surgeries,
    build_sc03_end_of_shift_boundary,
    build_sc04_shift_window_scenarios,
    build_sc05_edge_case_scenarios,
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
    """Casos principais e provas comparativas entre abordagens clássica, ingênua e adaptada."""

    def test_protocol_conformance(self) -> None:
        """Verifica que todos os novos escalonadores aderem a IntervalSchedulerProtocol."""
        for scheduler in (
            AdaptedGreedyScheduler(),
            AdaptedDPScheduler(),
            NaiveReductionScheduler(),
            BruteForceOracleScheduler(),
        ):
            assert isinstance(scheduler, IntervalSchedulerProtocol)

    def test_tp02_sc01_backward_compatibility_with_classic(self) -> None:
        """TP-02: Com shift_config=None e cirurgias CLEAN, adaptados igualam clássicos."""
        surgeries = build_sc01_classic_homogeneous_surgeries()

        classic_g = ClassicGreedyScheduler().schedule(surgeries)
        classic_dp = ClassicDPScheduler().schedule(surgeries)
        adapted_g = AdaptedGreedyScheduler().schedule(surgeries, shift_config=None)
        adapted_dp = AdaptedDPScheduler().schedule(surgeries, shift_config=None)

        assert adapted_g.total_selected == 5
        assert adapted_dp.total_selected == 5
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

    def test_tp03_sc02_counterexample_defeats_classic_and_naive(self) -> None:
        """TP-03: No SC-02, Adaptados e Oráculo escolhem {S2, S3} (2); Ingênuo e Clássico falham."""
        surgeries, shift_config = build_sc02_counterexample_surgeries()

        adapted_g = AdaptedGreedyScheduler().schedule(surgeries, shift_config)
        adapted_dp = AdaptedDPScheduler().schedule(surgeries, shift_config)
        oracle = BruteForceOracleScheduler().schedule(surgeries, shift_config)
        naive = NaiveReductionScheduler().schedule(surgeries, shift_config)
        classic_g = ClassicGreedyScheduler().schedule(surgeries, shift_config)

        assert adapted_g.total_selected == 2
        assert adapted_dp.total_selected == 2
        assert oracle.total_selected == 2
        assert [s.request.surgery_id for s in adapted_g.selected_surgeries] == ["S2", "S3"]
        assert [s.request.surgery_id for s in adapted_dp.selected_surgeries] == ["S2", "S3"]
        assert [s.request.surgery_id for s in oracle.selected_surgeries] == ["S2", "S3"]
        _assert_valid_adapted_schedule(adapted_g.selected_surgeries, shift_config)
        _assert_valid_adapted_schedule(adapted_dp.selected_surgeries, shift_config)

        # Redução ingênua descarta S3 e obtém no máximo 1 cirurgia
        assert naive.discarded_infeasible_count == 1
        assert naive.total_selected == 1

        # Guloso clássico escolhe S1 primeiro (f_1 = 14:00 < f_2 = 15:00), bloqueando a sala até 16:00
        assert classic_g.selected_surgeries[0].request.surgery_id == "S1"

    def test_tp04_sc03_and_sc04_shift_window_behaviors(self) -> None:
        """TP-04: Valida SC-03 e subcenários SC-04b (absorção) e SC-04c (transbordamento)."""
        sc03_surgeries, sc03_config = build_sc03_end_of_shift_boundary()
        for scheduler in (AdaptedGreedyScheduler(), AdaptedDPScheduler()):
            res_sc03 = scheduler.schedule(sc03_surgeries, sc03_config)
            assert res_sc03.total_selected == 1
            assert res_sc03.discarded_infeasible_count == 1
            assert res_sc03.selected_surgeries[0].request.surgery_id == "S_END"
            assert res_sc03.selected_surgeries[0].effective_release_time == 1100

        scenarios, sc04_config = build_sc04_shift_window_scenarios()
        for scheduler in (AdaptedGreedyScheduler(), AdaptedDPScheduler()):
            res_4b = scheduler.schedule(scenarios["SC-04b"], sc04_config)
            assert res_4b.total_selected == 2
            assert [x.request.surgery_id for x in res_4b.selected_surgeries] == [
                "ABSORBED",
                "NEXT_AT_B",
            ]
            assert res_4b.selected_surgeries[0].effective_release_time == 780

            res_4c = scheduler.schedule(scenarios["SC-04c"], sc04_config)
            assert res_4c.total_selected == 2
            assert [x.request.surgery_id for x in res_4c.selected_surgeries] == [
                "OVERFLOW",
                "VALID_AFTER_RELEASE",
            ]
            assert res_4c.selected_surgeries[0].effective_release_time == 795

    def test_tp05_presorted_mode_matches_general_mode(self) -> None:
        """TP-05: is_presorted=True (monótono e com presorted_start_indices) equivale ao geral."""
        greedy = AdaptedGreedyScheduler()
        dp = AdaptedDPScheduler()

        monotonic = build_monotonic_start_presorted_surgeries()
        assert greedy.schedule(monotonic, is_presorted=True).total_selected == (
            greedy.schedule(monotonic, is_presorted=False).total_selected
        )
        assert dp.schedule(monotonic, is_presorted=True).total_selected == (
            dp.schedule(monotonic, is_presorted=False).total_selected
        )

        sc01_sorted = sorted(
            build_sc01_classic_homogeneous_surgeries(),
            key=lambda s: (s.finish_time + s.sterilization_duration, s.finish_time, s.start_time),
        )
        start_indices = sorted(
            range(len(sc01_sorted)),
            key=lambda idx: sc01_sorted[idx].start_time,
        )

        dp_general = dp.schedule(sc01_sorted, is_presorted=False)
        dp_presorted = dp.schedule(sc01_sorted, is_presorted=True)
        dp_two_ptr = dp.schedule(
            sc01_sorted,
            is_presorted=True,
            presorted_start_indices=start_indices,
        )

        assert dp_presorted.total_selected == dp_general.total_selected == 5
        assert dp_two_ptr.total_selected == dp_general.total_selected == 5
        assert [x.request.surgery_id for x in dp_two_ptr.selected_surgeries] == [
            x.request.surgery_id for x in dp_general.selected_surgeries
        ]


class TestAdaptedSchedulersEdgeCases:
    """Casos extremos, empates em r_i e validações defensivas de pré-ordenação."""

    def test_te01_sc04a_window_rejection_and_boundary_acceptance(self) -> None:
        """TE-01: SC-04a descarta sobreposições ativas e agenda cirurgias nas bordas."""
        scenarios, sc04_config = build_sc04_shift_window_scenarios()
        for scheduler in (AdaptedGreedyScheduler(), AdaptedDPScheduler()):
            res = scheduler.schedule(scenarios["SC-04a"], sc04_config)
            assert res.discarded_infeasible_count == 2
            assert res.total_selected == 2
            assert [x.request.surgery_id for x in res.selected_surgeries] == [
                "TOUCH_PRE",
                "TOUCH_POST",
            ]

    def test_te02_sc05_empty_single_all_infeasible_and_release_ties(self) -> None:
        """TE-02: Valida entrada vazia, unitária, todas inviáveis e empates em r_i."""
        (all_infeasible, cfg_inf), (ties, cfg_ties) = build_sc05_edge_case_scenarios()

        for scheduler in (AdaptedGreedyScheduler(), AdaptedDPScheduler()):
            empty_res = scheduler.schedule([], cfg_inf)
            assert empty_res.total_selected == 0
            assert empty_res.discarded_infeasible_count == 0

            single_res = scheduler.schedule(
                [SurgeryRequest("ONE", start_time=100, finish_time=200)], cfg_inf
            )
            assert single_res.total_selected == 1
            assert single_res.discarded_infeasible_count == 0

            all_inf_res = scheduler.schedule(all_infeasible, cfg_inf)
            assert all_inf_res.total_selected == 0
            assert all_inf_res.discarded_infeasible_count == 3

            tie_res = scheduler.schedule(ties, cfg_ties)
            assert tie_res.total_selected == 2
            _assert_valid_adapted_schedule(tie_res.selected_surgeries, cfg_ties)

    def test_te05_presorted_rejects_unsorted_and_filtered_start_indices(self) -> None:
        """TE-05: Rejeita entrada não ordenada e presorted_start_indices após descarte."""
        unsorted = [
            SurgeryRequest("B", start_time=20, finish_time=40),
            SurgeryRequest("A", start_time=10, finish_time=30),
        ]
        for scheduler in (
            AdaptedGreedyScheduler(),
            AdaptedDPScheduler(),
            NaiveReductionScheduler(),
        ):
            with pytest.raises(InvalidSchedulingInputError):
                scheduler.schedule(unsorted, is_presorted=True)

        # Caso com descarte por horizonte H e fornecimento de presorted_start_indices
        dp = AdaptedDPScheduler()
        sorted_with_infeasible = [
            SurgeryRequest("OK", start_time=100, finish_time=200),
            SurgeryRequest("OUT", start_time=900, finish_time=1100),
        ]
        with pytest.raises(InvalidSchedulingInputError):
            dp.schedule(
                sorted_with_infeasible,
                ShiftConfig(closing_horizon=1080),
                is_presorted=True,
                presorted_start_indices=[0, 1],
            )
        with pytest.raises(InvalidSchedulingInputError):
            dp.schedule(
                sorted_with_infeasible[:1],
                is_presorted=False,
                presorted_start_indices=[0],
            )

    @pytest.mark.parametrize(
        "scheduler_cls",
        [AdaptedGreedyScheduler, AdaptedDPScheduler, NaiveReductionScheduler],
    )
    def test_te06_caller_non_mutation_and_invalid_inputs(
        self,
        scheduler_cls: type[AdaptedGreedyScheduler]
        | type[AdaptedDPScheduler]
        | type[NaiveReductionScheduler],
    ) -> None:
        """TE-06: Lista original não é mutada e None/tipos inválidos disparam exceção."""
        scheduler = scheduler_cls()
        surgeries, shift_config = build_sc02_counterexample_surgeries()
        snapshot = list(surgeries)

        scheduler.schedule(surgeries, shift_config)
        assert surgeries == snapshot

        with pytest.raises(InvalidSchedulingInputError):
            scheduler.schedule(None)  # type: ignore[arg-type]
        with pytest.raises(InvalidSchedulingInputError):
            scheduler.schedule(["invalid"])  # type: ignore[list-item]
