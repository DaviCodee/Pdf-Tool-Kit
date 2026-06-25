"""Fallback robusto sobre o pikepdf.

Usado quando o pypdf falha ao abrir/regravar documentos problemáticos (ex.: remoção
de senha em PDFs com estruturas que o pypdf não digere bem).
"""

from __future__ import annotations

from io import BytesIO

import pikepdf

from pdftoolkit.core.errors import EncryptedPdfError, OperationError


def remove_password(data: bytes, password: str | None = None) -> bytes:
    """Abre um PDF protegido e o regrava sem criptografia."""
    try:
        with pikepdf.open(BytesIO(data), password=password or "") as pdf:
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
            pdf.docinfo.clear()
            if "/Metadata" in pdf.Root:
                del pdf.Root["/Metadata"]
            out = BytesIO()
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
            pdf.save(out)
            return out.getvalue()
    except Exception as exc:
        raise OperationError(f"falha ao achatar anotações: {exc}") from exc


# Alias mantido para compatibilidade interna.
flatten_form = flatten_annotations


def list_bookmarks(data: bytes) -> list[dict]:
    """Lista os marcadores (outline) do PDF como árvore."""
    def _items(outline_items) -> list[dict]:
        result = []
        for item in outline_items:
            entry: dict = {"title": str(item.title)}
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


def add_bookmarks(data: bytes, bookmarks: list[dict]) -> bytes:
    """Adiciona marcadores. Cada item deve ter {title, page} (page 0-indexed)."""
    try:
        with pikepdf.open(BytesIO(data)) as pdf:
            with pdf.open_outline() as outline:
                for bm in bookmarks:
                    page_idx = max(0, min(int(bm.get("page", 0)), len(pdf.pages) - 1))
                    outline.root.append(pikepdf.OutlineItem(str(bm["title"]), page_idx))
            out = BytesIO()
            pdf.save(out)
            return out.getvalue()
    except Exception as exc:
        raise OperationError(f"falha ao adicionar marcadores: {exc}") from exc


def list_fonts(data: bytes) -> list[dict[str, str]]:
    """Lista as fontes referenciadas no PDF."""
    fonts: list[dict[str, str]] = []
    seen: set[str] = set()
    try:
        with pikepdf.open(BytesIO(data)) as pdf:
            for page in pdf.pages:
                resources = page.get("/Resources")
                if resources is None:
                    continue
                font_dict = resources.get("/Font")
                if font_dict is None:
                    continue
                for key in font_dict.keys():
                    try:
                        font_obj = font_dict[key]
                        name = str(font_obj.get("/BaseFont", pikepdf.Name("/Unknown")))
                        subtype = str(font_obj.get("/Subtype", pikepdf.Name("")))
                        if name not in seen:
                            seen.add(name)
                            fonts.append({"name": name.lstrip("/"), "subtype": subtype.lstrip("/")})
                    except Exception:
                        continue
        return fonts
    except pikepdf.PasswordError as exc:
        raise EncryptedPdfError("PDF protegido") from exc
    except Exception as exc:
        raise OperationError(f"falha ao listar fontes: {exc}") from exc


def get_info(data: bytes) -> dict:
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


def validate_pdf(data: bytes) -> dict:
    """Verifica a validade estrutural do PDF."""
    try:
        with pikepdf.open(BytesIO(data)) as pdf:
            issues = [str(i) for i in pdf.check_pdf_syntax()]
            return {"valid": len(issues) == 0, "pages": len(pdf.pages), "issues": issues}
    except pikepdf.PasswordError:
        return {"valid": True, "encrypted": True, "pages": None, "issues": []}
    except pikepdf.PdfError as exc:
        return {"valid": False, "pages": None, "issues": [str(exc)]}
    except Exception as exc:
        return {"valid": False, "pages": None, "issues": [str(exc)]}
