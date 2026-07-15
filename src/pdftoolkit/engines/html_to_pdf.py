"""HTML -> PDF via WeasyPrint (extra ``html``, BSD).

Requer libs nativas ``libcairo2`` e ``libpango-1.0-0`` instaladas no sistema —
veja ``README.md`` para detalhes de instalação.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from pdftoolkit.core.errors import MissingDependencyError, OperationError


def _weasyprint() -> Any:
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise MissingDependencyError(
            "html-to-pdf requer o extra 'html' "
            "(pip install pdftoolkit[html]) + libs nativas "
            "(apt install libpango-1.0-0 libpangoft2-1.0-0 libcairo2)"
        ) from exc
    return HTML


def html_to_pdf(html: str) -> bytes:
    """Renderiza ``html`` para PDF."""
    HTML = _weasyprint()
    buffer = BytesIO()
    try:
        HTML(string=html, base_url=".").write_pdf(target=buffer)
    except Exception as exc:
        raise OperationError(f"falha ao renderizar HTML: {exc}") from exc
    return buffer.getvalue()
