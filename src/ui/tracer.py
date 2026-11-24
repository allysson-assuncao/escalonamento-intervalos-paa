"""Rastreador passo a passo desacoplado e comparador lado a lado dos 4 algoritmos."""

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
    validate_scheduler_inputs,
)
from src.schedulers import (
    AdaptedDPScheduler,
    AdaptedGreedyScheduler,
    ClassicDPScheduler,
    ClassicGreedyScheduler,
    IntervalSchedulerProtocol,
)
from src.ui.scenarios_catalog import ScenarioPreset

MAX_TRACE_INPUT_SIZE: int = 200

ALGORITHM_KEYS: tuple[str, ...] = (
    "classic_greedy",
    "classic_dp",
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
    last_release_minutes: int | None = None


@dataclass(frozen=True)
class SimulationTrace:
    """Traço completo de execução passo a passo de um escalonador."""

    algorithm_key: str
    algorithm_name: str
    input_surgeries: tuple[SurgeryRequest, ...]
    processed_surgeries: tuple[ProcessedSurgery, ...]
    shift_config: ShiftConfig | None
    final_result: SchedulingResult
    steps: tuple[SimulationStep, ...]
    phase_offsets: dict[str, int]
    complexity_summary: dict[str, object]


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


def format_hhmm_with_min(minutes: int) -> str:
    """Formata um timestamp em minutos no formato didático 'HH:MM (min)'."""
    return f"{format_minutes_hhmm(minutes)} ({minutes} min)"


def _resolve_scheduler(algorithm_key: str) -> IntervalSchedulerProtocol:
    """Resolve a instância do escalonador a partir de sua chave textual."""
    mapping: dict[str, IntervalSchedulerProtocol] = {
        "classic_greedy": ClassicGreedyScheduler(),
        "classic_dp": ClassicDPScheduler(),
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
        last_release_minutes: int | None = None,
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
                last_release_minutes=last_release_minutes,
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
    """Registra a etapa PREPROCESSING para os modos clássico e adaptado."""
    is_classic = algorithm_key in ("classic_greedy", "classic_dp")

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
            variables={"Total de Cirurgias (n)": 0, "Viáveis / Descartadas": "0 / 0"},
            ordered=(),
            predecessors=(),
            dp_table=(),
            selected_ids=(),
        )
        return feasible, all_processed_for_gantt, discarded_count

    for idx, surgery in enumerate(items):
        sid = surgery.surgery_id
        statuses[sid] = SurgeryVisualStatus.INSPECTING
        raw_end = surgery.finish_time + surgery.sterilization_duration

        if is_classic:
            release = surgery.finish_time
            proc = ProcessedSurgery(request=surgery, effective_release_time=release)
            feasible.append(proc)
            all_processed_for_gantt.append(proc)
            statuses[sid] = SurgeryVisualStatus.FEASIBLE
            reason = (
                f"Modo clássico puro ignora esterilização (c_i={surgery.sterilization_duration} min) "
                f"e restrições de turno; adota liberação r_i = f_i = {format_hhmm_with_min(release)}."
            )
            release_label = format_hhmm_with_min(release)
        else:
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
                        f"ajustando r_i para {format_hhmm_with_min(release)}."
                    )
                elif (
                    shift_config is not None
                    and raw_end > shift_config.closing_horizon
                ):
                    reason = (
                        f"{sid} é viável (atuação médica até {format_minutes_hhmm(surgery.finish_time)} <= H); "
                        f"esterilização passiva segue até r_i = {format_hhmm_with_min(release)} após H."
                    )
                else:
                    reason = (
                        f"{sid} é viável; liberação efetiva r_i = {format_hhmm_with_min(release)}."
                    )
                release_label = format_hhmm_with_min(release)
            else:
                discarded_count += 1
                statuses[sid] = SurgeryVisualStatus.DISCARDED_INFEASIBLE
                reason = (
                    f"{sid} descartada por inviabilidade ativa: intervalo "
                    f"[{format_minutes_hhmm(surgery.start_time)}, {format_minutes_hhmm(surgery.finish_time)}] "
                    f"viola o horizonte H ou cruza a janela [A, B)."
                )
                release_label = "Descartada (inviável)"

        emit(  # type: ignore[operator]
            phase=TracePhase.PREPROCESSING,
            title=f"Pré-processamento ({idx + 1}/{len(items)}): {sid}",
            explanation=reason,
            active_surgery_id=sid,
            statuses=statuses,
            variables={
                "Cirurgia": f"{sid} ({idx + 1}/{len(items)})",
                "Intervalo Ativo [s_i, f_i]": (
                    f"{format_hhmm_with_min(surgery.start_time)} -> "
                    f"{format_hhmm_with_min(surgery.finish_time)}"
                ),
                "Risco e Esterilização (c_i)": (
                    f"{surgery.surgery_type.value} ({surgery.sterilization_duration} min)"
                ),
                "Fim Físico (e_i = f_i + c_i)": format_hhmm_with_min(raw_end),
                "Liberação Efetiva (r_i)": release_label,
                "Viáveis / Descartadas": f"{len(feasible)} / {discarded_count}",
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
    is_classic: bool,
    statuses: dict[str, SurgeryVisualStatus],
    emit: object,
) -> tuple[list[ProcessedSurgery], int]:
    """Registra a ordenação O(n log n) e retorna a sequência ordenada + comparações."""
    comparisons = [0]

    class _CountedSortKey:
        """Chave auxiliar apenas para contabilizar comparações reais do Timsort."""

        def __init__(self, key_tuple: tuple[int, int, int]) -> None:
            self.key_tuple = key_tuple

        def __lt__(self, other: "_CountedSortKey") -> bool:
            comparisons[0] += 1
            return self.key_tuple < other.key_tuple

    ordered = sorted(
        feasible,
        key=lambda item: _CountedSortKey(
            (
                item.effective_release_time,
                item.request.finish_time,
                item.request.start_time,
            )
        ),
    )

    criterion = (
        "(f_i, s_i) — término ativo crescente"
        if is_classic
        else "(r_i, f_i, s_i) — liberação efetiva crescente"
    )
    emit(  # type: ignore[operator]
        phase=TracePhase.SORTING,
        title="Ordenação Canônica — O(n log n)",
        explanation=(
            f"Ordenados {len(ordered)} itens viáveis em O(n log n) pelo critério {criterion} "
            f"({comparisons[0]} comparações executadas)."
        ),
        active_surgery_id=None,
        statuses=statuses,
        variables={
            "Cirurgias Viáveis (n')": len(ordered),
            "Critério de Ordenação": criterion,
            "Comparações na Ordenação": comparisons[0],
        },
        ordered=ordered,
        predecessors=(),
        dp_table=(),
        selected_ids=(),
    )
    return ordered, comparisons[0]


def _trace_predecessors_phase(
    ordered: Sequence[ProcessedSurgery],
    *,
    statuses: dict[str, SurgeryVisualStatus],
    emit: object,
) -> tuple[list[int], list[int | None], list[int | None], int]:
    """Registra cálculo de predecessores p[1..n'] exclusivamente via busca binária O(n log n)."""
    n_prime = len(ordered)
    predecessors_view: list[int | None] = [0] + [None] * n_prime
    dp_view: list[int | None] = [0] + [None] * n_prime
    resolved_p = [0] * (n_prime + 1)
    binary_search_steps = 0

    for idx in range(n_prime):
        item = ordered[idx]
        sid = item.request.surgery_id
        start_val = item.request.start_time
        lo = 0
        hi = idx
        while lo < hi:
            binary_search_steps += 1
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
                        "compatível (avança lo = mid + 1)."
                        if goes_right
                        else "incompatível (recua hi = mid)."
                    )
                ),
                active_surgery_id=sid,
                statuses=statuses,
                variables={
                    "Cirurgia": f"{sid} (índice {idx + 1})",
                    "Início (s_i)": format_hhmm_with_min(start_val),
                    "Janela [lo, mid, hi]": f"[{lo}, {mid}, {hi}]",
                    "Liberação R[mid]": format_hhmm_with_min(mid_release),
                    "Teste R[mid] <= s_i": "Compatível (lo = mid + 1)"
                    if goes_right
                    else "Conflito (hi = mid)",
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
        pred_label = (
            f"{lo} ({ordered[lo - 1].request.surgery_id})"
            if lo > 0
            else "0 (nenhum compatível)"
        )
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
                "Cirurgia": f"{sid} (índice {idx + 1})",
                "Início (s_i)": format_hhmm_with_min(start_val),
                "Predecessor p[i]": pred_label,
            },
            ordered=ordered,
            predecessors=predecessors_view,
            dp_table=dp_view,
            selected_ids=(),
            active_dp_index=idx + 1,
            referenced_dp_index=lo if lo > 0 else None,
        )

    return resolved_p, predecessors_view, dp_view, binary_search_steps


