"""Executor de benchmark empírico de complexidade assintótica e cardinalidade."""

from collections.abc import Sequence
from dataclasses import dataclass
import math
import random
import statistics

from src.domain.exceptions import InvalidSchedulingInputError
from src.domain.models import ShiftConfig, SurgeryRequest, SurgeryType, is_strict_int
from src.domain.preprocessing import compute_effective_release_time
from src.schedulers.adapted_dp import AdaptedDPScheduler
from src.schedulers.adapted_greedy import AdaptedGreedyScheduler
from src.schedulers.classic_dp import ClassicDPScheduler
from src.schedulers.classic_greedy import ClassicGreedyScheduler
from src.schedulers.naive_reduction import NaiveReductionScheduler
from src.schedulers.protocol import IntervalSchedulerProtocol


@dataclass(frozen=True)
class BenchmarkPoint:
    """Registro consolidado de desempenho e cardinalidade para um tamanho de entrada."""

    algorithm_name: str
    input_size: int
    feasible_count: int
    total_selected: int
    median_elapsed_ns: float
    mean_elapsed_ns: float
    median_elapsed_ms: float
    ratio_n_log_n: float
    ratio_n: float
    is_presorted: bool


def generate_synthetic_surgeries(
    n: int,
    *,
    seed: int = 42,
    contaminated_ratio: float = 0.35,
    horizon: int = 1080,
) -> list[SurgeryRequest]:
    """Gera instância sintética reproduzível de solicitações cirúrgicas."""
    if not is_strict_int(n) or n < 0:
        raise InvalidSchedulingInputError(
            "A quantidade n de cirurgias deve ser um inteiro não negativo."
        )
    if not is_strict_int(seed):
        raise InvalidSchedulingInputError("A semente aleatória deve ser um inteiro.")
    if (
        isinstance(contaminated_ratio, bool)
        or not isinstance(contaminated_ratio, (int, float))
        or not (0.0 <= float(contaminated_ratio) <= 1.0)
    ):
        raise InvalidSchedulingInputError(
            "A proporção de cirurgias contaminadas deve estar entre 0.0 e 1.0."
        )
    if not is_strict_int(horizon) or horizon <= 0:
        raise InvalidSchedulingInputError(
            "O horizonte de geração deve ser um inteiro estritamente positivo."
        )

    rng = random.Random(seed)
    surgeries: list[SurgeryRequest] = []
    max_start = max(1, horizon - 15)

    for index in range(n):
        start_time = rng.randint(0, max_start)
        duration = rng.randint(15, 120)
        finish_time = start_time + duration
        is_contaminated = rng.random() < float(contaminated_ratio)
        if is_contaminated:
            surgery_type = SurgeryType.CONTAMINATED
            sterilization = rng.randint(15, 90)
        else:
            surgery_type = SurgeryType.CLEAN
            sterilization = 0

        surgeries.append(
            SurgeryRequest(
                surgery_id=f"SYN-{index + 1}",
                start_time=start_time,
                finish_time=finish_time,
                surgery_type=surgery_type,
                sterilization_duration=sterilization,
            )
        )
    return surgeries


def _prepare_scheduler_input(
    surgeries: Sequence[SurgeryRequest],
    scheduler: IntervalSchedulerProtocol,
    shift_config: ShiftConfig | None,
    *,
    is_presorted: bool,
) -> list[SurgeryRequest]:
    """Prepara entrada na ordenação esperada pelo algoritmo quando is_presorted=True."""
    if not is_presorted:
        return list(surgeries)
    if isinstance(scheduler, (ClassicGreedyScheduler, ClassicDPScheduler)):
        return sorted(surgeries, key=lambda item: (item.finish_time, item.start_time))
    if isinstance(scheduler, NaiveReductionScheduler):
        return sorted(
            surgeries,
            key=lambda item: (
                item.finish_time + item.sterilization_duration,
                item.finish_time,
                item.start_time,
            ),
        )
    return sorted(
        surgeries,
        key=lambda item: (
            compute_effective_release_time(item, shift_config),
            item.finish_time,
            item.start_time,
        ),
    )


