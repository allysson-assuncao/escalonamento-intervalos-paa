"""Testes unitários e de integração para tracer visual, servidor HTTP e CLI."""

from collections.abc import Iterator
import http.client
import json
from pathlib import Path
import subprocess
import sys
import threading

import pytest

from src.domain import (
    InvalidSchedulingInputError,
    ShiftConfig,
    SurgeryRequest,
)
from src.main import main as cli_main
from src.schedulers import (
    AdaptedDPScheduler,
    AdaptedGreedyScheduler,
    ClassicDPScheduler,
    ClassicGreedyScheduler,
    NaiveReductionScheduler,
)
from src.ui import (
    ALGORITHM_KEYS,
    MAX_BENCHMARK_REPETITIONS,
    MAX_BENCHMARK_SIZE,
    MAX_GENERATE_SIZE,
    MAX_REQUEST_BODY_BYTES,
    MAX_TRACE_INPUT_SIZE,
    SimulationTrace,
    TracePhase,
    create_http_server,
    get_scenario_by_id,
    get_scenario_presets,
    run_comparative_arena,
    trace_scheduler_execution,
)
from tests.fixtures.scenarios import build_monotonic_start_presorted_surgeries


@pytest.fixture()
def live_server() -> Iterator[tuple[str, int]]:
    """Inicia servidor HTTP local efêmero em thread daemon para testes de integração."""
    server = create_http_server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[0], int(server.server_address[1])
    try:
        yield host, port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)


def _http_request(
    host: str,
    port: int,
    method: str,
    path: str,
    body: bytes | None = None,
) -> tuple[int, str, bytes]:
    """Executa requisição HTTP bruta preservando caminhos literais para testes de segurança."""
    conn = http.client.HTTPConnection(host, port, timeout=5.0)
    headers: dict[str, str] = {}
    if body is not None:
        headers["Content-Type"] = "application/json"
        headers["Content-Length"] = str(len(body))
    try:
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        content = resp.read()
        return resp.status, resp.getheader("Content-Type", ""), content
    finally:
        conn.close()


