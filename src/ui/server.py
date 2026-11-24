"""Servidor HTTP local em loopback (Stdlib) para a interface de simulação visual."""

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

from src.domain.exceptions import InvalidSchedulingInputError
from src.domain.models import (
    ShiftConfig,
    ShiftWindow,
    SurgeryRequest,
    SurgeryType,
    is_strict_int,
)
from src.ui.scenarios_catalog import get_scenario_presets
from src.ui.tracer import (
    MAX_TRACE_INPUT_SIZE,
    run_comparative_arena,
    serialize_comparison_to_dict,
    serialize_scenario_preset_to_dict,
    serialize_trace_to_dict,
    trace_scheduler_execution,
)

DEFAULT_HOST: str = "127.0.0.1"
DEFAULT_PORT: int = 8765
MAX_REQUEST_BODY_BYTES: int = 262_144
MAX_COMPARE_INPUT_SIZE: int = 500

STATIC_DIR: Path = Path(__file__).resolve().parent / "static"

_MIME_TYPES: dict[str, str] = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}


class _PayloadTooLargeError(ValueError):
    """Exceção interna para payloads acima do limite de segurança HTTP 413."""


def parse_shift_config_payload(raw_config: object) -> ShiftConfig | None:
    """Converte e valida objeto JSON opcional em ShiftConfig."""
    if raw_config is None:
        return None
    if not isinstance(raw_config, dict):
        raise InvalidSchedulingInputError(
            "shift_config deve ser um objeto JSON ou null."
        )

    closing_horizon = raw_config.get("closing_horizon")
    if not is_strict_int(closing_horizon):
        raise InvalidSchedulingInputError(
            "closing_horizon deve ser um inteiro estrito."
        )

    raw_window = raw_config.get("shift_window")
    shift_window: ShiftWindow | None = None
    if raw_window is not None:
        if not isinstance(raw_window, dict):
            raise InvalidSchedulingInputError(
                "shift_window deve ser um objeto JSON com start e end."
            )
        win_start = raw_window.get("start")
        win_end = raw_window.get("end")
        if not is_strict_int(win_start) or not is_strict_int(win_end):
            raise InvalidSchedulingInputError(
                "Os limites start e end de shift_window devem ser inteiros estritos."
            )
        shift_window = ShiftWindow(start=win_start, end=win_end)

    return ShiftConfig(closing_horizon=closing_horizon, shift_window=shift_window)


def parse_surgeries_payload(raw_surgeries: object) -> list[SurgeryRequest]:
    """Converte e valida lista JSON em instâncias imutáveis de SurgeryRequest."""
    if not isinstance(raw_surgeries, list):
        raise InvalidSchedulingInputError(
            "O campo surgeries deve ser uma lista JSON de cirurgias."
        )

    parsed: list[SurgeryRequest] = []
    for index, item in enumerate(raw_surgeries):
        if not isinstance(item, dict):
            raise InvalidSchedulingInputError(
                f"O item {index} em surgeries deve ser um objeto JSON."
            )

        surgery_id = item.get("surgery_id")
        start_time = item.get("start_time")
        finish_time = item.get("finish_time")
        raw_type = item.get("surgery_type", SurgeryType.CLEAN.value)
        sterilization = item.get("sterilization_duration", 0)

        if not isinstance(raw_type, str):
            raise InvalidSchedulingInputError(
                "surgery_type deve ser 'CLEAN' ou 'CONTAMINATED'."
            )
        try:
            surgery_type = SurgeryType(raw_type)
        except ValueError as exc:
            raise InvalidSchedulingInputError(
                f"surgery_type inválido '{raw_type}' no item {index}."
            ) from exc

        parsed.append(
            SurgeryRequest(
                surgery_id=surgery_id,  # type: ignore[arg-type]
                start_time=start_time,  # type: ignore[arg-type]
                finish_time=finish_time,  # type: ignore[arg-type]
                surgery_type=surgery_type,
                sterilization_duration=sterilization,  # type: ignore[arg-type]
            )
        )
    return parsed


def _handle_trace_request(payload: dict[str, object]) -> dict[str, object]:
    """Processa requisição POST /api/trace com limites de tamanho e validação."""
    surgeries = parse_surgeries_payload(payload.get("surgeries"))
    if len(surgeries) > MAX_TRACE_INPUT_SIZE:
        raise InvalidSchedulingInputError(
            f"A simulação passo a passo aceita no máximo {MAX_TRACE_INPUT_SIZE} cirurgias."
        )
    shift_config = parse_shift_config_payload(payload.get("shift_config"))
    algorithm_key = payload.get("algorithm_key", "adapted_greedy")
    if not isinstance(algorithm_key, str):
        raise InvalidSchedulingInputError("algorithm_key deve ser uma string.")

    trace = trace_scheduler_execution(
        surgeries,
        shift_config,
        algorithm_key=algorithm_key,
    )
    return serialize_trace_to_dict(trace)


def _handle_compare_request(payload: dict[str, object]) -> dict[str, object]:
    """Processa requisição POST /api/compare para os 4 algoritmos."""
    surgeries = parse_surgeries_payload(payload.get("surgeries"))
    if len(surgeries) > MAX_COMPARE_INPUT_SIZE:
        raise InvalidSchedulingInputError(
            f"A comparação suporta no máximo {MAX_COMPARE_INPUT_SIZE} cirurgias."
        )
    shift_config = parse_shift_config_payload(payload.get("shift_config"))
    entries = run_comparative_arena(surgeries, shift_config)
    return {
        "entries": [serialize_comparison_to_dict(entry) for entry in entries],
    }


