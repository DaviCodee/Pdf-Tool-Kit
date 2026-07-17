"""Fan-out automático: operações 1/1 processando N entradas de uma vez."""

from __future__ import annotations

import pytest

from pdftoolkit.core.errors import PdfToolkitError
from pdftoolkit.core.io import PdfInput
from pdftoolkit.core.registry import get_operation


def test_fan_out_one_artifact_per_input(pdf5, pdf3):
    op = get_operation("rotate")
    inputs = [
        PdfInput(pdf5, "a.pdf"),
        PdfInput(pdf3, "b.pdf"),
    ]
    result = op.execute(inputs, op.params_model(degrees=90))
    assert len(result.artifacts) == 2
    # output_name é fixo ("rotacionado.pdf") — a dedup entra em ação.
    assert [a.filename for a in result.artifacts] == [
        "rotacionado.pdf", "rotacionado-2.pdf",
    ]
    assert result.meta["fan_out"] is True
    assert result.meta["inputs"] == 2
    assert [entry["name"] for entry in result.meta["per_input"]] == ["a.pdf", "b.pdf"]


def test_fan_out_fails_fast_with_input_name(pdf5):
    op = get_operation("rotate")
    inputs = [
        PdfInput(pdf5, "bom.pdf"),
        PdfInput(b"nao-e-pdf", "ruim.pdf"),
        PdfInput(pdf5, "nunca.pdf"),
    ]
    with pytest.raises(PdfToolkitError) as excinfo:
        op.execute(inputs, op.params_model(degrees=90))
    assert str(excinfo.value).startswith("ruim.pdf: ")


def test_single_input_path_unchanged(pdf5):
    op = get_operation("rotate")
    result = op.execute([PdfInput(pdf5, "a.pdf")], op.params_model(degrees=90))
    assert len(result.artifacts) == 1
    assert "fan_out" not in result.meta


def test_merge_unbounded_op_not_fanned_out(pdf5, pdf3):
    op = get_operation("merge")
    inputs = [PdfInput(pdf5, "a.pdf"), PdfInput(pdf3, "b.pdf"), PdfInput(pdf5, "c.pdf")]
    result = op.execute(inputs, op.params_model())
    # merge agrega tudo num único artefato — o fan-out não pode ter disparado.
    assert len(result.artifacts) == 1
    assert "fan_out" not in result.meta


def test_stamp_fixed_arity_not_fanned_out(pdf5):
    op = get_operation("stamp")
    with pytest.raises(PdfToolkitError):
        # stamp é 2/2 (base + carimbo); 3 entradas violam a aridade em vez de
        # disparar fan-out.
        op.execute(
            [PdfInput(pdf5, "a.pdf"), PdfInput(pdf5, "b.pdf"), PdfInput(pdf5, "c.pdf")],
            op.params_model(),
        )


def test_watermark_single_op_fans_out(pdf5, pdf3):
    # watermark é 1/1 (o texto vem em params, não num 2º arquivo) — participa
    # normalmente do fan-out.
    op = get_operation("watermark")
    result = op.execute(
        [PdfInput(pdf5, "a.pdf"), PdfInput(pdf3, "b.pdf")],
        op.params_model(text="confidencial"),
    )
    assert len(result.artifacts) == 2
    assert result.meta["fan_out"] is True