def _trace_greedy_selection_phase(
    ordered: Sequence[ProcessedSurgery],
    statuses: dict[str, SurgeryVisualStatus],
    emit: object,
) -> tuple[list[str], int]:
    """Registra a varredura linear gulosa com evolução de last_release."""
    last_release = -1
    selected_ids: list[str] = []

    for idx, item in enumerate(ordered):
        sid = item.request.surgery_id
        start_val = item.request.start_time
        release_val = item.effective_release_time
        prev_last_release = last_release
        prev_label = (
            format_hhmm_with_min(prev_last_release)
            if prev_last_release >= 0
            else "Livre (início do turno)"
        )
        statuses[sid] = SurgeryVisualStatus.INSPECTING

        if start_val >= last_release:
            statuses[sid] = SurgeryVisualStatus.SELECTED
            selected_ids.append(sid)
            last_release = release_val
            decision = "SELECIONADA"
            comparison = (
                f"{format_minutes_hhmm(start_val)} >= "
                f"{format_minutes_hhmm(prev_last_release) if prev_last_release >= 0 else '00:00'}"
            )
            explanation = (
                f"{sid} inicia em {format_minutes_hhmm(start_val)} >= última liberação "
                f"({format_minutes_hhmm(prev_last_release) if prev_last_release >= 0 else 'início'}). "
                f"Selecionada; sala libera em {format_hhmm_with_min(last_release)}."
            )
        else:
            statuses[sid] = SurgeryVisualStatus.REJECTED_CONFLICT
            decision = "REJEITADA"
            comparison = (
                f"{format_minutes_hhmm(start_val)} < {format_minutes_hhmm(prev_last_release)}"
            )
            explanation = (
                f"{sid} inicia em {format_minutes_hhmm(start_val)} < última liberação "
                f"({format_minutes_hhmm(prev_last_release)}). Rejeitada por conflito temporal."
            )

        emit(  # type: ignore[operator]
            phase=TracePhase.SELECTION_OR_DP,
            title=f"Varredura Gulosa ({idx + 1}/{len(ordered)}): {sid} — {decision}",
            explanation=explanation,
            active_surgery_id=sid,
            statuses=statuses,
            variables={
                "Passo": f"{idx + 1}/{len(ordered)} ({sid})",
                "Início (s_i)": format_hhmm_with_min(start_val),
                "Liberação (r_i)": format_hhmm_with_min(release_val),
                "Última Liberação Anterior": prev_label,
                "Comparação (s_i >= r_última)": comparison,
                "Nova Liberação da Sala": format_hhmm_with_min(last_release),
                "Decisão": decision,
                "Total Selecionadas": len(selected_ids),
            },
            ordered=ordered,
            predecessors=(),
            dp_table=(),
            selected_ids=selected_ids,
            active_dp_index=idx + 1,
            last_release_minutes=last_release,
        )

    return selected_ids, len(ordered)