class SimulationRequestHandler(BaseHTTPRequestHandler):
    """Manipulador HTTP para ativos estáticos e endpoints JSON da interface."""

    def log_message(self, format: str, *args: object) -> None:
        """Suprime logs verbosos padrão em stderr durante testes e uso interativo."""
        return

    def _send_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        """Envia resposta JSON UTF-8 com cabeçalhos seguros."""
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _send_static_file(self, relative_path: str) -> None:
        """Serve arquivo dentro de STATIC_DIR bloqueando travessia de diretório."""
        static_root = STATIC_DIR.resolve()
        candidate = (static_root / relative_path).resolve()

        if not candidate.is_relative_to(static_root):
            self._send_json(
                HTTPStatus.FORBIDDEN,
                {"error": "Acesso negado fora do diretório estático."},
            )
            return
        if not candidate.is_file():
            self._send_json(
                HTTPStatus.NOT_FOUND,
                {"error": "Arquivo estático não encontrado."},
            )
            return

        content = candidate.read_bytes()
        mime_type = _MIME_TYPES.get(
            candidate.suffix.lower(), "application/octet-stream"
        )
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def _read_json_body(self) -> dict[str, object]:
        """Lê e valida o corpo JSON respeitando MAX_REQUEST_BODY_BYTES."""
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise InvalidSchedulingInputError(
                "Cabeçalho Content-Length obrigatório em requisições POST."
            )
        try:
            content_length = int(raw_length)
        except ValueError as exc:
            raise InvalidSchedulingInputError(
                "Cabeçalho Content-Length inválido."
            ) from exc

        if content_length < 0:
            raise InvalidSchedulingInputError(
                "Content-Length não pode ser negativo."
            )
        if content_length > MAX_REQUEST_BODY_BYTES:
            # Drena excesso limitado no buffer TCP para evitar TCP RST no Windows ao responder 413
            if content_length <= MAX_REQUEST_BODY_BYTES * 4:
                self.rfile.read(content_length)
            self.close_connection = True
            raise _PayloadTooLargeError(
                f"Corpo da requisição excede o limite de {MAX_REQUEST_BODY_BYTES} bytes."
            )

        raw_bytes = self.rfile.read(content_length)
        if len(raw_bytes) > MAX_REQUEST_BODY_BYTES:
            raise _PayloadTooLargeError(
                f"Corpo da requisição excede o limite de {MAX_REQUEST_BODY_BYTES} bytes."
            )

        try:
            decoded = json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InvalidSchedulingInputError(
                "JSON malformado no corpo da requisição."
            ) from exc

        if not isinstance(decoded, dict):
            raise InvalidSchedulingInputError(
                "O corpo JSON deve ser um objeto (dicionário)."
            )
        return decoded

    def do_GET(self) -> None:
        """Atende rotas estáticas e GET /api/scenarios."""
        raw_path = urlsplit(self.path).path
        clean_path = unquote(raw_path)

        if clean_path in ("/", "/index.html"):
            self._send_static_file("index.html")
            return
        if clean_path in ("/styles.css", "/app.js"):
            self._send_static_file(clean_path.lstrip("/"))
            return
        if clean_path.startswith("/static/"):
            rel_path = clean_path[len("/static/") :]
            if not rel_path:
                self._send_json(
                    HTTPStatus.NOT_FOUND, {"error": "Recurso estático não especificado."}
                )
                return
            self._send_static_file(rel_path)
            return
        if clean_path == "/api/scenarios":
            presets = [serialize_scenario_preset_to_dict(p) for p in get_scenario_presets()]
            self._send_json(HTTPStatus.OK, {"scenarios": presets})
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Rota não encontrada."})

    def do_POST(self) -> None:
        """Atende endpoints JSON de rastreamento e comparação dos 4 algoritmos."""
        clean_path = unquote(urlsplit(self.path).path)
        routes = {
            "/api/trace": _handle_trace_request,
            "/api/compare": _handle_compare_request,
        }
        handler = routes.get(clean_path)
        if handler is None:
            raw_len = (self.headers.get("Content-Length") or "").strip()
            if raw_len.isdigit():
                self.rfile.read(min(int(raw_len), MAX_REQUEST_BODY_BYTES))
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Rota POST não encontrada."})
            return

        try:
            payload = self._read_json_body()
            response = handler(payload)
        except _PayloadTooLargeError as exc:
            self._send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": str(exc)})
            return
        except InvalidSchedulingInputError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        self._send_json(HTTPStatus.OK, response)


def create_http_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> ThreadingHTTPServer:
    """Instancia o servidor HTTP local em loopback pronto para servir a interface."""
    if not isinstance(host, str) or not host.strip():
        raise InvalidSchedulingInputError("O host do servidor deve ser não vazio.")
    if not is_strict_int(port) or port < 0 or port > 65535:
        raise InvalidSchedulingInputError(
            "A porta do servidor deve ser um inteiro entre 0 e 65535."
        )
    return ThreadingHTTPServer((host, port), SimulationRequestHandler)
