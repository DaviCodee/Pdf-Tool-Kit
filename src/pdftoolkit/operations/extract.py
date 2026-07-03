"""Operações de extração de conteúdo: texto e imagens embutidas."""

from __future__ import annotations

from collections.abc import Sequence

from pdftoolkit.core.errors import InvalidInputError, MissingDependencyError
from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.registry import register
from pdftoolkit.core.validation import ensure_pdf, safe_filename
from pdftoolkit.engines import pypdf_engine as pe


class ExtractTextParams(OperationParams):
    pages: str | None = None
    output_name: str = "texto.txt"


@register
class ExtractTextOperation(PdfOperation[ExtractTextParams]):
    name = "extract-text"
    category = "converter"
    summary = "Extrai o texto de todas (ou de algumas) páginas do PDF."
    params_model = ExtractTextParams

    def run(self, inputs: Sequence[PdfInput], params: ExtractTextParams) -> OperationResult:
        from pdftoolkit.core.ranges import parse_page_ranges

        item = inputs[0]
        ensure_pdf(item.data, item.name)
        texts = pe.extract_page_texts(item.data)
        if params.pages:
            chosen = parse_page_ranges(params.pages, len(texts), unique=True)
            texts = [texts[i] for i in chosen]
        joined = "\n\n".join(texts).strip()
        artifact = Artifact(
            data=joined.encode("utf-8"),
            filename=safe_filename(params.output_name, fallback="texto.txt"),
            media_type="text/plain",
        )
        return OperationResult(
            artifacts=[artifact],
            meta={"pages": len(texts), "characters": len(joined)},
        )


class ExtractImagesParams(OperationParams):
    pass


@register
class ExtractImagesOperation(PdfOperation[ExtractImagesParams]):
    name = "extract-images"
    category = "converter"
    summary = "Extrai as imagens embutidas no PDF (extra 'render')."
    params_model = ExtractImagesParams

    def run(self, inputs: Sequence[PdfInput], params: ExtractImagesParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        try:
            import fitz  # PyMuPDF
        except ImportError as exc:
            raise MissingDependencyError(
                "extração de imagens requer o extra 'render' (pip install pdftoolkit[render])"
            ) from exc

        document = fitz.open(stream=item.data, filetype="pdf")
        artifacts: list[Artifact] = []
        seen: set[int] = set()
        try:
            for page in document:
                for info in page.get_images(full=True):
                    xref = info[0]
                    if xref in seen:
                        continue
                    seen.add(xref)
                    extracted = document.extract_image(xref)
                    ext = extracted.get("ext", "png")
                    artifacts.append(
                        Artifact(
                            data=extracted["image"],
                            filename=f"imagem-{len(artifacts) + 1}.{ext}",
                            media_type=f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}",
                        )
                    )
        finally:
            document.close()
        if not artifacts:
            raise InvalidInputError("nenhuma imagem embutida encontrada nesse pdf")
        return OperationResult(artifacts=artifacts, meta={"images": len(artifacts)})


class AnnotateParams(OperationParams):
    text: str
    page: int = 1
    x: float = 50.0
    y: float = 50.0
    output_name: str = "anotado.pdf"


@register
class AnnotateOperation(PdfOperation[AnnotateParams]):
    name = "annotate"
    category = "editar"
    summary = "Adiciona uma anotação (nota/comentário) em uma posição da página."
    params_model = AnnotateParams

    def run(self, inputs: Sequence[PdfInput], params: AnnotateParams) -> OperationResult:
        from pypdf.annotations import Text

        item = inputs[0]
        ensure_pdf(item.data, item.name)
        reader = pe.open_reader(item.data)
        writer = pe.clone_writer(reader)
        index = max(0, min(len(writer.pages) - 1, params.page - 1))
        annotation = Text(
            text=params.text,
            rect=(params.x, params.y, params.x + 20, params.y + 20),
            open=False,
        )
        writer.add_annotation(page_number=index, annotation=annotation)
        data = pe.write_bytes(writer)
        artifact = Artifact(
            data=data, filename=safe_filename(params.output_name, fallback="anotado.pdf")
        )
        return OperationResult(artifacts=[artifact], meta={"page": index + 1})
