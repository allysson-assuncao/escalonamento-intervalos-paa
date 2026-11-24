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
    ShiftConfig,
    ShiftWindow,
    SurgeryRequest,
)
from src.main import main as cli_main
from src.schedulers import (
    AdaptedDPScheduler,
    AdaptedGreedyScheduler,
    ClassicDPScheduler,
    ClassicGreedyScheduler,
)
from src.ui import (
    ALGORITHM_KEYS,
    MAX_COMPARE_INPUT_SIZE,
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
        """TP-01: Traço passo a passo equivale 100% a schedule() em CASE-01..CASE-04."""
        scheduler_map = {
            "classic_greedy": ClassicGreedyScheduler(),
            "classic_dp": ClassicDPScheduler(),
            "adapted_greedy": AdaptedGreedyScheduler(),
            "adapted_dp": AdaptedDPScheduler(),
        }
        presets = get_scenario_presets()
        assert len(presets) == 4
        assert [p.scenario_id for p in presets] == [
            "CASE-01",
            "CASE-02",
            "CASE-03",
            "CASE-04",
        ]

        for preset in presets:
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
                assert trace.complexity_summary["time_complexity"] == "O(n log n)"
                assert trace.complexity_summary["space_complexity"] == "O(n)"
                assert len(trace.complexity_summary["phases"]) >= 3  # type: ignore[arg-type]

                last_step = trace.steps[-1]
                assert last_step.phase == TracePhase.RESULT
                assert last_step.selected_ids == tuple(
                    s.request.surgery_id for s in official.selected_surgeries
                )

    def test_tp02_adapted_dp_and_greedy_trace_details(self) -> None:
        """TP-02: AdaptedDP registra busca binária e offsets; AdaptedGreedy expõe HH:MM e last_release_minutes."""
        case02 = get_scenario_by_id("CASE-02")
        trace_dp = trace_scheduler_execution(
            case02.surgeries,
            case02.shift_config,
            algorithm_key="adapted_dp",
        )

        expected_phases = {
            TracePhase.PREPROCESSING.value,
            TracePhase.SORTING.value,
            TracePhase.PREDECESSORS.value,
            TracePhase.SELECTION_OR_DP.value,
            TracePhase.BACKTRACKING.value,
            TracePhase.RESULT.value,
        }
        assert expected_phases.issubset(trace_dp.phase_offsets.keys())
        for phase_name, offset in trace_dp.phase_offsets.items():
            assert trace_dp.steps[offset].phase.value == phase_name

        pred_steps = [
            s for s in trace_dp.steps if s.phase == TracePhase.PREDECESSORS
        ]
        assert any(s.binary_search_range is not None for s in pred_steps)
        assert trace_dp.steps[-1].selected_ids == ("S2", "S3")

        # Verifica formatação HH:MM (min) e marcador numérico last_release_minutes no Guloso
        case04 = get_scenario_by_id("CASE-04")
        trace_greedy = trace_scheduler_execution(
            case04.surgeries,
            case04.shift_config,
            algorithm_key="adapted_greedy",
        )
        greedy_steps = [
            s for s in trace_greedy.steps if s.phase == TracePhase.SELECTION_OR_DP
        ]
        assert greedy_steps
        assert any(s.last_release_minutes is not None for s in greedy_steps)
        assert any(
            "min)" in str(val) for val in greedy_steps[0].variables.values()
        )
        assert trace_greedy.steps[-1].selected_ids == ("S2", "S3", "S6", "S7")

    def test_tp03_comparative_arena_and_conflict_detection(self) -> None:
        """TP-03: Arena comparativa retorna 4 abordagens e detecta conflitos em CASE-02 e CASE-03."""
        case02 = get_scenario_by_id("CASE-02")
        entries = run_comparative_arena(case02.surgeries, case02.shift_config)
        assert len(entries) == 4

        by_key = {entry.algorithm_key: entry for entry in entries}
        assert by_key["adapted_greedy"].result.total_selected == 2
        assert by_key["adapted_dp"].result.total_selected == 2
        assert by_key["adapted_greedy"].is_physically_valid is True
        assert by_key["adapted_dp"].is_physically_valid is True
        assert by_key["classic_greedy"].is_physically_valid is False
        assert len(by_key["classic_greedy"].physical_conflicts) >= 1

        case03 = get_scenario_by_id("CASE-03")
        entries_03 = run_comparative_arena(case03.surgeries, case03.shift_config)
        by_key_03 = {entry.algorithm_key: entry for entry in entries_03}
        assert by_key_03["adapted_greedy"].is_physically_valid is True
        assert by_key_03["adapted_dp"].is_physically_valid is True
        assert by_key_03["classic_greedy"].is_physically_valid is False


class TestHttpServerAndCliHappyPath:
    """Testes de integração da API HTTP local e CLI headless (TP-04 a TP-06)."""

    def test_tp04_static_assets_and_scenarios_endpoint(
        self, live_server: tuple[str, int]
    ) -> None:
        """TP-04: GET /, /styles.css, /app.js e /api/scenarios retornam HTTP 200 com layout enxuto."""
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

        html_text = Path("src/ui/static/index.html").read_text(encoding="utf-8")
        assert html_text.count('class="tab-btn') == 2
        assert "complexity-summary-card" in html_text
        assert "tab-benchmark" not in html_text
        assert "presorted-checkbox" not in html_text
        assert "generate-btn" not in html_text

        status, ctype, raw = _http_request(host, port, "GET", "/api/scenarios")
        assert status == 200
        assert "application/json" in ctype
        payload = json.loads(raw.decode("utf-8"))
        scenario_ids = [item["scenario_id"] for item in payload["scenarios"]]
        assert scenario_ids == ["CASE-01", "CASE-02", "CASE-03", "CASE-04"]

    def test_tp05_trace_and_compare_endpoints(
        self, live_server: tuple[str, int]
    ) -> None:
        """TP-05: POST /api/trace e POST /api/compare retornam JSON válido para CASE-02."""
        host, port = live_server
        body = json.dumps(
            {
                "algorithm_key": "adapted_dp",
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
        assert trace_data["complexity_summary"]["time_complexity"] == "O(n log n)"

        status_cmp, _, raw_cmp = _http_request(host, port, "POST", "/api/compare", body)
        assert status_cmp == 200
        cmp_data = json.loads(raw_cmp.decode("utf-8"))
        assert len(cmp_data["entries"]) == 4

    def test_tp06_cli_headless_modes(self, capsys: pytest.CaptureFixture[str]) -> None:
        """TP-06: src/main.py executa --scenario e --algorithm em modo headless."""
        rc_sc = cli_main(["--scenario", "CASE-02"])
        assert rc_sc == 0
        out_sc = capsys.readouterr().out
        assert "Impacto da Esterilização" in out_sc
        assert "Adapted Greedy" in out_sc

        rc_single = cli_main(["--scenario", "CASE-02", "--algorithm", "adapted_dp"])
        assert rc_single == 0
        out_single = capsys.readouterr().out
        assert "Adapted Dynamic Programming" in out_single
        assert "Classic Greedy" not in out_single

        # Valida invocação como módulo via subprocesso
        proc = subprocess.run(
            [sys.executable, "-m", "src.main", "--scenario", "CASE-02"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0
        assert "S2, S3" in proc.stdout


class TestUiSecurityAndEdgeCases:
    """Casos de borda do tracer, remoção de rotas e proteção contra XSS/path traversal."""

    def test_te01_empty_and_all_infeasible_traces(self) -> None:
        """TE-01: Entradas vazia e totalmente inviável geram traço limpo."""
        cfg = ShiftConfig(
            closing_horizon=1080,
            shift_window=ShiftWindow(start=720, end=780),
        )
        all_infeasible = [
            SurgeryRequest("I1", start_time=700, finish_time=740),
            SurgeryRequest("I2", start_time=720, finish_time=760),
            SurgeryRequest("I3", start_time=1020, finish_time=1090),
        ]
        for key in ALGORITHM_KEYS:
            empty_trace = trace_scheduler_execution([], cfg, algorithm_key=key)
            assert empty_trace.steps[-1].selected_ids == ()

            inf_trace = trace_scheduler_execution(all_infeasible, cfg, algorithm_key=key)
            assert inf_trace.steps[-1].phase == TracePhase.RESULT
            if key in ("classic_greedy", "classic_dp"):
                assert inf_trace.final_result.discarded_infeasible_count == 0
            else:
                assert inf_trace.final_result.total_selected == 0
                assert inf_trace.final_result.discarded_infeasible_count == 3

    def test_te02_removed_routes_return_404_and_invalid_algo_returns_400(
        self, live_server: tuple[str, int]
    ) -> None:
        """TE-02: Rotas removidas (/api/generate, /api/benchmark) retornam 404; algoritmo inválido 400."""
        host, port = live_server

        st_gen, _, _ = _http_request(host, port, "POST", "/api/generate", b"{}")
        assert st_gen == 404

        st_bench, _, _ = _http_request(host, port, "POST", "/api/benchmark", b"{}")
        assert st_bench == 404

        bad_algo = json.dumps({"algorithm_key": "naive_reduction", "surgeries": []}).encode("utf-8")
        st_algo, _, _ = _http_request(host, port, "POST", "/api/trace", bad_algo)
        assert st_algo == 400

    def test_te03_and_te04_http_validation_and_dos_caps(
        self, live_server: tuple[str, int]
    ) -> None:
        """TE-03 e TE-04: Rejeita JSON malformado, erros de domínio, 413 e limites de DoS."""
        host, port = live_server

        st_bad_json, _, _ = _http_request(
            host, port, "POST", "/api/trace", b"{bad-json"
        )
        assert st_bad_json == 400

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

        huge_body = b"{" + b" " * (MAX_REQUEST_BODY_BYTES + 32) + b"}"
        st_413, _, _ = _http_request(host, port, "POST", "/api/trace", huge_body)
        assert st_413 == 413

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

        too_many_compare = json.dumps(
            {
                "surgeries": [
                    {
                        "surgery_id": f"C{i}",
                        "start_time": i,
                        "finish_time": i + 5,
                    }
                    for i in range(MAX_COMPARE_INPUT_SIZE + 1)
                ]
            }
        ).encode("utf-8")
        st_cmp_cap, _, _ = _http_request(
            host, port, "POST", "/api/compare", too_many_compare
        )
        assert st_cmp_cap == 400

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

    def test_te07_hhmm_mask_and_client_time_validation_present(self) -> None:
        """TE-07: Interface usa máscara automática HH:MM e bloqueia startTime >= finishTime."""
        index_html = Path("src/ui/static/index.html").read_text(encoding="utf-8")
        app_js = Path("src/ui/static/app.js").read_text(encoding="utf-8")

        assert 'class="hhmm-input"' in index_html
        assert 'id="new-start"' in index_html
        assert 'id="new-finish"' in index_html
        assert "attachHhmmInputMask" in app_js
        assert "parseHhmmToMinutes" in app_js
        assert "startTime >= finishTime" in app_js