class TestTracerAndComparatorHappyPath:
    """Testes de paridade do tracer multiestágio e arena comparativa (TP-01 a TP-03)."""

    def test_tp01_tracer_parity_across_scenarios_and_schedulers(self) -> None:
        """TP-01: Traço passo a passo equivale 100% a schedule() em SC-01..SC-05."""
        scheduler_map = {
            "classic_greedy": ClassicGreedyScheduler(),
            "classic_dp": ClassicDPScheduler(),
            "naive_reduction": NaiveReductionScheduler(),
            "adapted_greedy": AdaptedGreedyScheduler(),
            "adapted_dp": AdaptedDPScheduler(),
        }
        for preset in get_scenario_presets():
            for key in ALGORITHM_KEYS:
                trace = trace_scheduler_execution(
                    preset.surgeries,
                    preset.shift_config,
                    algorithm_key=key,
                )
                assert isinstance(trace, SimulationTrace)
                official = scheduler_map[key].schedule(
                    preset.surgeries, preset.shift_config
                )

                assert trace.final_result.total_selected == official.total_selected
                assert (
                    trace.final_result.discarded_infeasible_count
                    == official.discarded_infeasible_count
                )
                last_step = trace.steps[-1]
                assert last_step.phase == TracePhase.RESULT
                assert last_step.selected_ids == tuple(
                    s.request.surgery_id for s in official.selected_surgeries
                )

    def test_tp02_adapted_dp_microsteps_and_phase_offsets(self) -> None:
        """TP-02: AdaptedDPScheduler registra busca binária, dois ponteiros e offsets de fase."""
        sc02 = get_scenario_by_id("SC-02")
        trace_bisect = trace_scheduler_execution(
            sc02.surgeries,
            sc02.shift_config,
            algorithm_key="adapted_dp",
            is_presorted=False,
        )

        expected_phases = {
            TracePhase.PREPROCESSING.value,
            TracePhase.SORTING.value,
            TracePhase.PREDECESSORS.value,
            TracePhase.SELECTION_OR_DP.value,
            TracePhase.BACKTRACKING.value,
            TracePhase.RESULT.value,
        }
        assert expected_phases.issubset(trace_bisect.phase_offsets.keys())
        for phase_name, offset in trace_bisect.phase_offsets.items():
            assert trace_bisect.steps[offset].phase.value == phase_name

        # Verifica registro explícito de lo/mid/hi na busca binária e resultado {S2, S3}
        pred_steps = [
            s for s in trace_bisect.steps if s.phase == TracePhase.PREDECESSORS
        ]
        assert any("lo" in s.variables and "hi" in s.variables for s in pred_steps)
        assert trace_bisect.steps[-1].selected_ids == ("S2", "S3")

        # Modo pré-ordenado com inícios monótonos usa dois ponteiros em O(n)
        monotonic = build_monotonic_start_presorted_surgeries()
        trace_two_ptr = trace_scheduler_execution(
            monotonic,
            None,
            algorithm_key="adapted_dp",
            is_presorted=True,
        )
        two_ptr_steps = [
            s for s in trace_two_ptr.steps if s.phase == TracePhase.PREDECESSORS
        ]
        assert any(s.variables.get("mode") == "two_pointers_O(n)" for s in two_ptr_steps)

        # Modo pré-ordenado com presorted_start_indices explícito
        sorted_sc02 = sorted(
            sc02.surgeries,
            key=lambda s: (
                s.finish_time + s.sterilization_duration,
                s.finish_time,
                s.start_time,
            ),
        )
        start_indices = sorted(
            range(len(sorted_sc02)), key=lambda i: sorted_sc02[i].start_time
        )
        trace_idx = trace_scheduler_execution(
            sorted_sc02,
            sc02.shift_config,
            algorithm_key="adapted_dp",
            is_presorted=True,
            presorted_start_indices=start_indices,
        )
        assert trace_idx.steps[-1].selected_ids == ("S2", "S3")

    def test_tp03_comparative_arena_and_conflict_detection(self) -> None:
        """TP-03: Arena comparativa retorna 5 abordagens e detecta conflitos em SC-02 e SC-04a."""
        sc02 = get_scenario_by_id("SC-02")
        entries = run_comparative_arena(sc02.surgeries, sc02.shift_config)
        assert len(entries) == 5

        by_key = {entry.algorithm_key: entry for entry in entries}
        assert by_key["adapted_greedy"].result.total_selected == 2
        assert by_key["adapted_dp"].result.total_selected == 2
        assert by_key["adapted_greedy"].is_physically_valid is True
        assert by_key["adapted_dp"].is_physically_valid is True

        assert by_key["naive_reduction"].result.total_selected == 1
        assert by_key["naive_reduction"].result.discarded_infeasible_count == 1
        # Clássicos aceitam {S1, S3} ignorando esterilização de 2h de S1 -> conflito físico real
        assert by_key["classic_greedy"].is_physically_valid is False
        assert len(by_key["classic_greedy"].physical_conflicts) >= 1

        sc04a = get_scenario_by_id("SC-04a")
        entries_4a = run_comparative_arena(sc04a.surgeries, sc04a.shift_config)
        by_key_4a = {entry.algorithm_key: entry for entry in entries_4a}
        assert by_key_4a["adapted_greedy"].is_physically_valid is True
        assert by_key_4a["classic_greedy"].is_physically_valid is False


