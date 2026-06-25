"""Operação: dividir um PDF em vários arquivos."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import model_validator

from pdftoolkit.core.errors import InvalidInputError
from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.ranges import parse_page_ranges
from pdftoolkit.core.registry import register
from pdftoolkit.core.validation import ensure_pdf, safe_filename
from pdftoolkit.engines import pypdf_engine as pe


class SplitParams(OperationParams):
    every: int | None = None
    ranges: list[str] | None = None
    output_stem: str = "parte"

    @model_validator(mode="after")
    def _exclusive(self) -> SplitParams:
        if self.every is not None and self.ranges is not None:
            raise ValueError("use 'every' OU 'ranges', não ambos")
        if self.every is not None and self.every < 1:
            raise ValueError("'every' deve ser >= 1")
        return self


@register
class SplitOperation(PdfOperation[SplitParams]):
    name = "split"
    category = "organizar"
    summary = "Divide um PDF por blocos de N páginas ou por intervalos explícitos."
    params_model = SplitParams
    min_inputs = 1
    max_inputs = 1

    def run(self, inputs: Sequence[PdfInput], params: SplitParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        reader = pe.open_reader(item.data)
        total = len(reader.pages)

        groups = self._groups(params, total)
        stem = safe_filename(params.output_stem, fallback="parte").removesuffix(".pdf")

        artifacts: list[Artifact] = []
        for position, indices in enumerate(groups, start=1):
            writer = pe.new_writer()
            pe.add_pages(writer, reader, indices)
            data = pe.write_bytes(writer)
            artifacts.append(
                Artifact(data=data, filename=f"{stem}-{position:03d}.pdf")
            )
        return OperationResult(artifacts=artifacts, meta={"files": len(artifacts)})

    @staticmethod
    def _groups(params: SplitParams, total: int) -> list[list[int]]:
        if params.ranges is not None:
            groups = [parse_page_ranges(spec, total) for spec in params.ranges]
            if not groups:
                raise InvalidInputError("nenhum intervalo informado")
            return groups
        step = params.every or 1
        return [list(range(start, min(start + step, total))) for start in range(0, total, step)]


class SplitBySizeParams(OperationParams):
    max_mb: float = 5.0
    output_stem: str = "parte"

    @classmethod
    def __get_validators__(cls):  # noqa: D105 - pydantic v2 compat
        yield cls._validate

    @classmethod
    def _validate(cls, v):
        return v

    def model_post_init(self, __context) -> None:
        if self.max_mb <= 0:
            raise ValueError("'max_mb' deve ser maior que zero")


@register
class SplitBySizeOperation(PdfOperation[SplitBySizeParams]):
    name = "split-by-size"
    category = "organizar"
    summary = "Divide um PDF em partes cujo tamanho não ultrapasse o limite em MB."
    params_model = SplitBySizeParams
    min_inputs = 1
    max_inputs = 1

    def run(self, inputs: Sequence[PdfInput], params: SplitBySizeParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        reader = pe.open_reader(item.data)
        total = len(reader.pages)
        max_bytes = int(params.max_mb * 1024 * 1024)
        stem = safe_filename(params.output_stem, fallback="parte").removesuffix(".pdf")

        artifacts: list[Artifact] = []
        chunk_indices: list[int] = []

        for i in range(total):
            chunk_indices.append(i)
            writer = pe.new_writer()
            pe.add_pages(writer, reader, chunk_indices)
            candidate = pe.write_bytes(writer)
            if len(candidate) > max_bytes and len(chunk_indices) > 1:
                # flush sem a última página e reabra com ela
                chunk_indices.pop()
                writer = pe.new_writer()
                pe.add_pages(writer, reader, chunk_indices)
                data = pe.write_bytes(writer)
                artifacts.append(
                    Artifact(data=data, filename=f"{stem}-{len(artifacts) + 1:03d}.pdf")
                )
                chunk_indices = [i]

        if chunk_indices:
            writer = pe.new_writer()
            pe.add_pages(writer, reader, chunk_indices)
            data = pe.write_bytes(writer)
            artifacts.append(
                Artifact(data=data, filename=f"{stem}-{len(artifacts) + 1:03d}.pdf")
            )

        return OperationResult(artifacts=artifacts, meta={"files": len(artifacts)})
