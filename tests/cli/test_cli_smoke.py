"""Smoke do adaptador de CLI (subcomandos por operação)."""

from __future__ import annotations

from click.testing import CliRunner
from PIL import Image

from pngtoolkit.cli.main import app

runner = CliRunner()


def _size(path) -> tuple[int, int]:
    return Image.open(path).size


def test_list_shows_operations():
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "resize" in result.output and "favicon" in result.output


def test_schema_outputs_json():
    result = runner.invoke(app, ["schema", "resize"])
    assert result.exit_code == 0
    assert '"width"' in result.output


def test_resize_subcommand(tmp_path, make_image):
    src = tmp_path / "foto.png"
    src.write_bytes(make_image(80, 60))
    out = tmp_path / "saida"
    result = runner.invoke(app, ["resize", str(src), "--width", "40", "-o", str(out)])
    assert result.exit_code == 0, result.output
    produced = list(out.glob("*.png"))
    assert len(produced) == 1
    assert _size(produced[0]) == (40, 30)


def test_convert_choice_flag(tmp_path, make_image):
    src = tmp_path / "foto.png"
    src.write_bytes(make_image())
    out = tmp_path / "out"
    result = runner.invoke(app, ["convert", str(src), "--format", "webp", "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert len(list(out.glob("*.webp"))) == 1


def test_invalid_choice_fails(tmp_path, make_image):
    src = tmp_path / "foto.png"
    src.write_bytes(make_image())
    result = runner.invoke(app, ["convert", str(src), "--format", "tga"])
    assert result.exit_code != 0


def test_favicon_emits_multiple_files(tmp_path, make_image):
    src = tmp_path / "logo.png"
    src.write_bytes(make_image(256, 256))
    out = tmp_path / "out"
    result = runner.invoke(app, ["favicon", str(src), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert (out / "favicon.ico").exists()
    assert (out / "favicon-16x16.png").exists()


def test_exif_read_prints_json(tmp_path, jpg_with_exif):
    src = tmp_path / "foto.jpg"
    src.write_bytes(jpg_with_exif)
    result = runner.invoke(app, ["exif-read", str(src)])
    assert result.exit_code == 0
    assert "Make" in result.output


def test_help_lists_operation_subcommands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "convert" in result.output and "watermark" in result.output


def test_unknown_command_fails():
    result = runner.invoke(app, ["inexistente"])
    assert result.exit_code != 0