def _trace_dp_table_and_backtracking(
    ordered: Sequence[ProcessedSurgery],
    resolved_p: Sequence[int],
    predecessors_view: list[int | None],
    dp_view: list[int | None],
    statuses: dict[str, SurgeryVisualStatus],
    emit: object,
) -> tuple[list[str], int, int]:
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
                "Índice (i)": f"{i} ({sid})",
                "Predecessor p[i]": pred,
                "Excluir (DP[i-1])": exclude_count,
                "Incluir (1 + DP[p[i]])": f"1 + {dp[pred]} = {include_count}",
                "Valor DP[i]": dp[i],
                "Melhor Escolha": "Incluir cirurgia" if chosen_include else "Manter DP[i-1]",
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
    backtrack_steps = 0
    while current > 0:
        backtrack_steps += 1
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
            decision_label = f"SELECIONA {sid} e salta para i={next_idx}"
            explanation = (
                f"Backtracking em i={current} ({sid}): 1 + DP[{pred}] ({include_val}) > "
                f"DP[{current - 1}] ({exclude_val}). Seleciona {sid} e salta para i={next_idx}."
            )
        else:
            statuses[sid] = SurgeryVisualStatus.REJECTED_CONFLICT
            next_idx = current - 1
            decision_label = f"DESCARTA {sid} e recua para i={next_idx}"
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
                "Índice Atual (i)": f"{current} ({sid})",
                "Predecessor p[i]": pred,
                "Excluir (DP[i-1])": exclude_val,
                "Incluir (1 + DP[p[i]])": include_val,
                "Decisão": decision_label,
                "Próximo Índice": next_idx,
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
    return selected_reversed, n_prime, backtrack_steps


