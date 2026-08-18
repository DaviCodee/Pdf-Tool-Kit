"""Fallback robusto sobre o pikepdf.

Usado quando o pypdf falha ao abrir/regravar documentos problemáticos (ex.: remoção
de senha em PDFs com estruturas que o pypdf não digere bem).
"""

from __future__ import annotations

import math
import re
from io import BytesIO
from typing import Any

import pikepdf

from pdftoolkit.core.errors import EncryptedPdfError, OperationError

# Identidade do toolkit no /Info do PDF. Sobrepõe o Producer/Creator que o
# pikepdf injeta por padrão ("pikepdf X.Y.Z" / vazio) pra que todo PDF
# gerado pelo davi·code carregue a marca do projeto.
DC_PRODUCER = "davi-code (https://github.com/DaviCodee/Pdf-Tool-Kit)"
DC_CREATOR = "davi-code (https://github.com/DaviCodee/Pdf-Tool-Kit)"


def _stamp_dc_metadata(pdf: "pikepdf.Pdf") -> None:
    """Carimba Producer/Creator davi-code em ``pdf.docinfo`` (pikepdf).

    No pikepdf, o /Info fica em ``pdf.docinfo`` (lazy-criado). Se já existir
    (ex.: PDF de entrada), sobrescreve — a marca davi-code tem prioridade.

    NOTA: usa ``pdf.docinfo`` (string livre) em vez de ``open_metadata``,
    porque o open_metadata rejeita valores com espaços ou ``/`` como
    "Invalid tag name" — e o nosso DC_PRODUCER contém "/".
    """
    pdf.docinfo["/Producer"] = DC_PRODUCER
    pdf.docinfo["/Creator"] = DC_CREATOR

# Sufixos de variação que o PDF usa pra diferenciar pesos/estilos de uma família.
# Match exact (case-sensitive) sobre o final do nome (sem "-Italic" extra, etc.).
_STYLE_SUFFIXES = (
    "-BoldOblique",
    "-BoldItalic",
    "-BoldOblique",
    "-Bold",
    "-Italic",
    "-Oblique",
    "-Roman",
    "-Regular",
    "-Light",
    "-Medium",
    "-Semibold",
    "-Black",
)


def _split_basename(basename: str) -> tuple[str | None, str, str]:
    """Decompõe /BaseFont em (subset_prefix, family, style).

    PDFs costumam usar `<subset>+<FamilyName>-<Style>` (ex: ``ABCDEF+Helvetica-Bold``).
    Strip o prefixo de subset (5-6 letras maiúsculas + `+`) e o sufixo de variação;
    o resto é a família. Style fica vazio quando o nome é exatamente o nome da família.
    """
    name = basename.lstrip("/")
    subset = ""
    if "+" in name:
        head, _, tail = name.partition("+")
        # Prefixo de subset: 5-6 letras maiúsculas (formato padrão 6; alguns
        # geradores usam 5). Aceita ambos.
        if re.fullmatch(r"[A-Z]{5,6}", head):
            subset = head
            name = tail
    family = name
    style = ""
    for suf in sorted(_STYLE_SUFFIXES, key=len, reverse=True):
        if name.endswith(suf) and len(name) > len(suf):
            family = name[: -len(suf)]
            style = suf.lstrip("-")
            break
    return (subset or None), family, style


def _font_from_obj(font_obj: Any) -> dict[str, Any] | None:
    """Extrai metadados de um font dict. Devolve None se BaseFont ausente."""
    if font_obj is None:
        return None
    try:
        base = font_obj.get("/BaseFont")
    except Exception:
        return None
    if base is None:
        return None
    raw_name = str(base).lstrip("/")
    subset, family, style = _split_basename(str(base))
    try:
        sub = font_obj.get("/Subtype")
    except Exception:
        sub = None
    subtype = str(sub).lstrip("/") if sub is not None else ""
    try:
        enc = font_obj.get("/Encoding")
    except Exception:
        enc = None
    encoding = str(enc).lstrip("/") if enc is not None else ""
    # Embedded = /FontDescriptor presente E com /FontFile* (2 = TrueType, 3 = CFF).
    embedded = False
    try:
        fd = font_obj.get("/FontDescriptor")
        if fd is not None:
            for key in ("/FontFile", "/FontFile2", "/FontFile3"):
                if fd.get(key) is not None:
                    embedded = True
                    break
    except Exception:
        pass
    return {
        "name": raw_name,
        "family": family,
        "style": style,
        "subset": subset,
        "subtype": subtype or "unknown",
        "encoding": encoding or None,
        "embedded": embedded,
    }


