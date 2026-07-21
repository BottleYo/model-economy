#!/usr/bin/env python3
"""生成官方目录提交使用的 512×512 PNG 品牌图。"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "plugins/model-economy/assets/brand/logo-512.png"


def render(output: Path) -> None:
    image = Image.new("RGB", (512, 512), "#F4F0E8")
    draw = ImageDraw.Draw(image)
    for top in (120, 232, 344):
        draw.rectangle((96, top, 264, top + 48), fill="#1F2528")
    draw.rectangle((264, 88, 320, 424), fill="#1F6F6A")
    draw.rectangle((320, 232, 416, 280), fill="#D98B2B")
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG", optimize=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    render(args.output)


if __name__ == "__main__":
    main()
