#!/usr/bin/env python3
"""Render the social preview with deterministic Pillow bitmap primitives."""

from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path

from PIL import Image, ImageDraw


WIDTH, HEIGHT = 1280, 640
BACKGROUND, TEXT, MUTED, RULE, TEAL, AMBER = range(6)
PALETTE = (
    (0x14, 0x17, 0x19),
    (0xF5, 0xF7, 0xF7),
    (0xC8, 0xD0, 0xD2),
    (0x64, 0x70, 0x77),
    (0x34, 0xC6, 0xA4),
    (0xF6, 0xB7, 0x4D),
)
BITMAP_FONT = {
    "0": "01110/10001/10011/10101/11001/10001/01110",
    "1": "00100/01100/00100/00100/00100/00100/01110",
    "2": "01110/10001/00001/00010/00100/01000/11111",
    "3": "11110/00001/00001/01110/00001/00001/11110",
    "A": "01110/10001/10001/11111/10001/10001/10001",
    "B": "11110/10001/10001/11110/10001/10001/11110",
    "C": "01111/10000/10000/10000/10000/10000/01111",
    "D": "11110/10001/10001/10001/10001/10001/11110",
    "E": "11111/10000/10000/11110/10000/10000/11111",
    "F": "11111/10000/10000/11110/10000/10000/10000",
    "G": "01111/10000/10000/10111/10001/10001/01111",
    "H": "10001/10001/10001/11111/10001/10001/10001",
    "I": "11111/00100/00100/00100/00100/00100/11111",
    "J": "00111/00010/00010/00010/00010/10010/01100",
    "K": "10001/10010/10100/11000/10100/10010/10001",
    "L": "10000/10000/10000/10000/10000/10000/11111",
    "M": "10001/11011/10101/10101/10001/10001/10001",
    "N": "10001/11001/10101/10011/10001/10001/10001",
    "O": "01110/10001/10001/10001/10001/10001/01110",
    "P": "11110/10001/10001/11110/10000/10000/10000",
    "Q": "01110/10001/10001/10001/10101/10010/01101",
    "R": "11110/10001/10001/11110/10100/10010/10001",
    "S": "01111/10000/10000/01110/00001/00001/11110",
    "T": "11111/00100/00100/00100/00100/00100/00100",
    "U": "10001/10001/10001/10001/10001/10001/01110",
    "V": "10001/10001/10001/10001/10001/01010/00100",
    "W": "10001/10001/10001/10101/10101/10101/01010",
    "X": "10001/10001/01010/00100/01010/10001/10001",
    "Y": "10001/10001/01010/00100/00100/00100/00100",
    "Z": "11111/00001/00010/00100/01000/10000/11111",
    "a": "00000/00000/01110/00001/01111/10001/01111",
    "b": "10000/10000/10110/11001/10001/10001/11110",
    "c": "00000/00000/01110/10001/10000/10001/01110",
    "d": "00001/00001/01101/10011/10001/10001/01111",
    "e": "00000/00000/01110/10001/11111/10000/01110",
    "f": "00110/01001/01000/11100/01000/01000/01000",
    "g": "00000/01111/10001/01111/00001/10001/01110",
    "h": "10000/10000/10110/11001/10001/10001/10001",
    "i": "00100/00000/01100/00100/00100/00100/01110",
    "j": "00010/00000/00110/00010/00010/10010/01100",
    "k": "10000/10000/10010/10100/11000/10100/10010",
    "l": "01100/00100/00100/00100/00100/00100/01110",
    "m": "00000/00000/11010/10101/10101/10101/10101",
    "n": "00000/00000/10110/11001/10001/10001/10001",
    "o": "00000/00000/01110/10001/10001/10001/01110",
    "p": "00000/00000/11110/10001/11110/10000/10000",
    "q": "00000/00000/01111/10001/01111/00001/00001",
    "r": "00000/00000/10110/11001/10000/10000/10000",
    "s": "00000/00000/01111/10000/01110/00001/11110",
    "t": "01000/01000/11100/01000/01000/01001/00110",
    "u": "00000/00000/10001/10001/10001/10011/01101",
    "v": "00000/00000/10001/10001/10001/01010/00100",
    "w": "00000/00000/10001/10001/10101/10101/01010",
    "x": "00000/00000/10001/01010/00100/01010/10001",
    "y": "00000/00000/10001/10001/01111/00001/01110",
    "z": "00000/00000/11111/00010/00100/01000/11111",
    " ": "000/000/000/000/000/000/000",
    ".": "000/000/000/000/000/010/010",
    "/": "00001/00010/00010/00100/01000/01000/10000",
    "·": "000/000/000/010/000/000/000",
}
PREVIEW_BADGES = (
    ((248, 346, 460, 390), "STRONG / DECIDE", 2),
    ((928, 346, 1150, 390), "STRONG / VERIFY", 2),
)


