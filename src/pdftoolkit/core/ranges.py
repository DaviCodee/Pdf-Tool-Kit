"""Parser autoral de intervalos de páginas.

Aceita uma especificação textual, 1-based e inclusiva, e devolve índices 0-based.

Formas aceitas por token (separados por vírgula):
    ``N``     -> página única N
    ``N-M``   -> de N até M (inclusive); se M < N o intervalo é invertido
    ``N-``    -> de N até a última página
    ``-M``    -> da primeira página até M

A ordem de aparição é preservada (importante para extração/reordenação). Use
``unique=True`` para remover duplicatas mantendo a primeira ocorrência.
"""

from __future__ import annotations

from pdftoolkit.core.errors import PageRangeError


def parse_page_ranges(spec: str, total: int, *, unique: bool = False) -> list[int]:
    """Converte ``spec`` em uma lista de índices 0-based dentro de ``[0, total)``.

    Levanta :class:`PageRangeError` para sintaxe inválida ou páginas fora do limite.
    """
    if total <= 0:
        raise PageRangeError("documento sem páginas")

    text = spec.strip()
    if not text:
        raise PageRangeError("intervalo de páginas vazio")

    result: list[int] = []
    for raw_token in text.split(","):
        token = raw_token.strip()
        if not token:
            raise PageRangeError(f"token vazio em {spec!r}")
        result.extend(_expand_token(token, total, spec))

    if unique:
        seen: set[int] = set()
        deduped: list[int] = []
        for index in result:
            if index not in seen:
                seen.add(index)
                deduped.append(index)
        return deduped
    return result


def _expand_token(token: str, total: int, spec: str) -> list[int]:
    if "-" in token:
        start_text, _, end_text = token.partition("-")
        start = _parse_bound(start_text, total, spec, default=1)
        end = _parse_bound(end_text, total, spec, default=total)
        step = 1 if end >= start else -1
        return [page - 1 for page in range(start, end + step, step)]

    page = _parse_bound(token, total, spec, default=None)
    return [page - 1]


def _parse_bound(text: str, total: int, spec: str, *, default: int | None) -> int:
    text = text.strip()
    if not text:
        if default is None:
            raise PageRangeError(f"número de página ausente em {spec!r}")
        return default
    if not text.isdigit():
        raise PageRangeError(f"número de página inválido {text!r} em {spec!r}")
    page = int(text)
    if page < 1 or page > total:
        raise PageRangeError(
            f"página {page} fora do intervalo 1..{total} em {spec!r}"
        )
    return page