def _build_complexity_summary(
    *,
    algorithm_key: str,
    algorithm_name: str,
    input_n: int,
    feasible_n: int,
    sort_comparisons: int,
    predecessor_ops: int,
    selection_or_dp_ops: int,
    backtrack_ops: int,
) -> dict[str, object]:
    """Constrói resumo didático de fórmulas e complexidade real por fase."""
    is_classic = algorithm_key in ("classic_greedy", "classic_dp")
    is_dp = algorithm_key in ("classic_dp", "adapted_dp")

    sorting_formula = (
        "Ordena pelo término médico f_i crescente (ignora esterilização c_i, horizonte H e janela [A, B])."
        if is_classic
        else "Filtra f_i <= H e (f_i <= A ou s_i >= B); calcula r_i = B se f_i <= A e A < f_i + c_i < B, senão r_i = f_i + c_i; ordena por r_i."
    )
    decision_formula = (
        (
            "p(i) = max{j < i | f_j <= s_i}; DP[i] = max(DP[i-1], 1 + DP[p(i)])"
            if is_classic
            else "p(i) = max{j < i | r_j <= s_i}; DP[i] = max(DP[i-1], 1 + DP[p(i)])"
        )
        if is_dp
        else (
            "Seleciona cirurgia i se s_i >= f_última"
            if is_classic
            else "Seleciona cirurgia i se s_i >= r_última"
        )
    )

    phases: list[dict[str, object]] = [
        {
            "phase": "1. Pré-processamento",
            "complexity": "O(n)",
            "operations": input_n,
            "description": (
                f"Inspeciona {input_n} cirurgia(s) ({feasible_n} viáveis)."
                if not is_classic
                else f"Adota todas as {input_n} cirurgias com r_i = f_i."
            ),
        },
        {
            "phase": "2. Ordenação",
            "complexity": "O(n log n)",
            "operations": sort_comparisons,
            "description": (
                f"Timsort sobre {feasible_n} itens ({sort_comparisons} comparações)."
            ),
        },
    ]

    if is_dp:
        phases.extend(
            [
                {
                    "phase": "3. Predecessores p[i] (Busca Binária)",
                    "complexity": "O(n log n)",
                    "operations": predecessor_ops,
                    "description": (
                        f"Busca binária (bisect_right) executada em {predecessor_ops} iterações."
                    ),
                },
                {
                    "phase": "4. Preenchimento Tabela DP[i]",
                    "complexity": "O(n)",
                    "operations": selection_or_dp_ops,
                    "description": f"Preenche {selection_or_dp_ops} subproblemas DP[1..n'].",
                },
                {
                    "phase": "5. Backtracking (Reconstrução)",
                    "complexity": "O(n)",
                    "operations": backtrack_ops,
                    "description": f"Reconstrói agenda ótima em {backtrack_ops} saltos.",
                },
            ]
        )
    else:
        phases.append(
            {
                "phase": "3. Varredura Gulosa Linear",
                "complexity": "O(n)",
                "operations": selection_or_dp_ops,
                "description": f"Testa compatibilidade s_i >= r_última em {selection_or_dp_ops} passos.",
            }
        )

    return {
        "algorithm_name": algorithm_name,
        "time_complexity": "O(n log n)",
        "space_complexity": "O(n)",
        "sorting_key_formula": sorting_formula,
        "decision_rule_formula": decision_formula,
        "input_n": input_n,
        "feasible_n": feasible_n,
        "phases": phases,
    }