def bitmap_text_width(text: str, scale: int) -> int:
    widths = [(len(BITMAP_FONT[character].split("/")[0]) + 1) * scale for character in text]
    return sum(widths) - scale + max(1, scale // 4)


def draw_bitmap_text(
    image: Image.Image,
    position: tuple[int, int],
    text: str,
    scale: int,
    color: int,
    *,
    bold: bool = False,
) -> None:
    draw = ImageDraw.Draw(image)
    cursor_x, cursor_y = position
    extra = max(1, scale // 4) if bold else 0
    for character in text:
        try:
            rows = BITMAP_FONT[character].split("/")
        except KeyError as error:
            raise ValueError(f"Unsupported preview character: {character!r}") from error
        for row_index, row in enumerate(rows):
            for column_index, pixel in enumerate(row):
                if pixel == "1":
                    left = cursor_x + column_index * scale
                    top = cursor_y + row_index * scale
                    draw.rectangle(
                        (left, top, left + scale - 1 + extra, top + scale - 1),
                        fill=color,
                    )
        cursor_x += (len(rows[0]) + 1) * scale


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    checksum = zlib.crc32(kind)
    checksum = zlib.crc32(payload, checksum)
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)


def stored_zlib(data: bytes) -> bytes:
    blocks = bytearray(b"\x78\x01")
    for offset in range(0, len(data), 65_535):
        block = data[offset : offset + 65_535]
        final = offset + len(block) == len(data)
        blocks.append(1 if final else 0)
        blocks.extend(struct.pack("<H", len(block)))
        blocks.extend(struct.pack("<H", 0xFFFF - len(block)))
        blocks.extend(block)
    blocks.extend(struct.pack(">I", zlib.adler32(data)))
    return bytes(blocks)


def save_indexed_png(
    image: Image.Image,
    output: Path,
    *,
    palette: tuple[tuple[int, int, int], ...] = PALETTE,
) -> None:
    pixels = image.tobytes()
    stride = image.width
    scanlines = b"".join(
        b"\x00" + pixels[offset : offset + stride]
        for offset in range(0, len(pixels), stride)
    )
    header = struct.pack(">IIBBBBB", image.width, image.height, 8, 3, 0, 0, 0)
    palette_bytes = bytes(channel for color in palette for channel in color)
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", header)
        + png_chunk(b"PLTE", palette_bytes)
        + png_chunk(b"IDAT", stored_zlib(scanlines))
        + png_chunk(b"IEND", b"")
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)


def render(output: Path) -> None:
    image = Image.new("P", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.line((80, 130, 1200, 130), fill=RULE, width=2)
    draw.line((80, 496, 1200, 496), fill=RULE, width=2)
    draw.line(
        (80, 427, 248, 427, 248, 368, 460, 368, 460, 427, 588, 427, 588, 368, 758, 368, 758, 427, 928, 427, 928, 368, 1200, 368),
        fill=TEAL,
        width=4,
    )
    for bounds, _, _ in PREVIEW_BADGES:
        draw.rounded_rectangle(bounds, radius=2, fill=AMBER)
    draw_bitmap_text(image, (80, 170), "MODEL ECONOMY", 8, TEXT, bold=True)
    draw_bitmap_text(image, (84, 264), "Rigor scales with risk.", 3, TEXT)
    draw_bitmap_text(image, (84, 306), "Policy caps. One orchestrator.", 3, MUTED)
    for (left, top, _, _), label, scale in PREVIEW_BADGES:
        draw_bitmap_text(image, (left + 12, top + 12), label, scale, BACKGROUND, bold=True)
    draw_bitmap_text(image, (588, 442), "BALANCED / EXECUTE", 2, TEAL, bold=True)
    draw_bitmap_text(
        image,
        (80, 530),
        "STRONG 0/1/2 · SUBAGENTS 3 MAX · NATIVE GATES",
        2,
        TEXT,
        bold=True,
    )
    save_indexed_png(image, output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the Model Economy social preview PNG.")
    parser.add_argument("--output", type=Path, default=Path("assets/social-preview.png"))
    args = parser.parse_args()
    render(args.output)


if __name__ == "__main__":
    main()
