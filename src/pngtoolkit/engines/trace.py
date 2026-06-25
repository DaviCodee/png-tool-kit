"""Vetorização raster -> SVG via ImageMagick + potrace (extra ``svg``).

Reescrito a partir do fluxo do próprio autor no ``site_principal``: o ImageMagick
binariza a imagem (limiar) e o potrace traça o contorno gerando o SVG. Não há
dependência Python — apenas os binários ``magick`` e ``potrace`` no sistema.
"""

from __future__ import annotations

from pngtoolkit.core.process import require_binary, run_command
from pngtoolkit.core.workspace import temp_workspace


def png_to_svg(data: bytes, *, threshold: int = 50) -> bytes:
    """Converte uma imagem raster em SVG. ``threshold`` é o limiar 1–99 (%)."""
    require_binary("magick")
    require_binary("potrace")
    pct = max(1, min(99, threshold))

    with temp_workspace() as tmp:
        src = tmp / "input"
        src.write_bytes(data)
        pbm = tmp / "trace.pbm"
        svg = tmp / "output.svg"

        result = run_command(
            ["magick", str(src), "-threshold", f"{pct}%", "-alpha", "off", "pbm:-"],
            timeout=30,
        )
        pbm.write_bytes(result.stdout)
        run_command(["potrace", str(pbm), "-s", "-o", str(svg)], timeout=30)
        return svg.read_bytes()