class TestHttpServerAndCliHappyPath:
    """Testes de integração da API HTTP local e CLI headless (TP-04 a TP-07)."""

    def test_tp04_static_assets_and_scenarios_endpoint(
        self, live_server: tuple[str, int]
    ) -> None:
        """TP-04: GET /, /styles.css, /app.js e /api/scenarios retornam HTTP 200."""
        host, port = live_server

        for route, expected_mime, marker in (
            ("/", "text/html", b"Escalonamento de Intervalos"),
            ("/styles.css", "text/css", b"--primary"),
            ("/app.js", "application/javascript", b"buildGanttSvg"),
        ):
            status, ctype, raw = _http_request(host, port, "GET", route)
            assert status == 200
            assert expected_mime in ctype
            assert marker in raw

        status, ctype, raw = _http_request(host, port, "GET", "/api/scenarios")
        assert status == 200
        assert "application/json" in ctype
        payload = json.loads(raw.decode("utf-8"))
        scenario_ids = [item["scenario_id"] for item in payload["scenarios"]]
        assert "SC-01" in scenario_ids
        assert "SC-02" in scenario_ids
        assert "SC-04b" in scenario_ids

    def test_tp05_trace_and_compare_endpoints(
        self, live_server: tuple[str, int]
    ) -> None:
        """TP-05: POST /api/trace e POST /api/compare retornam JSON válido para SC-02."""
        host, port = live_server
        body = json.dumps(
            {
                "algorithm_key": "adapted_dp",
                "is_presorted": False,
                "shift_config": {"closing_horizon": 1080, "shift_window": None},
                "surgeries": [
                    {
                        "surgery_id": "S1",
                        "start_time": 780,
                        "finish_time": 840,
                        "surgery_type": "CONTAMINATED",
                        "sterilization_duration": 120,
                    },
                    {
                        "surgery_id": "S2",
                        "start_time": 810,
                        "finish_time": 900,
                        "surgery_type": "CLEAN",
                        "sterilization_duration": 0,
                    },
                    {
                        "surgery_id": "S3",
                        "start_time": 900,
                        "finish_time": 1065,
                        "surgery_type": "CONTAMINATED",
                        "sterilization_duration": 60,
                    },
                ],
            }
        ).encode("utf-8")

        status, _, raw_trace = _http_request(host, port, "POST", "/api/trace", body)
        assert status == 200
        trace_data = json.loads(raw_trace.decode("utf-8"))
        assert trace_data["final_result"]["selected_ids"] == ["S2", "S3"]
        assert "PREDECESSORS" in trace_data["phase_offsets"]

        status_cmp, _, raw_cmp = _http_request(host, port, "POST", "/api/compare", body)
        assert status_cmp == 200
        cmp_data = json.loads(raw_cmp.decode("utf-8"))
        assert len(cmp_data["entries"]) == 5

    def test_tp06_generate_and_benchmark_endpoints(
        self, live_server: tuple[str, int]
    ) -> None:
        """TP-06: POST /api/generate e POST /api/benchmark executam com dados válidos."""
        host, port = live_server

        gen_body = json.dumps(
            {"n": 8, "seed": 99, "contaminated_ratio": 0.5, "horizon": 1080}
        ).encode("utf-8")
        status_gen, _, raw_gen = _http_request(
            host, port, "POST", "/api/generate", gen_body
        )
        assert status_gen == 200
        gen_data = json.loads(raw_gen.decode("utf-8"))
        assert len(gen_data["surgeries"]) == 8

        bench_body = json.dumps(
            {
                "sizes": [50, 100],
                "repetitions": 2,
                "seed": 42,
                "is_presorted": False,
                "include_naive": False,
                "shift_config": {"closing_horizon": 1080, "shift_window": None},
            }
        ).encode("utf-8")
        status_bench, _, raw_bench = _http_request(
            host, port, "POST", "/api/benchmark", bench_body
        )
        assert status_bench == 200
        bench_data = json.loads(raw_bench.decode("utf-8"))
        assert len(bench_data["points"]) == 8  # 2 tamanhos * 4 escalonadores
        assert "Algorithm" in bench_data["table"]

    def test_tp07_cli_headless_modes(self, capsys: pytest.CaptureFixture[str]) -> None:
        """TP-07: src/main.py executa --scenario e --benchmark em modo headless."""
        rc_sc = cli_main(["--scenario", "SC-02"])
        assert rc_sc == 0
        out_sc = capsys.readouterr().out
        assert "SC-02" in out_sc
        assert "Adapted Greedy" in out_sc

        rc_bench = cli_main(
            ["--benchmark", "--sizes", "50", "100", "--repetitions", "2"]
        )
        assert rc_bench == 0
        out_bench = capsys.readouterr().out
        assert "Adapted Dynamic Programming" in out_bench

        # Valida invocação como módulo via subprocesso
        proc = subprocess.run(
            [sys.executable, "-m", "src.main", "--scenario", "SC-02"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0
        assert "S2, S3" in proc.stdout


class TestUiSecurityAndEdgeCases:
    """Casos de borda do tracer, limites de API e proteção contra XSS/path traversal."""

    def test_te01_empty_and_all_infeasible_traces(self) -> None:
        """TE-01: Entradas vazia e totalmente inviável (SC-05a) geram traço limpo."""
        sc05a = get_scenario_by_id("SC-05a")
        for key in ALGORITHM_KEYS:
            empty_trace = trace_scheduler_execution([], sc05a.shift_config, algorithm_key=key)
            assert empty_trace.steps[-1].selected_ids == ()

            inf_trace = trace_scheduler_execution(
                sc05a.surgeries, sc05a.shift_config, algorithm_key=key
            )
            assert inf_trace.steps[-1].phase == TracePhase.RESULT
            if key in ("classic_greedy", "classic_dp"):
                assert inf_trace.final_result.discarded_infeasible_count == 0
            else:
                assert inf_trace.final_result.total_selected == 0
                assert inf_trace.final_result.discarded_infeasible_count == 3

    def test_te02_presorted_validation_errors_match_production(self) -> None:
        """TE-02: Tracer rejeita sequência fora de ordem ou presorted_start_indices inválido."""
        unsorted = [
            SurgeryRequest("B", start_time=20, finish_time=40),
            SurgeryRequest("A", start_time=10, finish_time=30),
        ]
        for key in ALGORITHM_KEYS:
            with pytest.raises(InvalidSchedulingInputError):
                trace_scheduler_execution(
                    unsorted, algorithm_key=key, is_presorted=True
                )

        with pytest.raises(InvalidSchedulingInputError):
            trace_scheduler_execution(
                [unsorted[1], unsorted[0]],
                ShiftConfig(closing_horizon=35),
                algorithm_key="adapted_dp",
                is_presorted=True,
                presorted_start_indices=[0, 1],
            )

    def test_te03_and_te04_http_validation_and_dos_caps(
        self, live_server: tuple[str, int]
    ) -> None:
        """TE-03 e TE-04: Rejeita JSON malformado, erros de domínio, 413 e limites de DoS."""
        host, port = live_server

        # JSON malformado -> 400
        st_bad_json, _, _ = _http_request(
            host, port, "POST", "/api/trace", b"{bad-json"
        )
        assert st_bad_json == 400

        # Erro de domínio (s_i >= f_i) -> 400
        bad_domain = json.dumps(
            {
                "surgeries": [
                    {"surgery_id": "BAD", "start_time": 100, "finish_time": 50}
                ]
            }
        ).encode("utf-8")
        st_bad_dom, _, _ = _http_request(
            host, port, "POST", "/api/compare", bad_domain
        )
        assert st_bad_dom == 400

        # Payload acima de MAX_REQUEST_BODY_BYTES -> 413
        huge_body = b"{" + b" " * (MAX_REQUEST_BODY_BYTES + 32) + b"}"
        st_413, _, _ = _http_request(host, port, "POST", "/api/trace", huge_body)
        assert st_413 == 413

        # Limite trace n > 200 -> 400
        too_many_trace = json.dumps(
            {
                "surgeries": [
                    {
                        "surgery_id": f"X{i}",
                        "start_time": i,
                        "finish_time": i + 5,
                    }
                    for i in range(MAX_TRACE_INPUT_SIZE + 1)
                ]
            }
        ).encode("utf-8")
        st_trace_cap, _, _ = _http_request(
            host, port, "POST", "/api/trace", too_many_trace
        )
        assert st_trace_cap == 400

        # Limite generate n > 5000 -> 400
        over_gen = json.dumps({"n": MAX_GENERATE_SIZE + 1}).encode("utf-8")
        st_gen_cap, _, _ = _http_request(host, port, "POST", "/api/generate", over_gen)
        assert st_gen_cap == 400

        # Limite benchmark size > 10000 e repetitions > 20 -> 400
        over_bench_n = json.dumps(
            {"sizes": [MAX_BENCHMARK_SIZE + 1], "repetitions": 1}
        ).encode("utf-8")
        st_bn, _, _ = _http_request(host, port, "POST", "/api/benchmark", over_bench_n)
        assert st_bn == 400

        over_bench_r = json.dumps(
            {"sizes": [10], "repetitions": MAX_BENCHMARK_REPETITIONS + 1}
        ).encode("utf-8")
        st_br, _, _ = _http_request(host, port, "POST", "/api/benchmark", over_bench_r)
        assert st_br == 400

    def test_te05_path_traversal_and_unknown_routes_blocked(
        self, live_server: tuple[str, int]
    ) -> None:
        """TE-05: Tentativas de path traversal e rotas desconhecidas retornam 403/404."""
        host, port = live_server

        st_trav, _, body_trav = _http_request(
            host, port, "GET", "/static/../server.py"
        )
        assert st_trav in (403, 404)
        assert b"ThreadingHTTPServer" not in body_trav

        st_unknown_get, _, _ = _http_request(host, port, "GET", "/api/unknown")
        assert st_unknown_get == 404

        st_unknown_post, _, _ = _http_request(
            host, port, "POST", "/api/unknown", b"{}"
        )
        assert st_unknown_post == 404

    def test_te06_xss_payload_roundtrip_and_safe_dom_rendering(
        self, live_server: tuple[str, int]
    ) -> None:
        """TE-06: surgery_id com <script> trafega literalmente e app.js evita innerHTML."""
        host, port = live_server
        xss_id = "<script>alert(1)</script>"
        body = json.dumps(
            {
                "algorithm_key": "adapted_greedy",
                "surgeries": [
                    {
                        "surgery_id": xss_id,
                        "start_time": 100,
                        "finish_time": 200,
                        "surgery_type": "CLEAN",
                        "sterilization_duration": 0,
                    }
                ],
            }
        ).encode("utf-8")

        status, _, raw = _http_request(host, port, "POST", "/api/trace", body)
        assert status == 200
        payload = json.loads(raw.decode("utf-8"))
        assert payload["final_result"]["selected_ids"] == [xss_id]

        app_js = Path("src/ui/static/app.js").read_text(encoding="utf-8")
        assert "innerHTML" not in app_js