def _validate_benchmark_params(
    sizes: Sequence[int],
    repetitions: int,
    shift_config: ShiftConfig | None,
    schedulers: Sequence[IntervalSchedulerProtocol] | None,
) -> tuple[list[int], tuple[IntervalSchedulerProtocol, ...]]:
    """Valida parâmetros de execução do benchmark de escalabilidade."""
    if (
        sizes is None
        or isinstance(sizes, (str, bytes))
        or not isinstance(sizes, Sequence)
        or len(sizes) == 0
    ):
        raise InvalidSchedulingInputError(
            "sizes deve ser uma sequência não vazia de tamanhos inteiros."
        )
    validated_sizes: list[int] = []
    for size in sizes:
        if not is_strict_int(size) or size < 0:
            raise InvalidSchedulingInputError(
                "Todos os tamanhos em sizes devem ser inteiros não negativos."
            )
        validated_sizes.append(size)

    if not is_strict_int(repetitions) or repetitions <= 0:
        raise InvalidSchedulingInputError(
            "O número de repetições deve ser um inteiro estritamente positivo."
        )
    if shift_config is not None and not isinstance(shift_config, ShiftConfig):
        raise InvalidSchedulingInputError(
            "shift_config deve ser uma instância de ShiftConfig ou None."
        )

    if schedulers is None:
        resolved: tuple[IntervalSchedulerProtocol, ...] = (
            ClassicGreedyScheduler(),
            ClassicDPScheduler(),
            AdaptedGreedyScheduler(),
            AdaptedDPScheduler(),
        )
    else:
        if isinstance(schedulers, (str, bytes)) or not isinstance(schedulers, Sequence):
            raise InvalidSchedulingInputError(
                "schedulers deve ser uma sequência de objetos compatíveis com IntervalSchedulerProtocol."
            )
        for scheduler in schedulers:
            if not isinstance(scheduler, IntervalSchedulerProtocol):
                raise InvalidSchedulingInputError(
                    "Todos os itens de schedulers devem implementar IntervalSchedulerProtocol."
                )
        resolved = tuple(schedulers)

    return validated_sizes, resolved


def run_scaling_benchmark(
    sizes: Sequence[int] = (100, 500, 1000, 2500, 5000),
    *,
    schedulers: Sequence[IntervalSchedulerProtocol] | None = None,
    shift_config: ShiftConfig | None = None,
    repetitions: int = 5,
    seed: int = 42,
    contaminated_ratio: float = 0.35,
    is_presorted: bool = False,
) -> list[BenchmarkPoint]:
    """Executa benchmark comparativo de escalabilidade assintótica e otimalidade."""
    validated_sizes, resolved_schedulers = _validate_benchmark_params(
        sizes, repetitions, shift_config, schedulers
    )
    horizon = shift_config.closing_horizon if shift_config is not None else 1080
    points: list[BenchmarkPoint] = []

    for size in validated_sizes:
        base_surgeries = generate_synthetic_surgeries(
            size,
            seed=seed + size,
            contaminated_ratio=contaminated_ratio,
            horizon=horizon,
        )
        for scheduler in resolved_schedulers:
            prepared_input = _prepare_scheduler_input(
                base_surgeries,
                scheduler,
                shift_config,
                is_presorted=is_presorted,
            )
            timings_ns: list[int] = []
            last_result = None
            for _ in range(repetitions):
                last_result = scheduler.schedule(
                    prepared_input,
                    shift_config=shift_config,
                    is_presorted=is_presorted,
                )
                timings_ns.append(last_result.elapsed_ns)

            assert last_result is not None
            median_ns = float(statistics.median(timings_ns))
            mean_ns = float(statistics.fmean(timings_ns))
            ratio_n_log_n = (
                median_ns / (size * math.log2(size)) if size > 1 else 0.0
            )
            ratio_n = median_ns / size if size > 0 else 0.0

            points.append(
                BenchmarkPoint(
                    algorithm_name=last_result.algorithm_name,
                    input_size=size,
                    feasible_count=size - last_result.discarded_infeasible_count,
                    total_selected=last_result.total_selected,
                    median_elapsed_ns=median_ns,
                    mean_elapsed_ns=mean_ns,
                    median_elapsed_ms=median_ns / 1_000_000.0,
                    ratio_n_log_n=ratio_n_log_n,
                    ratio_n=ratio_n,
                    is_presorted=is_presorted,
                )
            )

    return points


def format_benchmark_table(points: Sequence[BenchmarkPoint]) -> str:
    """Formata os resultados do benchmark em tabela textual alinhada para exibição."""
    header = (
        f"{'Algorithm':<44} | {'n':>6} | {'n_feas':>6} | {'Sel':>5} | "
        f"{'Median (ms)':>11} | {'T/(n log n)':>11} | {'T/n (ns)':>10}"
    )
    separator = "-" * len(header)
    lines = [header, separator]

    for point in points:
        lines.append(
            f"{point.algorithm_name:<44} | "
            f"{point.input_size:>6} | "
            f"{point.feasible_count:>6} | "
            f"{point.total_selected:>5} | "
            f"{point.median_elapsed_ms:>11.4f} | "
            f"{point.ratio_n_log_n:>11.2f} | "
            f"{point.ratio_n:>10.2f}"
        )

    return "\n".join(lines)
