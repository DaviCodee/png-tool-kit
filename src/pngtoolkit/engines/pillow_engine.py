"""Motor primário: invólucro fino sobre o Pillow.

O Pillow é a única dependência do núcleo e cobre PNG, JPEG, WebP, GIF, BMP, TIFF e
ICO nativamente. Todas as funções recebem/devolvem objetos ``PIL.Image.Image`` ou
``bytes``; nenhuma lógica de operação vive aqui.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from PIL.ExifTags import TAGS

from pngtoolkit.core.errors import (
    InvalidInputError,
    OperationError,
    UnsupportedFormatError,
)

# Nome curto -> (formato Pillow, media type)
_FORMATS: dict[str, tuple[str, str]] = {
    "png": ("PNG", "image/png"),
    "jpg": ("JPEG", "image/jpeg"),
    "jpeg": ("JPEG", "image/jpeg"),
    "webp": ("WEBP", "image/webp"),
    "gif": ("GIF", "image/gif"),
    "bmp": ("BMP", "image/bmp"),
    "tiff": ("TIFF", "image/tiff"),
    "ico": ("ICO", "image/x-icon"),
    "avif": ("AVIF", "image/avif"),
}

# Formatos que perdem o canal alfa ao salvar.
_NO_ALPHA = {"JPEG", "BMP"}
# Formatos que respeitam o parâmetro ``quality``.
_LOSSY = {"JPEG", "WEBP", "AVIF"}


def media_type(fmt: str) -> str:
    """Media type para um nome de formato curto."""
    try:
        return _FORMATS[fmt.lower()][1]
    except KeyError:
        raise UnsupportedFormatError(f"formato não suportado: {fmt!r}") from None


def _pillow_format(fmt: str) -> str:
    try:
        return _FORMATS[fmt.lower()][0]
    except KeyError:
        raise UnsupportedFormatError(f"formato não suportado: {fmt!r}") from None


def open_image(data: bytes, name: str | None = None) -> Image.Image:
    """Abre os ``bytes`` como imagem; levanta :class:`InvalidInputError` se falhar."""
    try:
        image = Image.open(BytesIO(data))
        image.load()
    except Exception as exc:
        raise InvalidInputError(f"imagem inválida: {name or 'entrada'}") from exc
    return image


def default_format(image: Image.Image, fallback: str = "png") -> str:
    """Nome curto do formato de origem da imagem, ou ``fallback``."""
    fmt = (image.format or "").lower()
    if fmt == "jpeg":
        return "jpg"
    return fmt if fmt in _FORMATS else fallback


def to_bytes(
    image: Image.Image,
    fmt: str,
    *,
    quality: int | None = None,
    optimize: bool = False,
    exif: bytes | None = None,
) -> bytes:
    """Serializa ``image`` no formato ``fmt`` e devolve os bytes."""
    pillow_fmt = _pillow_format(fmt)
    frame = image
    if pillow_fmt in _NO_ALPHA and frame.mode in {"RGBA", "LA", "P"}:
        frame = frame.convert("RGB")

    options: dict[str, Any] = {}
    if optimize and pillow_fmt in {"PNG", "JPEG"}:
        options["optimize"] = True
    if quality is not None and pillow_fmt in _LOSSY:
        options["quality"] = quality
    if exif is not None:
        options["exif"] = exif

    buffer = BytesIO()
    try:
        frame.save(buffer, format=pillow_fmt, **options)
    except (KeyError, OSError, ValueError) as exc:
        raise OperationError(f"falha ao salvar como {fmt!r}: {exc}") from exc
    return buffer.getvalue()


# --- transformações ---------------------------------------------------------


def compute_size(
    image: Image.Image,
    *,
    width: int | None,
    height: int | None,
    percent: float | None,
) -> tuple[int, int]:
    """Resolve a dimensão final mantendo proporção quando só um lado é dado."""
    src_w, src_h = image.size
    if percent is not None:
        factor = percent / 100.0
        return max(1, round(src_w * factor)), max(1, round(src_h * factor))
    if width is not None and height is not None:
        return width, height
    if width is not None:
        ratio = width / src_w
        return width, max(1, round(src_h * ratio))
    if height is not None:
        ratio = height / src_h
        return max(1, round(src_w * ratio)), height
    raise InvalidInputError("informe width, height ou percent")


def resize(image: Image.Image, width: int, height: int) -> Image.Image:
    """Redimensiona para ``width`` x ``height`` com reamostragem Lanczos."""
    return image.resize((width, height), Image.Resampling.LANCZOS)


def crop_box(image: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    """Recorta pela caixa ``(left, top, right, bottom)`` em pixels."""
    left, top, right, bottom = box
    src_w, src_h = image.size
    if not (0 <= left < right <= src_w and 0 <= top < bottom <= src_h):
        raise InvalidInputError(f"caixa de corte fora dos limites da imagem {image.size}")
    return image.crop(box)


def crop_anchored(image: Image.Image, width: int, height: int, anchor: str) -> Image.Image:
    """Recorta uma janela ``width`` x ``height`` ancorada na imagem."""
    src_w, src_h = image.size
    if width > src_w or height > src_h:
        raise InvalidInputError("dimensão de corte maior que a imagem")
    horizontal = {"left": 0, "center": (src_w - width) // 2, "right": src_w - width}
    vertical = {"top": 0, "middle": (src_h - height) // 2, "bottom": src_h - height}
    vname, _, hname = anchor.partition("-")
    if anchor == "center":
        vname, hname = "middle", "center"
    if vname not in vertical or hname not in horizontal:
        raise InvalidInputError(f"âncora inválida: {anchor!r}")
    x = horizontal[hname]
    y = vertical[vname]
    return image.crop((x, y, x + width, y + height))


def rotate(image: Image.Image, degrees: float, *, expand: bool = True) -> Image.Image:
    """Gira no sentido anti-horário; ``expand`` ajusta a tela à nova geometria."""
    return image.rotate(degrees, expand=expand)


def flip(image: Image.Image, direction: str) -> Image.Image:
    """Espelha na ``horizontal`` ou ``vertical``."""
    if direction == "horizontal":
        return image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if direction == "vertical":
        return image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    raise InvalidInputError(f"direção inválida: {direction!r}")


def to_grayscale(image: Image.Image) -> Image.Image:
    """Converte para tons de cinza (modo L)."""
    return image.convert("L")


def apply_blur(
    image: Image.Image, radius: float, region: tuple[int, int, int, int] | None
) -> Image.Image:
    """Aplica desfoque gaussiano à imagem inteira ou só a ``region``."""
    blur = ImageFilter.GaussianBlur(radius=radius)
    if region is None:
        return image.filter(blur)
    work = image.copy()
    patch = work.crop(region).filter(blur)
    work.paste(patch, region)
    return work


# --- EXIF -------------------------------------------------------------------


def read_exif(image: Image.Image) -> dict[str, str]:
    """Lê os metadados EXIF como dicionário ``tag -> valor`` (strings)."""
    exif = image.getexif()
    result: dict[str, str] = {}
    for tag_id, value in exif.items():
        name = TAGS.get(tag_id, str(tag_id))
        result[name] = str(value)
    return result


def strip_exif(image: Image.Image) -> Image.Image:
    """Devolve uma cópia da imagem sem nenhum metadado (incl. EXIF)."""
    clean = Image.new(image.mode, image.size)
    clean.paste(image)
    return clean


# --- composição / efeitos ---------------------------------------------------


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("DejaVuSans-Bold.ttf", "Arial Bold.ttf", "Impact.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size)
    except TypeError:  # pragma: no cover - Pillow antigo sem size em load_default
        return ImageFont.load_default()


_ANCHORS: dict[str, tuple[float, float]] = {
    "top-left": (0.0, 0.0),
    "top-right": (1.0, 0.0),
    "bottom-left": (0.0, 1.0),
    "bottom-right": (1.0, 1.0),
    "center": (0.5, 0.5),
}


def _anchor_xy(
    base: tuple[int, int], overlay: tuple[float, float], position: str, margin: int
) -> tuple[int, int]:
    if position not in _ANCHORS:
        raise InvalidInputError(f"posição inválida: {position!r}")
    fx, fy = _ANCHORS[position]
    bw, bh = base
    ow, oh = overlay
    x = round((bw - ow) * fx)
    y = round((bh - oh) * fy)
    # Recolhe a margem em direção ao centro.
    x += margin if fx == 0.0 else -margin if fx == 1.0 else 0
    y += margin if fy == 0.0 else -margin if fy == 1.0 else 0
    return x, y


def stamp_text(
    image: Image.Image,
    text: str,
    *,
    position: str = "bottom-right",
    opacity: float = 0.5,
    margin: int = 16,
    font_size: int | None = None,
) -> Image.Image:
    """Carimba ``text`` semitransparente sobre a imagem."""
    base = image.convert("RGBA")
    size = font_size or max(16, base.size[0] // 20)
    font = _load_font(size)

    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = _anchor_xy(base.size, (tw, th), position, margin)
    alpha = max(0, min(255, round(opacity * 255)))
    draw.text((x - bbox[0], y - bbox[1]), text, font=font, fill=(255, 255, 255, alpha))

    return Image.alpha_composite(base, layer)


def stamp_image(
    image: Image.Image,
    watermark: Image.Image,
    *,
    position: str = "bottom-right",
    opacity: float = 0.5,
    margin: int = 16,
) -> Image.Image:
    """Sobrepõe a imagem ``watermark`` semitransparente sobre a base."""
    base = image.convert("RGBA")
    mark = watermark.convert("RGBA")
    if opacity < 1.0:
        alpha = mark.getchannel("A").point(lambda v: round(v * opacity))
        mark.putalpha(alpha)
    x, y = _anchor_xy(base.size, mark.size, position, margin)
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    layer.paste(mark, (x, y), mark)
    return Image.alpha_composite(base, layer)


# Tamanhos PNG gerados pelo favicon e seus nomes de saída.
_FAVICON_PNGS = [
    (16, "favicon-16x16.png"),
    (32, "favicon-32x32.png"),
    (180, "apple-touch-icon.png"),
    (192, "icon-192x192.png"),
    (512, "icon-512x512.png"),
]
# Tamanhos embutidos no .ico multi-resolução.
_ICO_SIZES = [16, 32, 48]


def make_favicon(image: Image.Image) -> list[tuple[str, bytes, str]]:
    """Gera os PNGs de favicon e um .ico multi-resolução.

    Devolve uma lista de ``(filename, data, media_type)``.
    """
    source = image.convert("RGBA")
    outputs: list[tuple[str, bytes, str]] = []

    for size, filename in _FAVICON_PNGS:
        resized = source.resize((size, size), Image.Resampling.LANCZOS)
        buffer = BytesIO()
        resized.save(buffer, format="PNG")
        outputs.append((filename, buffer.getvalue(), "image/png"))

    ico_buffer = BytesIO()
    largest = max(_ICO_SIZES)
    source.resize((largest, largest), Image.Resampling.LANCZOS).save(
        ico_buffer, format="ICO", sizes=[(s, s) for s in _ICO_SIZES]
    )
    outputs.append(("favicon.ico", ico_buffer.getvalue(), "image/x-icon"))
    return outputs


def _draw_meme_line(
    draw: ImageDraw.ImageDraw,
    base_size: tuple[int, int],
    text: str,
    font: Any,
    top: bool,
) -> None:
    bw, bh = base_size
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = round((bw - tw) / 2 - bbox[0])
    y = round((bh * 0.04 if top else bh - th - bh * 0.04) - bbox[1])
    stroke = max(1, getattr(font, "size", 24) // 15)
    draw.text(
        (x, y), text, font=font, fill=(255, 255, 255),
        stroke_width=stroke, stroke_fill=(0, 0, 0),
    )


def make_meme(image: Image.Image, top: str, bottom: str) -> Image.Image:
    """Escreve texto estilo meme (branco com contorno preto) no topo e na base."""
    base = image.convert("RGB")
    draw = ImageDraw.Draw(base)
    font = _load_font(max(24, base.size[0] // 10))
    if top:
        _draw_meme_line(draw, base.size, top.upper(), font, top=True)
    if bottom:
        _draw_meme_line(draw, base.size, bottom.upper(), font, top=False)
    return base
