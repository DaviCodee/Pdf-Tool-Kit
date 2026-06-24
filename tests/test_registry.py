"""Garante a consistência do concentrador: registro, schemas e adaptadores."""

from __future__ import annotations

from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.registry import all_operations

EXPECTED = {
    "merge",
    "split",
    "remove-pages",
    "extract-pages",
    "reorder-pages",
    "rotate",
    "crop",
    "protect",
    "unlock",
    "metadata-read",
    "metadata-edit",
    "page-numbers",
    "watermark",
    "pdf-to-image",
    "thumbnail",
    "images-to-pdf",
    "compress",
    "optimize-web",
    "ocr",
    "extract-tables",
}


def test_all_tier1_operations_registered():
    names = {op.name for op in all_operations()}
    assert EXPECTED <= names


def test_each_operation_is_well_formed():
    for op in all_operations():
        assert isinstance(op, PdfOperation)
        assert issubclass(op.params_model, OperationParams)
        assert op.category and op.summary
        # O schema JSON deve ser gerável (alimenta CLI, API e GUI).
        assert op.params_model.model_json_schema()["type"] == "object"
