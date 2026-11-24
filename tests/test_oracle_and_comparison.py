"""Testes de validação cruzada com oráculo exato (branch-and-bound)."""

import random

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
        surgeries = [
            SurgeryRequest(
                surgery_id=f"S{i}",
                start_time=i * 10,
                finish_time=i * 10 + 5,
            )
            for i in range(MAX_ORACLE_INPUT_SIZE + 1)
        ]
        oracle = BruteForceOracleScheduler()

        with pytest.raises(InvalidSchedulingInputError):
            oracle.schedule(surgeries)