def _walk_resources(resources: Any, visit: Any) -> None:
    """Depth-first walk de resources, descendo em /XObject (Form XObjects).

    PDFs malformados podem ter ponteiros cíclicos; o limite de profundidade
    evita recursão infinita nesse caso.
    """
    if resources is None:
        return
    try:
        font_dict = resources.get("/Font")
    except Exception:
        font_dict = None
    if font_dict:
        for key in font_dict.keys():
            try:
                visit(font_dict[key])
            except Exception:
                continue
    try:
        xobjects = resources.get("/XObject")
    except Exception:
        xobjects = None
    if xobjects:
        for key in xobjects.keys():
            try:
                sub_res = xobjects[key].get("/Resources")
            except Exception:
                sub_res = None
            if sub_res is not None:
                _walk_resources(sub_res, visit)


def list_fonts(data: bytes) -> list[dict[str, Any]]:
    """Lista as fontes do PDF: páginas + AcroForm default resources + Form XObjects.

    Para cada fonte devolve:
    - name: ``BaseFont`` (com subset prefix preservado)
    - family: nome sem subset/sufixo (``AAAAA+Helvetica-Bold`` → ``Helvetica``)
    - style: variação (``Bold``, ``Italic``, ...); vazio quando nome = família
    - subtype: ``Type1``, ``TrueType``, ``CIDFontType2``, ``Type0``, ...
    - encoding: /Encoding (ex: ``WinAnsiEncoding``)
    - embedded: bool — font está embutida via /FontFile{,2,3}
    - subset: prefixo (``AAAAA``) se for subset embedding, senão ``None``
    """
    fonts: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    try:
        with pikepdf.open(BytesIO(data)) as pdf:
            visit = lambda fobj: _collect_font(fobj, fonts, seen)
            for page in pdf.pages:
                _walk_resources(page.get("/Resources"), visit)
            # AcroForm default resources (fonts compartilhados entre widgets).
            acroform = pdf.Root.get("/AcroForm")
            if acroform is not None:
                _walk_resources(acroform.get("/DR"), visit)
        return fonts
    except pikepdf.PasswordError as exc:
        raise EncryptedPdfError("PDF protegido") from exc
    except Exception as exc:
        raise OperationError(f"falha ao listar fontes: {exc}") from exc


def _collect_font(font_obj: Any, fonts: list[dict[str, Any]], seen: set[tuple[str, str]]) -> None:
    info = _font_from_obj(font_obj)
    if info is None:
        return
    key = (info["name"], info["subtype"])
    if key in seen:
        return
    seen.add(key)
    fonts.append(info)


def remove_password(data: bytes, password: str | None = None) -> bytes:
    """Abre um PDF protegido e o regrava sem criptografia."""
    try:
        with pikepdf.open(BytesIO(data), password=password or "") as pdf:
            _stamp_dc_metadata(pdf)
            out = BytesIO()
            pdf.save(out)
            return out.getvalue()
    except pikepdf.PasswordError as exc:
        raise EncryptedPdfError("senha ausente ou incorreta") from exc
    except Exception as exc:  # pragma: no cover - entrada corrompida
        raise OperationError(f"falha ao processar o PDF: {exc}") from exc


def linearize(data: bytes) -> bytes:
    """Regrava o PDF de forma linearizada (otimizado para visualização na web)."""
    try:
        with pikepdf.open(BytesIO(data)) as pdf:
            _stamp_dc_metadata(pdf)
            out = BytesIO()
            pdf.save(out, linearize=True)
            return out.getvalue()
    except pikepdf.PasswordError as exc:
        raise EncryptedPdfError("PDF protegido; remova a senha antes de otimizar") from exc
    except Exception as exc:  # pragma: no cover - entrada corrompida
        raise OperationError(f"falha ao otimizar o PDF: {exc}") from exc


def count_pages(data: bytes, password: str | None = None) -> int:
    """Conta páginas usando o pikepdf (tolerante a alguns PDFs malformados)."""
    try:
        with pikepdf.open(BytesIO(data), password=password or "") as pdf:
            return len(pdf.pages)
    except pikepdf.PasswordError as exc:
        raise EncryptedPdfError("senha ausente ou incorreta") from exc
    except Exception as exc:  # pragma: no cover
        raise OperationError(f"falha ao ler o PDF: {exc}") from exc


