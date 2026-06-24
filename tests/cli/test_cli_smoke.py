"""Smoke do adaptador de CLI (subcomandos por operação)."""

from __future__ import annotations

from io import BytesIO

from click.testing import CliRunner
from reportlab.pdfgen.canvas import Canvas

from pdftoolkit.cli.main import app
from pdftoolkit.engines import pypdf_engine as pe

runner = CliRunner()


def test_list_shows_operations():
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "merge" in result.output


def test_schema_outputs_json():
    result = runner.invoke(app, ["schema", "split"])
    assert result.exit_code == 0
    assert '"every"' in result.output


def test_operation_is_a_subcommand(tmp_path, make_pdf):
    a = tmp_path / "a.pdf"
    b = tmp_path / "b.pdf"
    a.write_bytes(make_pdf(2, "A"))
    b.write_bytes(make_pdf(3, "B"))
    out = tmp_path / "saida"
    result = runner.invoke(app, ["merge", str(a), str(b), "-o", str(out)])
    assert result.exit_code == 0, result.output
    produced = list(out.glob("*.pdf"))
    assert len(produced) == 1
    assert pe.count_pages(produced[0].read_bytes()) == 5


def test_subcommand_with_typed_flag(tmp_path, make_pdf):
    src = tmp_path / "x.pdf"
    src.write_bytes(make_pdf(5))
    out = tmp_path / "out"
    result = runner.invoke(app, ["split", str(src), "--every", "2", "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert len(list(out.glob("*.pdf"))) == 3


def test_list_field_repeated_flag(tmp_path, make_pdf):
    src = tmp_path / "x.pdf"
    src.write_bytes(make_pdf(5))
    out = tmp_path / "out"
    result = runner.invoke(
        app, ["split", str(src), "--ranges", "1-2", "--ranges", "3-5", "-o", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert len(list(out.glob("*.pdf"))) == 2


def test_choice_flag_validates(tmp_path, make_pdf):
    src = tmp_path / "x.pdf"
    src.write_bytes(make_pdf(2))
    result = runner.invoke(app, ["compress", str(src), "--quality", "invalida"])
    assert result.exit_code != 0


def test_metadata_read_prints_json(tmp_path, make_pdf):
    src = tmp_path / "x.pdf"
    src.write_bytes(make_pdf(3))
    result = runner.invoke(app, ["metadata-read", str(src)])
    assert result.exit_code == 0
    assert "/Pages" in result.output


def test_help_lists_operation_subcommands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "compress" in result.output and "watermark" in result.output


def test_unknown_command_fails():
    result = runner.invoke(app, ["inexistente"])
    assert result.exit_code != 0


def test_dict_field_key_value(tmp_path):
    buffer = BytesIO()
    canvas = Canvas(buffer)
    canvas.acroForm.textfield(name="nome", x=120, y=715, width=200, height=18, borderWidth=1)
    canvas.showPage()
    canvas.save()
    src = tmp_path / "form.pdf"
    src.write_bytes(buffer.getvalue())
    out = tmp_path / "out"
    result = runner.invoke(
        app, ["form-fill", str(src), "--values", "nome=Davi", "-o", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert len(list(out.glob("*.pdf"))) == 1
