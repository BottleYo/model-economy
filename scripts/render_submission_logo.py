#!/usr/bin/env python3
"""生成官方目录提交使用的 512×512 PNG 品牌图。"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

from render_social_preview import save_indexed_png


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "plugins/model-economy/assets/brand/logo-512.png"
LOGO_PALETTE = (
    (0xF4, 0xF0, 0xE8),
    (0x1F, 0x25, 0x28),
    (0x1F, 0x6F, 0x6A),
    (0xD9, 0x8B, 0x2B),
)


def render(output: Path) -> None:
    image = Image.new("P", (512, 512), 0)
    image.putpalette(bytes(channel for color in LOGO_PALETTE for channel in color))
    draw = ImageDraw.Draw(image)
    for top in (120, 232, 344):
        draw.rectangle((96, top, 264, top + 48), fill=1)
    draw.rectangle((264, 88, 320, 424), fill=2)
    draw.rectangle((320, 232, 416, 280), fill=3)
    save_indexed_png(image, output, palette=LOGO_PALETTE)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    render(args.output)


if __name__ == "__main__":
    main()
