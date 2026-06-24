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


def count_pages(data: bytes, password: str | None = None) -> int:
    """Conta páginas usando o pikepdf (tolerante a alguns PDFs malformados)."""
    try:
        with pikepdf.open(BytesIO(data), password=password or "") as pdf:
            return len(pdf.pages)
    except pikepdf.PasswordError as exc:
        raise EncryptedPdfError("senha ausente ou incorreta") from exc
    except Exception as exc:  # pragma: no cover
        raise OperationError(f"falha ao ler o PDF: {exc}") from exc
