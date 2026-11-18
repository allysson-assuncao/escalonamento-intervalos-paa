"""Rastreador passo a passo desacoplado e comparador lado a lado dos algoritmos."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from src.domain.exceptions import InvalidSchedulingInputError
from src.domain.models import (
    ProcessedSurgery,
    SchedulingResult,
    ShiftConfig,
    SurgeryRequest,
)
from src.domain.preprocessing import (
    compute_effective_release_time,
    is_actively_feasible,
    preprocess_naive_static_reduction,
    validate_scheduler_inputs,
)
from src.schedulers import (
    AdaptedDPScheduler,
    AdaptedGreedyScheduler,
    ClassicDPScheduler,
    ClassicGreedyScheduler,
    IntervalSchedulerProtocol,
    NaiveReductionScheduler,
)
from src.schedulers.protocol import validate_presorted_start_indices
from src.ui.scenarios_catalog import ScenarioPreset

MAX_TRACE_INPUT_SIZE: int = 200

ALGORITHM_KEYS: tuple[str, ...] = (
    "classic_greedy",
    "classic_dp",
    "naive_reduction",
    "adapted_greedy",
    "adapted_dp",
)


class TracePhase(str, Enum):
    """Fases estruturais da execução de um algoritmo de escalonamento."""

    PREPROCESSING = "PREPROCESSING"
    SORTING = "SORTING"
    PREDECESSORS = "PREDECESSORS"
    SELECTION_OR_DP = "SELECTION_OR_DP"
    BACKTRACKING = "BACKTRACKING"
    RESULT = "RESULT"


class SurgeryVisualStatus(str, Enum):
    """Estado visual de cada cirurgia durante a simulação passo a passo."""

    PENDING = "PENDING"
    INSPECTING = "INSPECTING"
    FEASIBLE = "FEASIBLE"
    DISCARDED_INFEASIBLE = "DISCARDED_INFEASIBLE"
    SELECTED = "SELECTED"
    REJECTED_CONFLICT = "REJECTED_CONFLICT"


@dataclass(frozen=True)
class SimulationStep:
    """Snapshot imutável de variáveis e estruturas em um passo da simulação."""

    step_index: int
    phase: TracePhase
    title: str
    explanation: str
    active_surgery_id: str | None
    statuses: dict[str, SurgeryVisualStatus]
    variables: dict[str, object]
    ordered_ids: tuple[str, ...]
    effective_releases: tuple[int, ...]
    predecessors: tuple[int | None, ...]
    dp_table: tuple[int | None, ...]
    selected_ids: tuple[str, ...]
    binary_search_range: tuple[int, int, int] | None = None
    active_dp_index: int | None = None
    referenced_dp_index: int | None = None


@dataclass(frozen=True)
class SimulationTrace:
    """Traço completo de execução passo a passo de um escalonador."""

    algorithm_key: str
    algorithm_name: str
    is_presorted: bool
    input_surgeries: tuple[SurgeryRequest, ...]
    processed_surgeries: tuple[ProcessedSurgery, ...]
    shift_config: ShiftConfig | None
    final_result: SchedulingResult
    steps: tuple[SimulationStep, ...]
    phase_offsets: dict[str, int]


@dataclass(frozen=True)
class AlgorithmComparisonEntry:
    """Resultado comparativo e auditoria de conflitos físicos para um algoritmo."""

    algorithm_key: str
    algorithm_name: str
    result: SchedulingResult
    is_physically_valid: bool
    physical_conflicts: tuple[str, ...]


def format_minutes_hhmm(minutes: int) -> str:
    """Formata um inteiro em minutos no formato legível HH:MM."""
    hours, mins = divmod(minutes, 60)
    return f"{hours:02d}:{mins:02d}"


def _resolve_scheduler(algorithm_key: str) -> IntervalSchedulerProtocol:
    """Resolve a instância do escalonador a partir de sua chave textual."""
    mapping: dict[str, IntervalSchedulerProtocol] = {
        "classic_greedy": ClassicGreedyScheduler(),
        "classic_dp": ClassicDPScheduler(),
        "naive_reduction": NaiveReductionScheduler(),
        "adapted_greedy": AdaptedGreedyScheduler(),
        "adapted_dp": AdaptedDPScheduler(),
    }
    scheduler = mapping.get(algorithm_key)
    if scheduler is None:
        valid = ", ".join(ALGORITHM_KEYS)
        raise InvalidSchedulingInputError(
            f"Algoritmo '{algorithm_key}' inválido. Opções suportadas: {valid}."
        )
    return scheduler


def _run_production_scheduler(
    scheduler: IntervalSchedulerProtocol,
    algorithm_key: str,
    items: list[SurgeryRequest],
    shift_config: ShiftConfig | None,
    *,
    is_presorted: bool,
    presorted_start_indices: Sequence[int] | None,
) -> SchedulingResult:
    """Executa o escalonador oficial de produção garantindo validação idêntica."""
    if isinstance(scheduler, (ClassicDPScheduler, AdaptedDPScheduler)):
        return scheduler.schedule(
            items,
            shift_config=shift_config,
            is_presorted=is_presorted,
            presorted_start_indices=presorted_start_indices,
        )
    if presorted_start_indices is not None:
        raise InvalidSchedulingInputError(
            f"presorted_start_indices não é suportado por '{algorithm_key}'."
        )
    return scheduler.schedule(
        items,
        shift_config=shift_config,
        is_presorted=is_presorted,
    )


def _are_processed_starts_monotonic(ordered: Sequence[ProcessedSurgery]) -> bool:
    """Verifica em O(n) se start_time é não decrescente na sequência ordenada."""
    for idx in range(1, len(ordered)):
        if ordered[idx].request.start_time < ordered[idx - 1].request.start_time:
            return False
    return True


def _build_step_emitter(
    steps: list[SimulationStep],
    phase_offsets: dict[str, int],
) -> object:
    """Fábrica interna de função emissora de snapshots indexados com offsets de fase."""

    def _emit(
        *,
        phase: TracePhase,
        title: str,
        explanation: str,
        active_surgery_id: str | None,
        statuses: dict[str, SurgeryVisualStatus],
        variables: dict[str, object],
        ordered: Sequence[ProcessedSurgery],
        predecessors: Sequence[int | None],
        dp_table: Sequence[int | None],
        selected_ids: Sequence[str],
        binary_search_range: tuple[int, int, int] | None = None,
        active_dp_index: int | None = None,
        referenced_dp_index: int | None = None,
    ) -> None:
        step_idx = len(steps)
        if phase.value not in phase_offsets:
            phase_offsets[phase.value] = step_idx
        steps.append(
            SimulationStep(
                step_index=step_idx,
                phase=phase,
                title=title,
                explanation=explanation,
                active_surgery_id=active_surgery_id,
                statuses=dict(statuses),
                variables=dict(variables),
                ordered_ids=tuple(item.request.surgery_id for item in ordered),
                effective_releases=tuple(
                    item.effective_release_time for item in ordered
                ),
                predecessors=tuple(predecessors),
                dp_table=tuple(dp_table),
                selected_ids=tuple(selected_ids),
                binary_search_range=binary_search_range,
                active_dp_index=active_dp_index,
                referenced_dp_index=referenced_dp_index,
            )
        )

    return _emit


def _trace_preprocessing_phase(
    algorithm_key: str,
    items: list[SurgeryRequest],
    shift_config: ShiftConfig | None,
    statuses: dict[str, SurgeryVisualStatus],
    emit: object,
) -> tuple[list[ProcessedSurgery], list[ProcessedSurgery], int]:
    """Registra a etapa PREPROCESSING para modo clássico, ingênuo ou adaptado."""
    is_classic = algorithm_key in ("classic_greedy", "classic_dp")
    is_naive = algorithm_key == "naive_reduction"

    feasible: list[ProcessedSurgery] = []
    all_processed_for_gantt: list[ProcessedSurgery] = []
    discarded_count = 0

    if not items:
        emit(  # type: ignore[operator]
            phase=TracePhase.PREPROCESSING,
            title="Pré-processamento — Entrada Vazia",
            explanation="Nenhuma cirurgia recebida para validação de viabilidade.",
            active_surgery_id=None,
            statuses=statuses,
            variables={"n": 0, "feasible_count": 0, "discarded_count": 0},
            ordered=(),
            predecessors=(),
            dp_table=(),
            selected_ids=(),
        )
        return feasible, all_processed_for_gantt, discarded_count

    for idx, surgery in enumerate(items):
        sid = surgery.surgery_id
        statuses[sid] = SurgeryVisualStatus.INSPECTING

        if is_classic:
            release = surgery.finish_time
            proc = ProcessedSurgery(request=surgery, effective_release_time=release)
            feasible.append(proc)
            all_processed_for_gantt.append(proc)
            statuses[sid] = SurgeryVisualStatus.FEASIBLE
            reason = (
                f"Modo clássico puro ignora esterilização (c_i={surgery.sterilization_duration}m) "
                f"e restrições de turno; adota r_i = f_i = {format_minutes_hhmm(release)}."
            )
        elif is_naive:
            naive_finish = surgery.finish_time + surgery.sterilization_duration
            proc = ProcessedSurgery(
                request=surgery, effective_release_time=naive_finish
            )
            all_processed_for_gantt.append(proc)
            naive_items, naive_disc = preprocess_naive_static_reduction(
                [surgery], shift_config
            )
            if naive_disc == 0:
                feasible.extend(naive_items)
                statuses[sid] = SurgeryVisualStatus.FEASIBLE
                reason = (
                    f"Redução ingênua calcula f'_i = f_i + c_i = {format_minutes_hhmm(naive_finish)} "
                    f"e aceita dentro do turno."
                )
            else:
                discarded_count += 1
                statuses[sid] = SurgeryVisualStatus.DISCARDED_INFEASIBLE
                reason = (
                    f"Redução ingênua descarta {sid} porque f'_i = {format_minutes_hhmm(naive_finish)} "
                    f"viola H ou [A, B] mesmo sendo esterilização passiva."
                )
        else:
            raw_end = surgery.finish_time + surgery.sterilization_duration
            release = compute_effective_release_time(surgery, shift_config)
            proc = ProcessedSurgery(request=surgery, effective_release_time=release)
            all_processed_for_gantt.append(proc)
            if is_actively_feasible(surgery, shift_config):
                feasible.append(proc)
                statuses[sid] = SurgeryVisualStatus.FEASIBLE
                if release != raw_end:
                    reason = (
                        f"{sid} é viável (f_i={format_minutes_hhmm(surgery.finish_time)}); "
                        f"esterilização até {format_minutes_hhmm(raw_end)} é absorvida por [A, B], "
                        f"ajustando r_i para {format_minutes_hhmm(release)}."
                    )
                elif (
                    shift_config is not None
                    and raw_end > shift_config.closing_horizon
                ):
                    reason = (
                        f"{sid} é viável (atuação médica até {format_minutes_hhmm(surgery.finish_time)} <= H); "
                        f"esterilização passiva segue até r_i = {format_minutes_hhmm(release)} após H."
                    )
                else:
                    reason = (
                        f"{sid} é viável; liberação efetiva r_i = "
                        f"{format_minutes_hhmm(release)} ({release} min)."
                    )
            else:
                discarded_count += 1
                statuses[sid] = SurgeryVisualStatus.DISCARDED_INFEASIBLE
                reason = (
                    f"{sid} descartada por inviabilidade ativa: intervalo "
                    f"[{format_minutes_hhmm(surgery.start_time)}, {format_minutes_hhmm(surgery.finish_time)}] "
                    f"viola H ou cruza [A, B)."
                )

        emit(  # type: ignore[operator]
            phase=TracePhase.PREPROCESSING,
            title=f"Pré-processamento ({idx + 1}/{len(items)}): {sid}",
            explanation=reason,
            active_surgery_id=sid,
            statuses=statuses,
            variables={
                "i": idx + 1,
                "n": len(items),
                "s_i": surgery.start_time,
                "f_i": surgery.finish_time,
                "c_i": surgery.sterilization_duration,
                "r_i": proc.effective_release_time,
                "feasible_count": len(feasible),
                "discarded_count": discarded_count,
            },
            ordered=feasible,
            predecessors=(),
            dp_table=(),
            selected_ids=(),
        )

    return feasible, all_processed_for_gantt, discarded_count


def _trace_sorting_phase(
    feasible: list[ProcessedSurgery],
    *,
    is_presorted: bool,
    statuses: dict[str, SurgeryVisualStatus],
    emit: object,
) -> list[ProcessedSurgery]:
    """Registra a ordenação (ou validação O(n) de pré-ordenação) por (r_i, f_i, s_i)."""
    ordered = list(feasible)
    if not is_presorted:
        ordered.sort(
            key=lambda item: (
                item.effective_release_time,
                item.request.finish_time,
                item.request.start_time,
            )
        )
        explanation = (
            f"Ordenados {len(ordered)} itens viáveis em O(n log n) por "
            "(effective_release_time, finish_time, start_time)."
        )
    else:
        explanation = (
            f"Validada pré-ordenação de {len(ordered)} itens viáveis em varredura linear O(n)."
        )

    emit(  # type: ignore[operator]
        phase=TracePhase.SORTING,
        title="Ordenação Canônica",
        explanation=explanation,
        active_surgery_id=None,
        statuses=statuses,
        variables={
            "n_prime": len(ordered),
            "is_presorted": is_presorted,
            "order_key": "(r_i, f_i, s_i)",
        },
        ordered=ordered,
        predecessors=(),
        dp_table=(),
        selected_ids=(),
    )
    return ordered


def _trace_predecessors_phase(
    ordered: Sequence[ProcessedSurgery],
    *,
    is_presorted: bool,
    validated_start_order: Sequence[int] | None,
    statuses: dict[str, SurgeryVisualStatus],
    emit: object,
) -> tuple[list[int], list[int | None], list[int | None]]:
    """Registra cálculo de predecessores p[1..n'] via dois ponteiros ou bisect_right."""
    n_prime = len(ordered)
    predecessors_view: list[int | None] = [0] + [None] * n_prime
    dp_view: list[int | None] = [0] + [None] * n_prime
    resolved_p = [0] * (n_prime + 1)

    use_two_pointers = is_presorted and (
        validated_start_order is not None or _are_processed_starts_monotonic(ordered)
    )

    if use_two_pointers:
        start_order = (
            validated_start_order
            if validated_start_order is not None
            else range(n_prime)
        )
        release_ptr = 0
        for idx in start_order:
            item = ordered[idx]
            sid = item.request.surgery_id
            start_val = item.request.start_time
            while (
                release_ptr < idx
                and ordered[release_ptr].effective_release_time <= start_val
            ):
                release_ptr += 1
            resolved_p[idx + 1] = release_ptr
            predecessors_view[idx + 1] = release_ptr
            emit(  # type: ignore[operator]
                phase=TracePhase.PREDECESSORS,
                title=f"Predecessor via Dois Ponteiros — p[{idx + 1}] ({sid})",
                explanation=(
                    f"Varredura monótona: para {sid} (s_i={format_minutes_hhmm(start_val)}), "
                    f"release_ptr avançou até {release_ptr}; portanto p[{idx + 1}] = {release_ptr}."
                ),
                active_surgery_id=sid,
                statuses=statuses,
                variables={
                    "mode": "two_pointers_O(n)",
                    "idx": idx + 1,
                    "s_idx": start_val,
                    "release_ptr": release_ptr,
                    "p_i": release_ptr,
                },
                ordered=ordered,
                predecessors=predecessors_view,
                dp_table=dp_view,
                selected_ids=(),
                active_dp_index=idx + 1,
                referenced_dp_index=release_ptr if release_ptr > 0 else None,
            )
    else:
        for idx in range(n_prime):
            item = ordered[idx]
            sid = item.request.surgery_id
            start_val = item.request.start_time
            lo = 0
            hi = idx
            while lo < hi:
                mid = (lo + hi) // 2
                mid_release = ordered[mid].effective_release_time
                goes_right = mid_release <= start_val
                emit(  # type: ignore[operator]
                    phase=TracePhase.PREDECESSORS,
                    title=f"Busca Binária para p[{idx + 1}] ({sid})",
                    explanation=(
                        f"Comparando s[{idx + 1}]={format_minutes_hhmm(start_val)} com "
                        f"R[mid={mid}]={format_minutes_hhmm(mid_release)}: "
                        + (
                            "compatível (lo = mid + 1)."
                            if goes_right
                            else "incompatível (hi = mid)."
                        )
                    ),
                    active_surgery_id=sid,
                    statuses=statuses,
                    variables={
                        "mode": "binary_search_O(n_log_n)",
                        "idx": idx + 1,
                        "s_idx": start_val,
                        "lo": lo,
                        "mid": mid,
                        "hi": hi,
                        "r_mid": mid_release,
                    },
                    ordered=ordered,
                    predecessors=predecessors_view,
                    dp_table=dp_view,
                    selected_ids=(),
                    binary_search_range=(lo, mid, hi),
                    active_dp_index=idx + 1,
                    referenced_dp_index=mid + 1,
                )
                if goes_right:
                    lo = mid + 1
                else:
                    hi = mid

            resolved_p[idx + 1] = lo
            predecessors_view[idx + 1] = lo
            emit(  # type: ignore[operator]
                phase=TracePhase.PREDECESSORS,
                title=f"Predecessor Definido — p[{idx + 1}] = {lo} ({sid})",
                explanation=(
                    f"Busca binária convergiu em lo=hi={lo}. "
                    + (
                        f"Última cirurgia compatível antes de {sid} é o item {lo} "
                        f"({ordered[lo - 1].request.surgery_id})."
                        if lo > 0
                        else f"Nenhuma cirurgia anterior é compatível com {sid} (p[{idx + 1}] = 0)."
                    )
                ),
                active_surgery_id=sid,
                statuses=statuses,
                variables={
                    "mode": "binary_search_O(n_log_n)",
                    "idx": idx + 1,
                    "s_idx": start_val,
                    "lo": lo,
                    "hi": hi,
                    "p_i": lo,
                },
                ordered=ordered,
                predecessors=predecessors_view,
                dp_table=dp_view,
                selected_ids=(),
                active_dp_index=idx + 1,
                referenced_dp_index=lo if lo > 0 else None,
            )

    return resolved_p, predecessors_view, dp_view


def _trace_greedy_selection_phase(
    ordered: Sequence[ProcessedSurgery],
    statuses: dict[str, SurgeryVisualStatus],
    emit: object,
) -> list[str]:
    """Registra a varredura linear gulosa com evolução de last_release."""
    last_release = -1
    selected_ids: list[str] = []

    for idx, item in enumerate(ordered):
        sid = item.request.surgery_id
        start_val = item.request.start_time
        release_val = item.effective_release_time
        prev_last_release = last_release
        statuses[sid] = SurgeryVisualStatus.INSPECTING

        if start_val >= last_release:
            statuses[sid] = SurgeryVisualStatus.SELECTED
            selected_ids.append(sid)
            last_release = release_val
            decision = "SELECIONADA"
            explanation = (
                f"{sid} inicia em {format_minutes_hhmm(start_val)} >= last_release "
                f"({format_minutes_hhmm(prev_last_release) if prev_last_release >= 0 else '-1'}). "
                f"Selecionada; last_release atualizado para {format_minutes_hhmm(last_release)}."
            )
        else:
            statuses[sid] = SurgeryVisualStatus.REJECTED_CONFLICT
            decision = "REJEITADA"
            explanation = (
                f"{sid} inicia em {format_minutes_hhmm(start_val)} < last_release "
                f"({format_minutes_hhmm(prev_last_release)}). Rejeitada por conflito temporal."
            )

        emit(  # type: ignore[operator]
            phase=TracePhase.SELECTION_OR_DP,
            title=f"Varredura Gulosa ({idx + 1}/{len(ordered)}): {sid} — {decision}",
            explanation=explanation,
            active_surgery_id=sid,
            statuses=statuses,
            variables={
                "step": idx + 1,
                "s_i": start_val,
                "r_i": release_val,
                "previous_last_release": prev_last_release,
                "last_release": last_release,
                "decision": decision,
                "selected_count": len(selected_ids),
            },
            ordered=ordered,
            predecessors=(),
            dp_table=(),
            selected_ids=selected_ids,
            active_dp_index=idx + 1,
        )

    return selected_ids


def _trace_dp_table_and_backtracking(
    ordered: Sequence[ProcessedSurgery],
    resolved_p: Sequence[int],
    predecessors_view: list[int | None],
    dp_view: list[int | None],
    statuses: dict[str, SurgeryVisualStatus],
    emit: object,
) -> list[str]:
    """Registra o preenchimento de DP[1..n'] e a reconstrução via backtracking."""
    n_prime = len(ordered)
    dp = [0] * (n_prime + 1)

    for i in range(1, n_prime + 1):
        item = ordered[i - 1]
        sid = item.request.surgery_id
        pred = resolved_p[i]
        include_count = 1 + dp[pred]
        exclude_count = dp[i - 1]
        chosen_include = include_count > exclude_count
        dp[i] = include_count if chosen_include else exclude_count
        dp_view[i] = dp[i]

        emit(  # type: ignore[operator]
            phase=TracePhase.SELECTION_OR_DP,
            title=f"Tabela DP[{i}] = {dp[i]} ({sid})",
            explanation=(
                f"Para {sid}: incluir = 1 + DP[p[{i}]={pred}] = {include_count} vs "
                f"excluir = DP[{i - 1}] = {exclude_count} -> DP[{i}] = {dp[i]}."
            ),
            active_surgery_id=sid,
            statuses=statuses,
            variables={
                "i": i,
                "p_i": pred,
                "dp_pred": dp[pred],
                "include_count": include_count,
                "exclude_count": exclude_count,
                "dp_i": dp[i],
                "prefer_include": chosen_include,
            },
            ordered=ordered,
            predecessors=predecessors_view,
            dp_table=dp_view,
            selected_ids=(),
            active_dp_index=i,
            referenced_dp_index=pred,
        )

    selected_reversed: list[str] = []
    current = n_prime
    while current > 0:
        item = ordered[current - 1]
        sid = item.request.surgery_id
        pred = resolved_p[current]
        include_val = 1 + dp[pred]
        exclude_val = dp[current - 1]
        take = include_val > exclude_val

        if take:
            statuses[sid] = SurgeryVisualStatus.SELECTED
            selected_reversed.append(sid)
            next_idx = pred
            explanation = (
                f"Backtracking em i={current} ({sid}): 1 + DP[{pred}] ({include_val}) > "
                f"DP[{current - 1}] ({exclude_val}). Seleciona {sid} e salta para i={next_idx}."
            )
        else:
            statuses[sid] = SurgeryVisualStatus.REJECTED_CONFLICT
            next_idx = current - 1
            explanation = (
                f"Backtracking em i={current} ({sid}): 1 + DP[{pred}] ({include_val}) <= "
                f"DP[{current - 1}] ({exclude_val}). Descarta {sid} e recua para i={next_idx}."
            )

        emit(  # type: ignore[operator]
            phase=TracePhase.BACKTRACKING,
            title=f"Backtracking i={current} -> {next_idx} ({sid})",
            explanation=explanation,
            active_surgery_id=sid,
            statuses=statuses,
            variables={
                "current": current,
                "next_current": next_idx,
                "p_current": pred,
                "include_val": include_val,
                "exclude_val": exclude_val,
                "taken": take,
            },
            ordered=ordered,
            predecessors=predecessors_view,
            dp_table=dp_view,
            selected_ids=list(reversed(selected_reversed)),
            active_dp_index=current,
            referenced_dp_index=next_idx,
        )
        current = next_idx

    selected_reversed.reverse()
    return selected_reversed


def trace_scheduler_execution(
    surgeries: Sequence[SurgeryRequest],
    shift_config: ShiftConfig | None = None,
    *,
    algorithm_key: str = "adapted_greedy",
    is_presorted: bool = False,
    presorted_start_indices: Sequence[int] | None = None,
) -> SimulationTrace:
    """Executa rastreamento passo a passo desacoplado e valida paridade com schedule()."""
    items = validate_scheduler_inputs(surgeries, shift_config)
    if len(items) > MAX_TRACE_INPUT_SIZE:
        raise InvalidSchedulingInputError(
            f"O simulador passo a passo suporta no máximo {MAX_TRACE_INPUT_SIZE} cirurgias."
        )

    scheduler = _resolve_scheduler(algorithm_key)
    final_result = _run_production_scheduler(
        scheduler,
        algorithm_key,
        items,
        shift_config,
        is_presorted=is_presorted,
        presorted_start_indices=presorted_start_indices,
    )

    validated_start_order: Sequence[int] | None = None
    if presorted_start_indices is not None:
        target_for_indices = (
            items
            if algorithm_key == "classic_dp"
            else [
                ProcessedSurgery(
                    request=item,
                    effective_release_time=compute_effective_release_time(
                        item, shift_config
                    ),
                )
                for item in items
                if is_actively_feasible(item, shift_config)
            ]
        )
        validated_start_order = validate_presorted_start_indices(
            target_for_indices, presorted_start_indices
        )

    steps: list[SimulationStep] = []
    phase_offsets: dict[str, int] = {}
    statuses: dict[str, SurgeryVisualStatus] = {
        item.surgery_id: SurgeryVisualStatus.PENDING for item in items
    }
    emit = _build_step_emitter(steps, phase_offsets)

    feasible, all_processed_for_gantt, discarded_count = _trace_preprocessing_phase(
        algorithm_key, items, shift_config, statuses, emit
    )
    ordered = _trace_sorting_phase(
        feasible, is_presorted=is_presorted, statuses=statuses, emit=emit
    )

    is_dp = algorithm_key in ("classic_dp", "adapted_dp")
    predecessors_view: list[int | None] = []
    dp_view: list[int | None] = []
    selected_ids: list[str] = []

    if ordered:
        if is_dp:
            resolved_p, predecessors_view, dp_view = _trace_predecessors_phase(
                ordered,
                is_presorted=is_presorted,
                validated_start_order=validated_start_order,
                statuses=statuses,
                emit=emit,
            )
            selected_ids = _trace_dp_table_and_backtracking(
                ordered,
                resolved_p,
                predecessors_view,
                dp_view,
                statuses,
                emit,
            )
        else:
            selected_ids = _trace_greedy_selection_phase(ordered, statuses, emit)

    emit(  # type: ignore[operator]
        phase=TracePhase.RESULT,
        title=f"Resultado Final — {scheduler.name}",
        explanation=(
            f"Execução concluída com {len(selected_ids)} cirurgia(s) selecionada(s) "
            f"e {discarded_count} descartada(s) por inviabilidade."
        ),
        active_surgery_id=None,
        statuses=statuses,
        variables={
            "total_selected": len(selected_ids),
            "discarded_infeasible_count": discarded_count,
            "elapsed_ns": final_result.elapsed_ns,
        },
        ordered=ordered,
        predecessors=predecessors_view,
        dp_table=dp_view,
        selected_ids=selected_ids,
    )

    expected_ids = tuple(item.request.surgery_id for item in final_result.selected_surgeries)
    if tuple(selected_ids) != expected_ids:
        raise AssertionError(
            f"Divergência interna no tracer ({selected_ids}) vs schedule() ({expected_ids})."
        )

    return SimulationTrace(
        algorithm_key=algorithm_key,
        algorithm_name=scheduler.name,
        is_presorted=is_presorted,
        input_surgeries=tuple(items),
        processed_surgeries=tuple(all_processed_for_gantt),
        shift_config=shift_config,
        final_result=final_result,
        steps=tuple(steps),
        phase_offsets=phase_offsets,
    )


def _audit_physical_conflicts(
    selected: Sequence[ProcessedSurgery],
    shift_config: ShiftConfig | None,
) -> tuple[str, ...]:
    """Audita se uma agenda gerada viola regras reais de esterilização, H ou [A, B]."""
    conflicts: list[str] = []
    for idx, item in enumerate(selected):
        req = item.request
        if shift_config is not None and not is_actively_feasible(req, shift_config):
            if req.finish_time > shift_config.closing_horizon:
                conflicts.append(
                    f"Cirurgia {req.surgery_id} termina após o horizonte H "
                    f"({format_minutes_hhmm(req.finish_time)} > "
                    f"{format_minutes_hhmm(shift_config.closing_horizon)})."
                )
            elif shift_config.shift_window is not None:
                win = shift_config.shift_window
                conflicts.append(
                    f"Cirurgia {req.surgery_id} sobrepõe a janela de plantão "
                    f"[{format_minutes_hhmm(win.start)}, {format_minutes_hhmm(win.end)})."
                )

        if idx > 0:
            prev_req = selected[idx - 1].request
            real_prev_release = compute_effective_release_time(prev_req, shift_config)
            if req.start_time < real_prev_release:
                conflicts.append(
                    f"Cirurgia {req.surgery_id} inicia às {format_minutes_hhmm(req.start_time)} "
                    f"antes da liberação real de {prev_req.surgery_id} "
                    f"({format_minutes_hhmm(real_prev_release)})."
                )

    return tuple(conflicts)


def _prepare_input_for_algorithm(
    items: list[SurgeryRequest],
    algorithm_key: str,
    shift_config: ShiftConfig | None,
    *,
    is_presorted: bool,
) -> list[SurgeryRequest]:
    """Prepara entrada ordenada conforme a chave de cada algoritmo quando is_presorted=True."""
    if not is_presorted:
        return items
    if algorithm_key in ("classic_greedy", "classic_dp"):
        return sorted(items, key=lambda s: (s.finish_time, s.start_time))
    if algorithm_key == "naive_reduction":
        return sorted(
            items,
            key=lambda s: (
                s.finish_time + s.sterilization_duration,
                s.finish_time,
                s.start_time,
            ),
        )
    return sorted(
        items,
        key=lambda s: (
            compute_effective_release_time(s, shift_config),
            s.finish_time,
            s.start_time,
        ),
    )


def run_comparative_arena(
    surgeries: Sequence[SurgeryRequest],
    shift_config: ShiftConfig | None = None,
    *,
    is_presorted: bool = False,
) -> tuple[AlgorithmComparisonEntry, ...]:
    """Executa os 5 escalonadores lado a lado e audita violações físicas nas agendas."""
    items = validate_scheduler_inputs(surgeries, shift_config)
    entries: list[AlgorithmComparisonEntry] = []

    for key in ALGORITHM_KEYS:
        scheduler = _resolve_scheduler(key)
        prepared = _prepare_input_for_algorithm(
            items, key, shift_config, is_presorted=is_presorted
        )
        result = scheduler.schedule(
            prepared,
            shift_config=shift_config,
            is_presorted=is_presorted,
        )
        conflicts = _audit_physical_conflicts(result.selected_surgeries, shift_config)
        entries.append(
            AlgorithmComparisonEntry(
                algorithm_key=key,
                algorithm_name=result.algorithm_name,
                result=result,
                is_physically_valid=len(conflicts) == 0,
                physical_conflicts=conflicts,
            )
        )

    return tuple(entries)


def serialize_surgery_request(surgery: SurgeryRequest) -> dict[str, object]:
    """Converte SurgeryRequest em dicionário JSON serializável."""
    return {
        "surgery_id": surgery.surgery_id,
        "start_time": surgery.start_time,
        "finish_time": surgery.finish_time,
        "surgery_type": surgery.surgery_type.value,
        "sterilization_duration": surgery.sterilization_duration,
    }


def serialize_shift_config(shift_config: ShiftConfig | None) -> dict[str, object] | None:
    """Converte ShiftConfig (ou None) em dicionário JSON serializável."""
    if shift_config is None:
        return None
    return {
        "closing_horizon": shift_config.closing_horizon,
        "shift_window": (
            {
                "start": shift_config.shift_window.start,
                "end": shift_config.shift_window.end,
            }
            if shift_config.shift_window is not None
            else None
        ),
    }


def serialize_processed_surgery(item: ProcessedSurgery) -> dict[str, object]:
    """Converte ProcessedSurgery em dicionário JSON serializável para Gantt."""
    return {
        **serialize_surgery_request(item.request),
        "raw_sterilization_end": (
            item.request.finish_time + item.request.sterilization_duration
        ),
        "effective_release_time": item.effective_release_time,
    }


def serialize_scenario_preset_to_dict(preset: ScenarioPreset) -> dict[str, object]:
    """Serializa ScenarioPreset completo para resposta de API."""
    return {
        "scenario_id": preset.scenario_id,
        "title": preset.title,
        "description": preset.description,
        "surgeries": [serialize_surgery_request(s) for s in preset.surgeries],
        "shift_config": serialize_shift_config(preset.shift_config),
    }


def serialize_trace_to_dict(trace: SimulationTrace) -> dict[str, object]:
    """Serializa SimulationTrace completo para consumo do frontend Web/SVG."""
    return {
        "algorithm_key": trace.algorithm_key,
        "algorithm_name": trace.algorithm_name,
        "is_presorted": trace.is_presorted,
        "shift_config": serialize_shift_config(trace.shift_config),
        "processed_surgeries": [
            serialize_processed_surgery(item) for item in trace.processed_surgeries
        ],
        "final_result": {
            "algorithm_name": trace.final_result.algorithm_name,
            "total_selected": trace.final_result.total_selected,
            "discarded_infeasible_count": trace.final_result.discarded_infeasible_count,
            "elapsed_ns": trace.final_result.elapsed_ns,
            "selected_ids": [
                item.request.surgery_id for item in trace.final_result.selected_surgeries
            ],
        },
        "phase_offsets": dict(trace.phase_offsets),
        "steps": [
            {
                "step_index": step.step_index,
                "phase": step.phase.value,
                "title": step.title,
                "explanation": step.explanation,
                "active_surgery_id": step.active_surgery_id,
                "statuses": {k: v.value for k, v in step.statuses.items()},
                "variables": dict(step.variables),
                "ordered_ids": list(step.ordered_ids),
                "effective_releases": list(step.effective_releases),
                "predecessors": list(step.predecessors),
                "dp_table": list(step.dp_table),
                "selected_ids": list(step.selected_ids),
                "binary_search_range": (
                    list(step.binary_search_range)
                    if step.binary_search_range is not None
                    else None
                ),
                "active_dp_index": step.active_dp_index,
                "referenced_dp_index": step.referenced_dp_index,
            }
            for step in trace.steps
        ],
    }


def serialize_comparison_to_dict(entry: AlgorithmComparisonEntry) -> dict[str, object]:
    """Serializa AlgorithmComparisonEntry para a Arena Comparativa."""
    return {
        "algorithm_key": entry.algorithm_key,
        "algorithm_name": entry.algorithm_name,
        "total_selected": entry.result.total_selected,
        "discarded_infeasible_count": entry.result.discarded_infeasible_count,
        "elapsed_ns": entry.result.elapsed_ns,
        "selected_ids": [
            item.request.surgery_id for item in entry.result.selected_surgeries
        ],
        "selected_surgeries": [
            serialize_processed_surgery(item) for item in entry.result.selected_surgeries
        ],
        "is_physically_valid": entry.is_physically_valid,
        "physical_conflicts": list(entry.physical_conflicts),
    }
