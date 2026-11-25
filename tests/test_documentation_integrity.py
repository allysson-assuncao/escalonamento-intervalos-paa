"""Testes automatizados de integridade estrutural, links e âncoras da documentação."""

from pathlib import Path
import re

import pytest

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
DOCS_DIR: Path = REPO_ROOT / "docs"
README_PATH: Path = REPO_ROOT / "README.md"
MATH_DOC_PATH: Path = DOCS_DIR / "formulacao-matematica-e-comparativo-algoritmos.md"
GUIDE_PATH: Path = DOCS_DIR / "guia-revisao-arquitetura-e-apresentacao.md"

DOC_FILES: tuple[Path, ...] = (README_PATH, MATH_DOC_PATH, GUIDE_PATH)

_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_LINE_ANCHOR_PATTERN = re.compile(r"^L(\d+)(?:-L(\d+))?$")
_HOST_PATH_OR_SECRET_PATTERN = re.compile(
    r"(?:[A-Za-z]:[/\\]Users[/\\]|[A-Za-z]:[/\\]Python\d+|file:///|"
    r"\b(?:password|secret|api_key|token)\s*[:=])",
    re.IGNORECASE,
)


def extract_markdown_links(markdown_text: str) -> list[tuple[str, str]]:
    """Extrai pares (texto, destino) de links Markdown fora de blocos de código."""
    cleaned = re.sub(r"```.*?```", "", markdown_text, flags=re.DOTALL)
    return _LINK_PATTERN.findall(cleaned)


def validate_markdown_link(
    doc_path: Path,
    raw_target: str,
    *,
    repo_root: Path = REPO_ROOT,
) -> tuple[Path, tuple[int, int] | None]:
    """Valida que um link relativo aponta para arquivo existente e linhas válidas."""
    target = raw_target.strip()
    if target.startswith("#"):
        return doc_path, None
    if target.startswith(("http://", "https://")):
        return doc_path, None
    if target.startswith("file://") or re.match(r"^[A-Za-z]:[/\\]", target):
        raise ValueError(f"Caminho absoluto proibido na documentação: '{target}'.")

    file_part, _, fragment = target.partition("#")
    resolved_root = repo_root.resolve()
    resolved_file = (doc_path.parent / file_part).resolve()

    if not resolved_file.is_relative_to(resolved_root):
        raise ValueError(
            f"Link aponta para fora da raiz do repositório: '{target}'."
        )
    if not resolved_file.exists():
        raise ValueError(f"Arquivo referenciado não encontrado: '{target}'.")

    if not fragment:
        return resolved_file, None

    match = _LINE_ANCHOR_PATTERN.match(fragment)
    if match is None:
        return resolved_file, None

    start_line = int(match.group(1))
    end_line = int(match.group(2)) if match.group(2) is not None else start_line
    total_lines = len(resolved_file.read_text(encoding="utf-8").splitlines())

    if start_line < 1 or end_line < start_line or end_line > total_lines:
        raise ValueError(
            f"Intervalo de linhas inválido '#{fragment}' em '{resolved_file.name}' "
            f"(total de linhas: {total_lines})."
        )
    return resolved_file, (start_line, end_line)


class TestDocumentationIntegrityHappyPath:
    """Validação de existência, seções, links relativos e intervalos #Lxx-Lyy."""

    def test_tp01_required_docs_exist_and_contain_mandated_sections(self) -> None:
        """TP-01: Verifica presença dos 2 documentos e suas seções obrigatórias."""
        for path in DOC_FILES:
            assert path.is_file(), f"Documento obrigatório ausente: {path}"
            content = path.read_text(encoding="utf-8")
            assert len(content.strip()) > 500

        readme = README_PATH.read_text(encoding="utf-8")
        for marker in (
            "Problema Original vs. Adaptação Autoral",
            "Contrexemplo `CASE-02`",
            "Instalação, Execução e Testes",
            "docs/formulacao-matematica-e-comparativo-algoritmos.md",
            "docs/guia-revisao-arquitetura-e-apresentacao.md",
        ):
            assert marker in readme

        math_doc = MATH_DOC_PATH.read_text(encoding="utf-8")
        for marker in (
            "Dicionário Completo de Notação",
            "Comparativo Matemático dos 4 Algoritmos",
            "CASE-02",
            "CASE-03",
        ):
            assert marker in math_doc

        guide = GUIDE_PATH.read_text(encoding="utf-8")
        for marker in (
            "Módulo 1",
            "Módulo 2",
            "Módulo 3",
            "Módulo 4",
            "Módulo 5",
        ):
            assert marker in guide

    def test_tp02_and_tp03_all_links_and_line_anchors_resolve_cleanly(self) -> None:
        """TP-02 e TP-03: Todos os links relativos e #Lxx-Lyy existem dentro dos limites."""
        total_links = 0
        total_anchored_links = 0

        for doc_path in DOC_FILES:
            content = doc_path.read_text(encoding="utf-8")
            for label, target in extract_markdown_links(content):
                total_links += 1
                resolved_file, line_range = validate_markdown_link(doc_path, target)
                if line_range is not None:
                    total_anchored_links += 1
                    lines = resolved_file.read_text(encoding="utf-8").splitlines()
                    slice_text = "\n".join(lines[line_range[0] - 1 : line_range[1]])
                    clean_label = label.strip("` ")
                    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", clean_label):
                        assert clean_label in slice_text, (
                            f"Símbolo '{clean_label}' não encontrado em "
                            f"{resolved_file.name}#L{line_range[0]}-L{line_range[1]}"
                        )

        assert total_links >= 15
        assert total_anchored_links >= 20


class TestDocumentationIntegrityEdgeCases:
    """Casos de borda, segurança e portabilidade dos arquivos Markdown."""

    def test_te01_validator_rejects_broken_links_and_invalid_line_ranges(self) -> None:
        """TE-01: Validador rejeita arquivos ausentes, travessia e intervalos invertidos."""
        with pytest.raises(ValueError):
            validate_markdown_link(README_PATH, "src/does_not_exist.py")
        with pytest.raises(ValueError):
            validate_markdown_link(GUIDE_PATH, "../../fora_do_repo.py")
        with pytest.raises(ValueError):
            validate_markdown_link(GUIDE_PATH, "../src/domain/exceptions.py#L5-L2")
        with pytest.raises(ValueError):
            validate_markdown_link(GUIDE_PATH, "../src/domain/exceptions.py#L0")
        with pytest.raises(ValueError):
            validate_markdown_link(GUIDE_PATH, "../src/domain/exceptions.py#L1-L999")
        with pytest.raises(ValueError):
            validate_markdown_link(README_PATH, "file:///C:/temp/test.py")

    def test_te02_no_host_absolute_paths_or_secrets_in_documentation(self) -> None:
        """TE-02: Garante zero caminhos locais absolutos ou credenciais na documentação."""
        for doc_path in DOC_FILES:
            content = doc_path.read_text(encoding="utf-8")
            match = _HOST_PATH_OR_SECRET_PATTERN.search(content)
            assert match is None, (
                f"Padrão proibido '{match.group(0)}' encontrado em {doc_path.name}"
            )

    def test_te03_balanced_markdown_and_mermaid_code_fences(self) -> None:
        """TE-03: Todos os blocos cercados (``` e Mermaid) estão devidamente fechados."""
        for doc_path in DOC_FILES:
            content = doc_path.read_text(encoding="utf-8")
            fence_count = sum(
                1 for line in content.splitlines() if line.lstrip().startswith("```")
            )
            assert fence_count % 2 == 0, f"Bloco de código não fechado em {doc_path.name}"
