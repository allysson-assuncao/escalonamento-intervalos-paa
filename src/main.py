"""Ponto de entrada CLI e servidor web local da interface de simulação."""

import argparse
from collections.abc import Sequence
import sys
import webbrowser

from src.benchmark.runner import format_benchmark_table, run_scaling_benchmark
from src.domain.exceptions import InvalidSchedulingInputError
from src.ui.scenarios_catalog import get_scenario_by_id
from src.ui.server import DEFAULT_HOST, DEFAULT_PORT, create_http_server
from src.ui.tracer import run_comparative_arena


def build_arg_parser() -> argparse.ArgumentParser:
    """Constrói o analisador de argumentos CLI da aplicação."""
    parser = argparse.ArgumentParser(
        prog="escalonamento-intervalos-paa",
        description=(
            "Simulador interativo, comparador e benchmark empírico para "
            "escalonamento cirúrgico com esterilização assimétrica e janela de turno."
        ),
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Endereço de bind do servidor local (padrão: {DEFAULT_HOST}).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Porta TCP do servidor local (padrão: {DEFAULT_PORT}).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Inicia o servidor web sem abrir automaticamente o navegador.",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="Executa comparação em modo CLI para um cenário (ex: SC-02) e encerra.",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Executa benchmark empírico de escalabilidade no terminal e encerra.",
    )
    parser.add_argument(
        "--sizes",
        type=int,
        nargs="+",
        default=[100, 500, 1000, 2500],
        help="Tamanhos de entrada n usados com --benchmark.",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=3,
        help="Número de repetições por tamanho no modo --benchmark.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Semente determinística para geração sintética no modo --benchmark.",
    )
    parser.add_argument(
        "--presorted",
        action="store_true",
        help="Usa modo pré-ordenado O(n) nas execuções CLI.",
    )
    return parser


def _run_scenario_cli(scenario_id: str, *, is_presorted: bool) -> int:
    """Executa comparação dos 5 algoritmos sobre um cenário e imprime resumo."""
    preset = get_scenario_by_id(scenario_id)
    entries = run_comparative_arena(
        preset.surgeries,
        preset.shift_config,
        is_presorted=is_presorted,
    )
    print(f"=== {preset.title} ===")
    print(preset.description)
    print()
    for entry in entries:
        selected_ids = ", ".join(
            item.request.surgery_id for item in entry.result.selected_surgeries
        )
        status = (
            "VÁLIDO"
            if entry.is_physically_valid
            else f"CONFLITO ({len(entry.physical_conflicts)})"
        )
        print(
            f"- {entry.algorithm_name}: selecionadas={entry.result.total_selected}, "
            f"descartadas={entry.result.discarded_infeasible_count}, "
            f"agenda=[{selected_ids}], tempo={entry.result.elapsed_ns}ns, status={status}"
        )
        for conflict in entry.physical_conflicts:
            print(f"    * {conflict}")
    return 0


def _run_benchmark_cli(
    sizes: Sequence[int],
    *,
    repetitions: int,
    seed: int,
    is_presorted: bool,
) -> int:
    """Executa benchmark de escalabilidade no terminal e imprime tabela formatada."""
    points = run_scaling_benchmark(
        sizes,
        repetitions=repetitions,
        seed=seed,
        is_presorted=is_presorted,
    )
    print(format_benchmark_table(points))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Ponto de entrada principal suportando modos CLI e interface Web local."""
    parser = build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        if args.scenario is not None:
            return _run_scenario_cli(args.scenario, is_presorted=args.presorted)
        if args.benchmark:
            return _run_benchmark_cli(
                args.sizes,
                repetitions=args.repetitions,
                seed=args.seed,
                is_presorted=args.presorted,
            )

        server = create_http_server(host=args.host, port=args.port)
    except InvalidSchedulingInputError as exc:
        print(f"Erro de entrada: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Falha ao iniciar servidor local: {exc}", file=sys.stderr)
        return 1

    bound_host, bound_port = server.server_address[0], server.server_address[1]
    url = f"http://{bound_host}:{bound_port}/"
    print(f"Simulador visual disponível em {url} (Ctrl+C para encerrar).")

    if not args.no_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
