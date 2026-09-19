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
    result = runner.invoke(app, ["convert", str(src), "--format", "dxf"])
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


def test_batch_convert_recursive_keeps_originals(tmp_path, make_image):
    root = tmp_path / "fotos"
    sub = root / "sub"
    sub.mkdir(parents=True)
    (root / "a.png").write_bytes(make_image())
    (sub / "b.jpg").write_bytes(make_image(fmt="JPEG"))
    result = runner.invoke(
        app, ["batch-convert", str(root), "--format", "webp"]
    )
    assert result.exit_code == 0, result.output
    assert (root / "a.webp").exists()
    assert (sub / "b.webp").exists()
    assert (root / "a.png").exists()
    assert (sub / "b.jpg").exists()


def test_batch_convert_with_delete_originals(tmp_path, make_image):
    root = tmp_path / "fotos"
    sub = root / "sub"
    sub.mkdir(parents=True)
    (root / "a.png").write_bytes(make_image())
    (sub / "b.jpg").write_bytes(make_image(fmt="JPEG"))
    result = runner.invoke(
        app,
        ["batch-convert", str(root), "--format", "webp", "--delete-originals"],
    )
    assert result.exit_code == 0, result.output
    assert (root / "a.webp").exists()
    assert (sub / "b.webp").exists()
    assert not (root / "a.png").exists()
    assert not (sub / "b.jpg").exists()


def test_batch_convert_writes_to_separate_out_dir(tmp_path, make_image):
    root = tmp_path / "fotos"
    sub = root / "sub"
    sub.mkdir(parents=True)
    (root / "a.png").write_bytes(make_image())
    (sub / "b.jpg").write_bytes(make_image(fmt="JPEG"))
    out = tmp_path / "out"
    result = runner.invoke(
        app,
        ["batch-convert", str(root), "-o", str(out), "--format", "webp"],
    )
    assert result.exit_code == 0, result.output
    assert (out / "a.webp").exists()
    assert (out / "sub" / "b.webp").exists()
    assert (root / "a.png").exists()
    assert (sub / "b.jpg").exists()


def test_batch_convert_skips_non_images(tmp_path, make_image):
    root = tmp_path / "fotos"
    root.mkdir()
    (root / "a.png").write_bytes(make_image())
    (root / "notes.txt").write_text("não é imagem")
    result = runner.invoke(
        app, ["batch-convert", str(root), "--format", "webp"]
    )
    assert result.exit_code == 0, result.output
    assert (root / "a.webp").exists()
    assert (root / "notes.txt").exists()


def test_batch_convert_empty_folder(tmp_path):
    empty = tmp_path / "vazio"
    empty.mkdir()
    result = runner.invoke(
        app, ["batch-convert", str(empty), "--format", "webp"]
    )
    assert result.exit_code == 0, result.output
    assert "nenhuma imagem" in result.output


def test_batch_convert_requires_folder(tmp_path):
    file = tmp_path / "a.png"
    file.write_bytes(b"")
    result = runner.invoke(
        app, ["batch-convert", str(file), "--format", "webp"]
    )
    assert result.exit_code != 0


def _make_folder(tmp_path, make_image):
    folder = tmp_path / "pasta"
    (folder / "sub").mkdir(parents=True)
    (folder / "a.png").write_bytes(make_image(20, 20))
    (folder / "sub" / "b.png").write_bytes(make_image(20, 20))
    (folder / "ignorar.txt").write_bytes(b"nao e imagem")
    hidden = folder / ".oculto"
    hidden.mkdir()
    (hidden / "c.png").write_bytes(make_image(20, 20))
    return folder


def test_folder_input_expands_recursively(tmp_path, make_image):
    folder = _make_folder(tmp_path, make_image)
    out = tmp_path / "saida"
    result = runner.invoke(app, ["compress", str(folder), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert (out / "a-comprimido.png").exists()
    assert (out / "sub" / "b-comprimido.png").exists()
    assert not list(out.rglob("*ignorar*"))
    assert not list(out.rglob("*c-comprimido*"))


def test_folder_without_images_errors(tmp_path):
    folder = tmp_path / "vazia"
    folder.mkdir()
    result = runner.invoke(app, ["compress", str(folder)])
    assert result.exit_code != 0
    assert "nenhum arquivo compatível" in result.output


def test_ext_overrides_whitelist(tmp_path, make_image):
    folder = tmp_path / "dados"
    folder.mkdir()
    (folder / "foto.imguncommon").write_bytes(make_image(20, 20))
    out = tmp_path / "saida"
    result = runner.invoke(
        app, ["compress", str(folder), "--ext", ".imguncommon", "-o", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert (out / "foto-comprimido.imguncommon").exists()


def test_multi_file_fan_out_via_cli(tmp_path, make_image):
    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    a.write_bytes(make_image(20, 20))
    b.write_bytes(make_image(20, 20))
    out = tmp_path / "saida"
    result = runner.invoke(app, ["compress", str(a), str(b), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert (out / "a-comprimido.png").exists()
    assert (out / "b-comprimido.png").exists()


def test_batch_convert_still_uses_folder_walker(tmp_path, make_image):
    # Regressão: o comando bespoke batch-convert continua funcionando após o
    # refactor pra _expand_paths.
    folder = tmp_path / "fotos"
    folder.mkdir()
    (folder / "a.png").write_bytes(make_image(20, 20))
    out = tmp_path / "saida"
    result = runner.invoke(app, ["batch-convert", str(folder), "--format", "webp", "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert (out / "a.webp").exists()
