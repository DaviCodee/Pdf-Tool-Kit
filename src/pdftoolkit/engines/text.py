"""Extração e representação de texto de PDFs.

Cobre texto cru, layout posicional, Markdown e HTML. A maioria das funções depende
apenas de ``pypdf`` (núcleo). ``pages_to_markdown`` usa ``pdfplumber`` (extra
``tables``) e levanta ``MissingDependencyError`` se não estiver instalado.
"""

from __future__ import annotations

import io
import json
import re
from collections.abc import Sequence
from html import escape
from typing import Any

from pdftoolkit.core.errors import MissingDependencyError, OperationError
from pdftoolkit.engines import pypdf_engine as pe

# Tolerância em pontos para considerar duas palavras na mesma linha.
_LINE_TOLERANCE = 2.0

# Tamanhos de fonte (pt) usados para inferir nível de cabeçalho em Markdown.
_H1_MIN, _H2_MIN, _H3_MIN = 18.0, 14.0, 12.0

BBox = tuple[float, float, float, float]


def extract_pages_text(data: bytes, password: str | None = None) -> list[str]:
    """Retorna uma string por página (string vazia para páginas sem texto)."""
    return pe.extract_page_texts(data, password)


def _pdfplumber() -> Any:
    try:
        import pdfplumber
    except ImportError as exc:
        raise MissingDependencyError(
            "extração de layout/markdown requer o extra 'tables' "
            "(pip install pdftoolkit[tables])"
        ) from exc
    return pdfplumber


def _open_plumber(data: bytes) -> Any:
    pdfplumber = _pdfplumber()
    return pdfplumber.open(io.BytesIO(data))


def extract_pages_layout(data: bytes, password: str | None = None) -> list[dict[str, Any]]:
    """Extrai texto com bounding boxes aproximadas via ``extraction_mode='layout'``.

    Retorna ``[{page: int, blocks: [{text: str, bbox: (x0, y0, x1, y1)}]}, ...]``.

    Como o pypdf com ``layout`` devolve o texto já alinhado por espaços, não temos
    palavras individuais; cada bloco é uma linha contínua identificada pela sua
    posição vertical no fluxo da página.
    """
    _pdfplumber()  # garante que o extra está instalado antes de gastar trabalho
    reader = pe.open_reader(data, password)
    pages: list[dict[str, Any]] = []
    try:
        for index, page in enumerate(reader.pages):
            layout_text = page.extract_text(extraction_mode="layout") or ""
            blocks = _layout_to_blocks(layout_text)
            pages.append({"page": index + 1, "blocks": blocks})
    except Exception as exc:  # pragma: no cover - entrada corrompida
        raise OperationError(f"falha ao extrair layout: {exc}") from exc
    finally:
        # PdfReader não exige close, mas mantemos o leitor descartável.
        del reader
    return pages


def _layout_to_blocks(text: str) -> list[dict[str, Any]]:
    """Quebra o texto de ``layout`` em blocos com bbox aproximada."""
    blocks: list[dict[str, Any]] = []
    _FLOAT = r"-?\d+(?:\.\d+)?"
    line_re = re.compile(rf"^\s*({_FLOAT}),({_FLOAT}),({_FLOAT}),({_FLOAT}):(.*)$")
    for raw_line in text.splitlines():
        match = line_re.match(raw_line)
        if not match:
            continue
        x0, y0, w, h = (float(value) for value in match.groups()[:4])
        content = match.group(5).strip()
        if not content:
            continue
        blocks.append({"text": content, "bbox": (x0, y0, x0 + w, y0 + h)})
    return blocks


def pages_to_markdown(data: bytes, password: str | None = None) -> str:
    """Converte o PDF para Markdown básico, inferindo cabeçalhos pelo tamanho da fonte."""
    del password  # pdfplumber aceita senha via construtor; não expomos aqui
    chunks: list[str] = []
    with _open_plumber(data) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            if page_number > 1:
                chunks.append("\n\n---\n\n")
            words = page.extract_words(keep_blank_chars=False)
            if not words:
                continue
            lines = _words_to_lines(words)
            chunks.extend(_lines_to_markdown(lines))
    return "".join(chunks).strip() + "\n"


def _words_to_lines(words: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Agrupa palavras em linhas com base na posição vertical (``top``)."""
    if not words:
        return []
    lines: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = [words[0]]
    current_top = float(words[0]["top"])
    for word in words[1:]:
        top = float(word["top"])
        if abs(top - current_top) <= _LINE_TOLERANCE:
            current.append(word)
        else:
            lines.append(_finalize_line(current))
            current = [word]
            current_top = top
    lines.append(_finalize_line(current))
    return lines


def _finalize_line(words: list[dict[str, Any]]) -> dict[str, Any]:
    text = " ".join(str(word["text"]) for word in words)
    size = max(float(word.get("height", 0)) for word in words)
    return {"text": text, "size": size}


def _lines_to_markdown(lines: list[dict[str, Any]]) -> list[str]:
    rendered: list[str] = []
    for line in lines:
        text = line["text"].strip()
        if not text:
            continue
        size = line["size"]
        prefix = ""
        if size >= _H1_MIN:
            prefix = "# "
        elif size >= _H2_MIN:
            prefix = "## "
        elif size >= _H3_MIN:
            prefix = "### "
        rendered.append(prefix + text)
    return rendered


def pages_to_html(data: bytes, password: str | None = None) -> str:
    """Empacota o texto extraído de cada página em um documento HTML simples.

    Usa fonte monoespaçada e ``<pre>`` para preservar espaçamento aproximado.
    """
    pages = extract_pages_text(data, password)
    body_parts = [
        f"<section class=\"page\"><h2>Página {index + 1}</h2>"
        f"<pre>{escape(text) or '(sem texto)'}</pre></section>"
        for index, text in enumerate(pages)
    ]
    css = (
        "<style>body{font-family:sans-serif;max-width:780px;margin:2em auto;"
        "padding:0 1em;color:#222}section.page{border-bottom:1px solid #ccc;"
        "padding:1em 0}pre{font-family:ui-monospace,Menlo,Consolas,monospace;"
        "white-space:pre-wrap;font-size:0.9em;background:#f6f8fa;padding:1em;"
        "border-radius:6px}</style>"
    )
    return (
        "<!DOCTYPE html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\">"
        f"<title>PDF</title>{css}</head><body>{''.join(body_parts)}</body></html>"
    )


def layout_to_json(pages: list[dict[str, Any]]) -> bytes:
    """Serializa a saída de :func:`extract_pages_layout` em JSON UTF-8 formatado."""
    return json.dumps(pages, ensure_ascii=False, indent=2).encode("utf-8")
