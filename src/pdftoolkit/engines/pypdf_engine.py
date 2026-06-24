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
    """Compõe a primeira página de ``overlay_pdf`` sobre (ou sob) as páginas alvo."""
    overlay_reader = open_reader(overlay_pdf)
    overlay_page = overlay_reader.pages[0]
    pages = writer.pages
    targets = range(len(pages)) if indices is None else list(indices)
    for index in targets:
        pages[index].merge_page(overlay_page, over=over)


def page_size(reader: PdfReader, index: int) -> tuple[float, float]:
    """Largura e altura (em pontos) de uma página, a partir da mediabox."""
    box = reader.pages[index].mediabox
    return float(box.width), float(box.height)
