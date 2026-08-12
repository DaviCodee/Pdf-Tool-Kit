"""Primitivas estruturais sobre o pypdf.

Motor primário das operações Tier 1. Trabalha inteiramente em memória.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from io import BytesIO

from pypdf import PdfReader, PdfWriter
from pypdf.constants import UserAccessPermissions
from pypdf.generic import RectangleObject

from pdftoolkit.core.errors import EncryptedPdfError, OperationError

# Caixa de corte: (esquerda, base, direita, topo) em pontos PDF.
CropBox = tuple[float, float, float, float]


def open_reader(data: bytes, password: str | None = None) -> PdfReader:
    """Abre um PDF a partir de bytes, decifrando se necessário."""
    try:
        reader = PdfReader(BytesIO(data))
    except Exception as exc:  # pragma: no cover - depende de entrada corrompida
        raise OperationError(f"não foi possível ler o PDF: {exc}") from exc
    if reader.is_encrypted:
        if not reader.decrypt(password or ""):
            raise EncryptedPdfError("PDF protegido: senha ausente ou incorreta")
    return reader


def count_pages(data: bytes, password: str | None = None) -> int:
    """Conta as páginas de um PDF."""
    return len(open_reader(data, password).pages)


def write_bytes(writer: PdfWriter) -> bytes:
    """Serializa um writer para bytes."""
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def new_writer() -> PdfWriter:
    """Cria um writer vazio."""
    return PdfWriter()


def clone_writer(reader: PdfReader) -> PdfWriter:
    """Cria um writer com uma cópia completa do documento (páginas + metadados)."""
    return PdfWriter(clone_from=reader)


def add_pages(
    writer: PdfWriter,
    reader: PdfReader,
    indices: Sequence[int] | None = None,
) -> None:
    """Acrescenta páginas de ``reader`` ao ``writer``.

    Sem ``indices`` copia todas as páginas; com ``indices`` copia exatamente aquelas,
    na ordem dada (permitindo seleção e reordenação).
    """
    pages = reader.pages
    chosen = range(len(pages)) if indices is None else indices
    for index in chosen:
        writer.add_page(pages[index])


def rotate_pages(writer: PdfWriter, indices: Iterable[int] | None, degrees: int) -> None:
    """Gira páginas no sentido horário por um múltiplo de 90 graus."""
    pages = writer.pages
    targets = range(len(pages)) if indices is None else list(indices)
    for index in targets:
        pages[index].rotate(degrees)


def set_crop(writer: PdfWriter, indices: Iterable[int] | None, box: CropBox) -> None:
    """Define a caixa de corte das páginas alvo."""
    pages = writer.pages
    targets = range(len(pages)) if indices is None else list(indices)
    for index in targets:
        pages[index].cropbox = RectangleObject(box)


def encrypt(
    writer: PdfWriter,
    user_password: str,
    owner_password: str | None = None,
    *,
    allow_printing: bool = True,
    allow_copy: bool = True,
    allow_modify: bool = False,
    allow_annotate: bool = False,
) -> None:
    """Aplica criptografia AES-256 com permissões granulares."""
    perms = UserAccessPermissions(0)
    if allow_printing:
        perms |= UserAccessPermissions.PRINT | UserAccessPermissions.PRINT_TO_REPRESENTATION
    if allow_copy:
        perms |= (
            UserAccessPermissions.EXTRACT
            | UserAccessPermissions.EXTRACT_TEXT_AND_GRAPHICS
        )
    if allow_modify:
        perms |= UserAccessPermissions.MODIFY | UserAccessPermissions.ASSEMBLE_DOC
    if allow_annotate:
        perms |= UserAccessPermissions.ADD_OR_MODIFY | UserAccessPermissions.FILL_FORM_FIELDS
    writer.encrypt(
        user_password=user_password,
        owner_password=owner_password or None,
        algorithm="AES-256",
        permissions_flag=perms,
    )


def encrypt_advanced(
    writer: PdfWriter,
    user_password: str,
    owner_password: str | None = None,
    *,
    allow_printing: bool = True,
    allow_print_high_quality: bool = True,
    allow_copy: bool = True,
    allow_extract_accessibility: bool = True,
    allow_modify: bool = False,
    allow_annotate: bool = False,
    allow_fill_forms: bool = True,
    allow_assemble: bool = False,
) -> None:
    """Criptografia AES-256 com controle individual de cada permissão PDF."""
    perms = UserAccessPermissions(0)
    if allow_printing:
        perms |= UserAccessPermissions.PRINT
    if allow_print_high_quality:
        perms |= UserAccessPermissions.PRINT_TO_REPRESENTATION
    if allow_copy:
        perms |= UserAccessPermissions.EXTRACT
    if allow_extract_accessibility:
        perms |= UserAccessPermissions.EXTRACT_TEXT_AND_GRAPHICS
    if allow_modify:
        perms |= UserAccessPermissions.MODIFY
    if allow_annotate:
        perms |= UserAccessPermissions.ADD_OR_MODIFY
    if allow_fill_forms:
        perms |= UserAccessPermissions.FILL_FORM_FIELDS
    if allow_assemble:
        perms |= UserAccessPermissions.ASSEMBLE_DOC
    writer.encrypt(
        user_password=user_password,
        owner_password=owner_password or None,
        algorithm="AES-256",
        permissions_flag=perms,
    )


def read_metadata(reader: PdfReader) -> dict[str, str]:
    """Lê o dicionário de informações do documento como ``{chave: valor}``."""
    meta = reader.metadata
    if meta is None:
        return {}
    return {str(key): str(value) for key, value in meta.items()}


def set_metadata(writer: PdfWriter, mapping: dict[str, str]) -> None:
    """Aplica/atualiza entradas de metadados (chaves no formato ``/Title``)."""
    writer.add_metadata(mapping)


def merge_overlay(
    writer: PdfWriter,
    indices: Iterable[int] | None,
    overlay_pdf: bytes,
    *,
    over: bool = True,
) -> None:
    """Compõe ``overlay_pdf`` sobre (ou sob) as páginas alvo.

    As páginas do overlay avançam junto com as páginas alvo; quando o overlay
    tem menos páginas, a última é repetida (overlay de 1 página vale para o
    documento inteiro).
    """
    overlay_reader = open_reader(overlay_pdf)
    overlay_pages = overlay_reader.pages
    last = len(overlay_pages) - 1
    pages = writer.pages
    targets = range(len(pages)) if indices is None else list(indices)
    for pos, index in enumerate(targets):
        pages[index].merge_page(overlay_pages[min(pos, last)], over=over)


def page_size(reader: PdfReader, index: int) -> tuple[float, float]:
    """Largura e altura (em pontos) de uma página, a partir da mediabox."""
    box = reader.pages[index].mediabox
    return float(box.width), float(box.height)


def extract_page_texts(data: bytes, password: str | None = None) -> list[str]:
    """Extrai o texto de cada página (string vazia quando não há texto)."""
    reader = open_reader(data, password)
    return [page.extract_text() or "" for page in reader.pages]


def _field_type_name(field: object) -> str:
    """Mapeia /FT para nome human-readable que o front sabe renderizar.

    /FT: Tx=text, Btn=button (checkbox ou radio), Ch=choice, Sig=signature.
    Para Btn, /Ff bit 32768 (Rb) = radio; sem o bit = checkbox.
    """
    if not hasattr(field, "get"):
        return "unknown"
    ft = field.get("/FT")
    if ft is None:
        return "unknown"
    name = str(ft).lstrip("/")
    if name == "Btn":
        try:
            ff = int(field.get("/Ff") or 0)
        except (TypeError, ValueError):
            ff = 0
        return "radio" if (ff & 32768) else "checkbox"
    if name == "Tx":
        return "text"
    if name == "Ch":
        return "choice"
    if name == "Sig":
        return "signature"
    return name.lower() or "unknown"


def _field_is_required(field: object) -> bool:
    """Bit 2 (valor 2) de /Ff = required."""
    if not hasattr(field, "get"):
        return False
    try:
        ff = int(field.get("/Ff") or 0)
    except (TypeError, ValueError):
        return False
    return bool(ff & 2)


def _field_value(field: object, type_name: str) -> object:
    """Extrai `/V` no tipo certo (bool pra checkbox, list pra choice, str resto)."""
    if not hasattr(field, "get"):
        return None
    raw = field.get("/V")
    if raw is None:
        return "" if type_name in ("text", "choice") else False
    if type_name == "checkbox":
        return bool(raw)
    if type_name == "choice":
        if isinstance(raw, list):
            return ", ".join(str(v) for v in raw)
        return str(raw)
    return str(raw)


def _field_options(field: object) -> list[str] | None:
    """Lê /Opt (choice/radio) ou deriva do estado dos kids (radio)."""
    if not hasattr(field, "get"):
        return None
    opt = field.get("/Opt")
    if opt is None:
        return None
    if isinstance(opt, list):
        return [str(o) for o in opt]
    return [str(opt)]


def _field_rect(field: object) -> list[float] | None:
    """Lê /Rect (posicionamento do widget) — o pypdf às vezes põe no indirect_reference.

    Páginas com widget + field mesclados expõem /Rect via `indirect_reference`;
    outros casos via `field.get("/Rect")` ou via kids. Tenta todos.
    """
    rect = None
    if hasattr(field, "get") and field.get("/Rect") is not None:
        rect = field.get("/Rect")
    if rect is None and hasattr(field, "indirect_reference"):
        try:
            rect = field.indirect_reference.get("/Rect")
        except Exception:
            rect = None
    if rect is None and hasattr(field, "get") and field.get("/Kids"):
        for kid in field.get("/Kids"):
            try:
                kid_rect = kid.get_object().get("/Rect") if hasattr(kid, "get_object") else kid.get("/Rect")
            except Exception:
                kid_rect = None
            if kid_rect is not None:
                rect = kid_rect
                break
    if rect is None:
        return None
    try:
        return [float(v) for v in rect]
    except (TypeError, ValueError):
        return None


def read_form_fields(data: bytes, password: str | None = None) -> list[dict[str, object]]:
    """Lê os campos do PDF AcroForm com metadados ricos por campo.

    Shape do retorno: ``[{"name", "type", "value", "options", "required", "rect"}]``.

    Tipos: ``text``, ``checkbox``, ``radio``, ``choice``, ``signature``, ``unknown``.
    """
    reader = open_reader(data, password)
    fields = reader.get_fields()
    if not fields:
        return []
    result: list[dict[str, object]] = []
    for name, field in fields.items():
        try:
            type_name = _field_type_name(field)
            entry: dict[str, object] = {
                "name": str(name),
                "type": type_name,
                "value": _field_value(field, type_name),
                "options": _field_options(field),
                "required": _field_is_required(field),
                "rect": _field_rect(field),
            }
            result.append(entry)
        except Exception:
            # Não bloquear a leitura inteira se um campo estiver corrompido.
            continue
    return result


def fill_form(data: bytes, values: dict[str, str], *, password: str | None = None) -> bytes:
    """Preenche campos de formulário e devolve o PDF resultante."""
    reader = open_reader(data, password)
    writer = clone_writer(reader)
    writer.set_need_appearances_writer(True)
    for page in writer.pages:
        try:
            writer.update_page_form_field_values(page, values, auto_regenerate=False)
        except Exception:  # noqa: S112 - páginas sem widgets são ignoradas
            continue
    return write_bytes(writer)


def insert_pages_at(base_data: bytes, insert_data: bytes, position: int) -> bytes:
    """Insere todas as páginas de insert_data em base_data na posição indicada (0-indexed)."""
    base_reader = open_reader(base_data)
    insert_reader = open_reader(insert_data)
    total = len(base_reader.pages)
    pos = max(0, min(position, total))
    writer = PdfWriter()
    for page in list(base_reader.pages)[:pos]:
        writer.add_page(page)
    for page in insert_reader.pages:
        writer.add_page(page)
    for page in list(base_reader.pages)[pos:]:
        writer.add_page(page)
    return write_bytes(writer)


def add_blank_page_at(
    data: bytes,
    position: int,
    *,
    width: float | None = None,
    height: float | None = None,
) -> bytes:
    """Insere uma página em branco na posição indicada (0-indexed).

    O tamanho é herdado da página adjacente quando não informado.
    """
    reader = open_reader(data)
    total = len(reader.pages)
    pos = max(0, min(position, total))
    if width is None or height is None:
        ref_idx = min(pos, total - 1)
        box = reader.pages[ref_idx].mediabox
        width = float(box.width)
        height = float(box.height)
    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        if i == pos:
            writer.add_blank_page(width=width, height=height)
        writer.add_page(page)
    if pos >= total:
        writer.add_blank_page(width=width, height=height)
    return write_bytes(writer)


def resize_pages(
    data: bytes,
    width: float,
    height: float,
    indices: list[int] | None = None,
) -> bytes:
    """Altera a mediabox das páginas indicadas para (width x height) em pontos."""
    reader = open_reader(data)
    writer = clone_writer(reader)
    targets = set(range(len(writer.pages))) if indices is None else set(indices)
    for i, page in enumerate(writer.pages):
        if i in targets:
            page.mediabox.upper_right = (width, height)
            page.mediabox.lower_left = (0, 0)
    return write_bytes(writer)
