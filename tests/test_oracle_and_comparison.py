"""Testes de validação cruzada com oráculo exato e benchmark de escalabilidade."""

import math
import random

import pytest

from src.benchmark import (
    BenchmarkPoint,
    format_benchmark_table,
    generate_synthetic_surgeries,
    run_scaling_benchmark,
)
from src.domain import (
    InvalidSchedulingInputError,
    ProcessedSurgery,
    ShiftConfig,
    ShiftWindow,
    SurgeryRequest,
    SurgeryType,
)
from src.schedulers import (
    MAX_ORACLE_INPUT_SIZE,
    AdaptedDPScheduler,
    AdaptedGreedyScheduler,
    BruteForceOracleScheduler,
)


def _assert_physical_schedule_invariants(
    selected: tuple[ProcessedSurgery, ...],
    shift_config: ShiftConfig | None,
) -> None:
    """Valida todas as restrições físicas, biológicas e de turno sobre o resultado."""
    for index, item in enumerate(selected):
        req = item.request
        if shift_config is not None:
            assert req.finish_time <= shift_config.closing_horizon
            if shift_config.shift_window is not None:
                win = shift_config.shift_window
                assert req.finish_time <= win.start or req.start_time >= win.end
                if req.finish_time <= win.start and win.start < (
                    req.finish_time + req.sterilization_duration
                ) < win.end:
                    assert item.effective_release_time == win.end
                else:
                    assert (
                        item.effective_release_time
                        == req.finish_time + req.sterilization_duration
                    )
            else:
                assert (
                    item.effective_release_time
                    == req.finish_time + req.sterilization_duration
                )
        if index > 0:
            assert req.start_time >= selected[index - 1].effective_release_time


class TestOracleCrossValidation:
    """Validação cruzada aleatória entre Guloso Adaptado, PD Adaptada e Oráculo Exato."""

    def test_tp06_randomized_equivalence_against_exact_oracle(self) -> None:
        """TP-06: Em 180 instâncias aleatórias (n in [0, 16]), Adaptados igualam Oráculo."""
        rng = random.Random(20261118)
        greedy = AdaptedGreedyScheduler()
        dp = AdaptedDPScheduler()
        oracle = BruteForceOracleScheduler()

        for trial in range(180):
            n = trial % 17  # 0..16
            horizon = rng.choice([720, 960, 1080, 1200])
            use_window = rng.random() < 0.7
            shift_window = None
            if use_window:
                win_start = rng.randint(horizon // 3, (2 * horizon) // 3 - 30)
                win_end = win_start + rng.randint(20, 90)
                shift_window = ShiftWindow(start=win_start, end=win_end)
            shift_config: ShiftConfig | None = (
                None
                if rng.random() < 0.15
                else ShiftConfig(closing_horizon=horizon, shift_window=shift_window)
            )

            surgeries: list[SurgeryRequest] = []
            for idx in range(n):
                start = rng.randint(0, horizon + 20)
                duration = rng.randint(10, 150)
                contaminated = rng.random() < 0.5
                surgeries.append(
                    SurgeryRequest(
                        surgery_id=f"R-{trial}-{idx}",
                        start_time=start,
                        finish_time=start + duration,
                        surgery_type=(
                            SurgeryType.CONTAMINATED
                            if contaminated
                            else SurgeryType.CLEAN
                        ),
                        sterilization_duration=rng.randint(5, 90) if contaminated else 0,
                    )
                )

            greedy_res = greedy.schedule(surgeries, shift_config)
            dp_res = dp.schedule(surgeries, shift_config)
            oracle_res = oracle.schedule(surgeries, shift_config)

            assert (
                greedy_res.total_selected
                == dp_res.total_selected
                == oracle_res.total_selected
            )
            assert (
                greedy_res.discarded_infeasible_count
                == dp_res.discarded_infeasible_count
                == oracle_res.discarded_infeasible_count
            )
            _assert_physical_schedule_invariants(
                greedy_res.selected_surgeries, shift_config
            )
            _assert_physical_schedule_invariants(dp_res.selected_surgeries, shift_config)
            _assert_physical_schedule_invariants(
                oracle_res.selected_surgeries, shift_config
            )

    def test_te04_oracle_rejects_input_above_limit(self) -> None:
        """TE-04: Oráculo exato rejeita n = 21 imediatamente antes de enumerar."""
        surgeries = generate_synthetic_surgeries(MAX_ORACLE_INPUT_SIZE + 1, seed=7)
        oracle = BruteForceOracleScheduler()

        with pytest.raises(InvalidSchedulingInputError):
            oracle.schedule(surgeries)


class TestBenchmarkRunner:
    """Testes de fumaça e validação defensiva para src/benchmark/runner.py."""

    def test_tp07_scaling_benchmark_and_table_formatting(self) -> None:
        """TP-07: Executa benchmark em tamanhos pequenos e verifica métricas e tabela."""
        shift_config = ShiftConfig(
            closing_horizon=1080,
            shift_window=ShiftWindow(start=720, end=780),
        )
        points = run_scaling_benchmark(
            sizes=(50, 100, 200),
            shift_config=shift_config,
            repetitions=3,
            seed=123,
        )

        # 3 tamanhos * 4 escalonadores padrão = 12 registros
        assert len(points) == 12
        for point in points:
            assert isinstance(point, BenchmarkPoint)
            assert point.input_size in {50, 100, 200}
            assert 0 <= point.feasible_count <= point.input_size
            assert 0 <= point.total_selected <= point.feasible_count
            assert point.median_elapsed_ns >= 0.0
            assert point.mean_elapsed_ns >= 0.0
            assert math.isfinite(point.ratio_n_log_n)
            assert math.isfinite(point.ratio_n)

        # Modo pré-ordenado também deve executar sem falhas
        presorted_points = run_scaling_benchmark(
            sizes=(50,),
            shift_config=shift_config,
            repetitions=2,
            is_presorted=True,
        )
        assert len(presorted_points) == 4
        assert all(point.is_presorted for point in presorted_points)

        table = format_benchmark_table(points)
        assert "Algorithm" in table
        assert "Adapted Greedy" in table
        assert "Adapted Dynamic Programming" in table

    def test_te06_benchmark_and_generator_validation_guards(self) -> None:
        """TE-06: Gerador e benchmark rejeitam parâmetros inválidos."""
        with pytest.raises(InvalidSchedulingInputError):
            generate_synthetic_surgeries(-1)
        with pytest.raises(InvalidSchedulingInputError):
            generate_synthetic_surgeries(10, contaminated_ratio=1.5)
        with pytest.raises(InvalidSchedulingInputError):
            generate_synthetic_surgeries(10, horizon=0)
        with pytest.raises(InvalidSchedulingInputError):
            run_scaling_benchmark(sizes=())
        with pytest.raises(InvalidSchedulingInputError):
            run_scaling_benchmark(sizes=(10,), repetitions=0)
        with pytest.raises(InvalidSchedulingInputError):
            run_scaling_benchmark(sizes=(10,), shift_config="bad")  # type: ignore[arg-type]