def remove_metadata(data: bytes) -> bytes:
    """Remove todos os metadados (/Info e XMP) do documento."""
    try:
        with pikepdf.open(BytesIO(data)) as pdf:
            # docinfo pode não existir (PDF sem /Info) — remove direto do trailer
            if "/Info" in pdf.trailer:
                del pdf.trailer["/Info"]
            if "/Metadata" in pdf.Root:
                del pdf.Root["/Metadata"]
            out = BytesIO()
            # Re-stamp explícito: o helper recria o /Info com a marca davi-code.
            # "remove metadata" = limpar o que o usuário subiu; preserva a
            # nossa identidade no Producer/Creator. Sem isso, o PDF sairia
            # sem /Info e visualizadores + nosso pdf-info mostrariam vazio.
            _stamp_dc_metadata(pdf)
            pdf.save(out)
            return out.getvalue()
    except pikepdf.PasswordError as exc:
        raise EncryptedPdfError("PDF protegido; remova a senha antes de limpar metadados") from exc
    except Exception as exc:
        raise OperationError(f"falha ao remover metadados: {exc}") from exc


def flatten_annotations(data: bytes) -> bytes:
    """Achata anotações interativas preservando o conteúdo visual renderizado."""
    try:
        with pikepdf.open(BytesIO(data)) as pdf:
            pdf.generate_appearance_streams()
            pdf.flatten_annotations("all")
            out = BytesIO()
            _stamp_dc_metadata(pdf)
            pdf.save(out)
            return out.getvalue()
    except Exception as exc:
        raise OperationError(f"falha ao achatar anotações: {exc}") from exc


# Alias mantido para compatibilidade interna.
flatten_form = flatten_annotations


