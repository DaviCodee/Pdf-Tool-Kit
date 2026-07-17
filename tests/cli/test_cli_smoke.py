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


def _make_pdf_folder(tmp_path, make_pdf):
    folder = tmp_path / "pasta"
    (folder / "sub").mkdir(parents=True)
    (folder / "a.pdf").write_bytes(make_pdf(2, "A"))
    (folder / "sub" / "b.pdf").write_bytes(make_pdf(1, "B"))
    (folder / "ignorar.txt").write_bytes(b"nao e pdf")
    hidden = folder / ".oculto"
    hidden.mkdir()
    (hidden / "c.pdf").write_bytes(make_pdf(1, "C"))
    return folder


def test_folder_input_expands_recursively(tmp_path, make_pdf):
    folder = _make_pdf_folder(tmp_path, make_pdf)
    out = tmp_path / "saida"
    result = runner.invoke(app, ["rotate", str(folder), "--degrees", "90", "-o", str(out)])
    assert result.exit_code == 0, result.output
    produced = list(out.rglob("*.pdf"))
    assert len(produced) == 2  # a.pdf + sub/b.pdf; ignorar.txt e .oculto/c.pdf ficam de fora
    assert (out / "rotacionado.pdf").exists()
    assert (out / "sub" / "rotacionado.pdf").exists()


def test_folder_without_pdfs_errors(tmp_path):
    folder = tmp_path / "vazia"
    folder.mkdir()
    result = runner.invoke(app, ["rotate", str(folder), "--degrees", "90"])
    assert result.exit_code != 0
    assert "nenhum arquivo compatível" in result.output


def test_ext_unlocks_non_pdf_folder(tmp_path):
    from PIL import Image

    folder = tmp_path / "fotos"
    folder.mkdir()
    Image.new("RGB", (30, 30), (200, 0, 0)).save(folder / "a.png")
    Image.new("RGB", (30, 30), (0, 200, 0)).save(folder / "b.png")
    out = tmp_path / "saida"
    result = runner.invoke(
        app, ["images-to-pdf", str(folder), "--ext", ".png", "-o", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert len(list(out.glob("*.pdf"))) == 1


def test_multi_file_fan_out_via_cli(tmp_path, make_pdf):
    a = tmp_path / "a.pdf"
    b = tmp_path / "b.pdf"
    a.write_bytes(make_pdf(2, "A"))
    b.write_bytes(make_pdf(1, "B"))
    out = tmp_path / "saida"
    result = runner.invoke(app, ["rotate", str(a), str(b), "--degrees", "90", "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert len(list(out.glob("*.pdf"))) == 2