def trace_scheduler_execution(
    surgeries: Sequence[SurgeryRequest],
    shift_config: ShiftConfig | None = None,
    *,
    algorithm_key: str = "adapted_greedy",
) -> SimulationTrace:
    """Executa rastreamento passo a passo desacoplado e valida paridade com schedule()."""
    items = validate_scheduler_inputs(surgeries, shift_config)
    if len(items) > MAX_TRACE_INPUT_SIZE:
        raise InvalidSchedulingInputError(
            f"O simulador passo a passo suporta no máximo {MAX_TRACE_INPUT_SIZE} cirurgias."
        )

    scheduler = _resolve_scheduler(algorithm_key)
    final_result = scheduler.schedule(items, shift_config=shift_config)

    steps: list[SimulationStep] = []
    phase_offsets: dict[str, int] = {}
    statuses: dict[str, SurgeryVisualStatus] = {
        item.surgery_id: SurgeryVisualStatus.PENDING for item in items
    }
    emit = _build_step_emitter(steps, phase_offsets)

    is_classic = algorithm_key in ("classic_greedy", "classic_dp")
    is_dp = algorithm_key in ("classic_dp", "adapted_dp")

    feasible, all_processed_for_gantt, discarded_count = _trace_preprocessing_phase(
        algorithm_key, items, shift_config, statuses, emit
    )
    ordered, sort_comparisons = _trace_sorting_phase(
        feasible, is_classic=is_classic, statuses=statuses, emit=emit
    )

    predecessors_view: list[int | None] = []
    dp_view: list[int | None] = []
    selected_ids: list[str] = []
    predecessor_ops = 0
    selection_or_dp_ops = 0
    backtrack_ops = 0

    if ordered:
        if is_dp:
            resolved_p, predecessors_view, dp_view, predecessor_ops = (
                _trace_predecessors_phase(ordered, statuses=statuses, emit=emit)
            )
            selected_ids, selection_or_dp_ops, backtrack_ops = (
                _trace_dp_table_and_backtracking(
                    ordered,
                    resolved_p,
                    predecessors_view,
                    dp_view,
                    statuses,
                    emit,
                )
            )
        else:
            selected_ids, selection_or_dp_ops = _trace_greedy_selection_phase(
                ordered, statuses, emit
            )

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
            "Total Selecionadas": len(selected_ids),
            "Descartadas (Inviáveis)": discarded_count,
            "Agenda Escolhida": ", ".join(selected_ids) if selected_ids else "(vazia)",
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

    complexity_summary = _build_complexity_summary(
        algorithm_key=algorithm_key,
        algorithm_name=scheduler.name,
        input_n=len(items),
        feasible_n=len(ordered),
        sort_comparisons=sort_comparisons,
        predecessor_ops=predecessor_ops,
        selection_or_dp_ops=selection_or_dp_ops,
        backtrack_ops=backtrack_ops,
    )

    return SimulationTrace(
        algorithm_key=algorithm_key,
        algorithm_name=scheduler.name,
        input_surgeries=tuple(items),
        processed_surgeries=tuple(all_processed_for_gantt),
        shift_config=shift_config,
        final_result=final_result,
        steps=tuple(steps),
        phase_offsets=phase_offsets,
        complexity_summary=complexity_summary,
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


def run_comparative_arena(
    surgeries: Sequence[SurgeryRequest],
    shift_config: ShiftConfig | None = None,
) -> tuple[AlgorithmComparisonEntry, ...]:
    """Executa os 4 escalonadores lado a lado e audita violações físicas nas agendas."""
    items = validate_scheduler_inputs(surgeries, shift_config)
    entries: list[AlgorithmComparisonEntry] = []

    for key in ALGORITHM_KEYS:
        scheduler = _resolve_scheduler(key)
        result = scheduler.schedule(items, shift_config=shift_config)
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
        "complexity_summary": dict(trace.complexity_summary),
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
                "last_release_minutes": step.last_release_minutes,
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