def list_bookmarks(data: bytes) -> list[dict[str, Any]]:
    """Lista os marcadores (outline) do PDF como árvore."""
    def _items(outline_items: list[Any]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for item in outline_items:
            entry: dict[str, Any] = {"title": str(item.title)}
            if item.children:
                entry["children"] = _items(item.children)
            result.append(entry)
        return result

    try:
        with pikepdf.open(BytesIO(data)) as pdf:
            with pdf.open_outline() as outline:
                return _items(outline.root)
    except Exception as exc:
        raise OperationError(f"falha ao ler marcadores: {exc}") from exc


def add_bookmarks(data: bytes, bookmarks: list[dict[str, Any]]) -> bytes:
    """Adiciona marcadores. Cada item deve ter {title, page} (page 0-indexed)."""
    try:
        with pikepdf.open(BytesIO(data)) as pdf:
            with pdf.open_outline() as outline:
                for bm in bookmarks:
                    page_idx = max(0, min(int(bm.get("page", 0)), len(pdf.pages) - 1))
                    outline.root.append(pikepdf.OutlineItem(str(bm["title"]), page_idx))
            out = BytesIO()
            _stamp_dc_metadata(pdf)
            pdf.save(out)
            return out.getvalue()
    except Exception as exc:
        raise OperationError(f"falha ao adicionar marcadores: {exc}") from exc


def get_info(data: bytes) -> dict[str, Any]:
    """Retorna informações estruturais do PDF (versão, páginas, tamanhos, etc.)."""
    try:
        with pikepdf.open(BytesIO(data)) as pdf:
            page_sizes = []
            for page in pdf.pages:
                mb = page.get("/MediaBox")
                if mb:
                    w = round(float(mb[2]) - float(mb[0]), 2)
                    h = round(float(mb[3]) - float(mb[1]), 2)
                    page_sizes.append({"width": w, "height": h})
            issues = [str(s) for s in pdf.check_pdf_syntax()]
            return {
                "pages": len(pdf.pages),
                "pdf_version": str(pdf.pdf_version),
                "is_encrypted": pdf.is_encrypted,
                "is_linearized": pdf.is_linearized,
                "has_forms": "/AcroForm" in pdf.Root,
                "has_xmp": "/Metadata" in pdf.Root,
                "page_sizes": page_sizes,
                "syntax_issues": issues,
            }
    except pikepdf.PasswordError as exc:
        raise EncryptedPdfError("PDF protegido") from exc
    except Exception as exc:
        raise OperationError(f"falha ao inspecionar o PDF: {exc}") from exc


def validate_pdf(data: bytes) -> dict[str, Any]:
    """Verifica a validade estrutural do PDF."""
    try:
        with pikepdf.open(BytesIO(data)) as pdf:
            issues = [str(i) for i in pdf.check_pdf_syntax()]
            return {
                "valid": len(issues) == 0,
                "pages": len(pdf.pages),
                "issues": issues,
                "version": str(pdf.pdf_version),
                "encrypted": pdf.is_encrypted,
            }
    except pikepdf.PasswordError:
        return {"valid": True, "encrypted": True, "pages": None, "issues": [], "version": None}
    except pikepdf.PdfError as exc:
        return {"valid": False, "pages": None, "issues": [str(exc)], "version": None,
                "encrypted": None}
    except Exception as exc:
        return {"valid": False, "pages": None, "issues": [str(exc)], "version": None,
                "encrypted": None}


# Papel em pontos (portrait). Tamanho A4 como default de saída.
_NUP_PAPER: dict[str, tuple[float, float]] = {
    "a3": (841.89, 1190.55),
    "a4": (595.28, 841.89),
    "a5": (419.53, 595.28),
    "letter": (612.0, 792.0),
    "legal": (612.0, 1008.0),
}

# Grades pré-definidas (cols × rows) para valores comuns de N.
_NUP_GRIDS: dict[int, tuple[int, int]] = {
    2: (2, 1),
    4: (2, 2),
    6: (3, 2),
    8: (4, 2),
    9: (3, 3),
    16: (4, 4),
}


def _nup_grid(n: int) -> tuple[int, int]:
    if n in _NUP_GRIDS:
        return _NUP_GRIDS[n]
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    return cols, rows


def nup(
    data: bytes,
    n: int,
    *,
    paper: str = "a4",
    landscape: bool | None = None,
    margin: float = 4.0,
) -> bytes:
    """Coloca N páginas por folha (N-up) preservando vetores e texto.

    ``landscape`` por padrão é True quando cols > rows.
    """
    if n < 2:
        raise OperationError("'n' deve ser >= 2")
    paper_key = paper.lower()
    if paper_key not in _NUP_PAPER:
        raise OperationError(f"papel inválido; opções: {sorted(_NUP_PAPER)}")

    cols, rows = _nup_grid(n)
    pw, ph = _NUP_PAPER[paper_key]
    use_landscape = landscape if landscape is not None else (cols > rows)
    if use_landscape:
        pw, ph = ph, pw

    cell_w = pw / cols
    cell_h = ph / rows

    try:
        with pikepdf.open(BytesIO(data)) as src:
            out = pikepdf.new()
            total = len(src.pages)

            for group_start in range(0, total, n):
                group = list(src.pages[group_start: group_start + n])
                resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary())
                content_parts: list[str] = []

                for i, src_page in enumerate(group):
                    col = i % cols
                    row = rows - 1 - (i // cols)

                    mb = src_page.mediabox
                    src_w = float(mb[2]) - float(mb[0])
                    src_h = float(mb[3]) - float(mb[1])
                    if src_w <= 0 or src_h <= 0:
                        continue

                    usable_w = cell_w - 2 * margin
                    usable_h = cell_h - 2 * margin
                    scale = min(usable_w / src_w, usable_h / src_h)

                    x_off = col * cell_w + margin + (usable_w - src_w * scale) / 2
                    y_off = row * cell_h + margin + (usable_h - src_h * scale) / 2

                    xobj = out.copy_foreign(src_page.as_form_xobject())
                    name = f"P{group_start + i}"
                    resources.XObject[f"/{name}"] = xobj
                    content_parts.append(
                        f"q {scale:.6f} 0 0 {scale:.6f} {x_off:.4f} {y_off:.4f} cm /{name} Do Q"
                    )

                content = "\n".join(content_parts).encode()
                page_obj = out.make_indirect(pikepdf.Dictionary(
                    Type=pikepdf.Name.Page,
                    MediaBox=pikepdf.Array([0, 0, pw, ph]),
                    Resources=resources,
                    Contents=out.make_stream(content),
                ))
                out.pages.append(pikepdf.Page(page_obj))

            result = BytesIO()
            _stamp_dc_metadata(out)
            out.save(result)
            return result.getvalue()
    except pikepdf.PasswordError as exc:
        raise EncryptedPdfError("PDF protegido") from exc
    except OperationError:
        raise
    except Exception as exc:
        raise OperationError(f"falha ao montar N-up: {exc}") from exc
