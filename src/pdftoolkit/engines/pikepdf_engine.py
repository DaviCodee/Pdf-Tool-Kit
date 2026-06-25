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


def flatten_form(data: bytes) -> bytes:
    """Remove widgets de formulário preservando o conteúdo visual já renderizado."""
    try:
        with pikepdf.open(BytesIO(data)) as pdf:
            for page in pdf.pages:
                if "/Annots" in page:
                    page["/Annots"] = pikepdf.Array(
                        a for a in page["/Annots"]
                        if a.get("/Subtype") != pikepdf.Name("/Widget")
                    )
            if "/AcroForm" in pdf.Root:
                del pdf.Root["/AcroForm"]
            out = BytesIO()
            pdf.save(out)
            return out.getvalue()
    except Exception as exc:
        raise OperationError(f"falha ao achatar formulário: {exc}") from exc
