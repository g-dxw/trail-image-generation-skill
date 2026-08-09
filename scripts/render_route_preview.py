#!/usr/bin/env python3
"""Render a dependency-free PNG preview from route_to_svg layout JSON."""

from __future__ import annotations

import argparse
import json
import struct
import zlib
from pathlib import Path


Color = tuple[int, int, int]

DIGITS = {
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"),
    "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"),
    "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "111"),
}


def set_pixel(image: bytearray, width: int, height: int, x: int, y: int, color: Color) -> None:
    if 0 <= x < width and 0 <= y < height:
        offset = (y * width + x) * 3
        image[offset : offset + 3] = bytes(color)


def draw_disk(image: bytearray, width: int, height: int, cx: int, cy: int, radius: int, color: Color) -> None:
    radius_sq = radius * radius
    for y in range(cy - radius, cy + radius + 1):
        for x in range(cx - radius, cx + radius + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= radius_sq:
                set_pixel(image, width, height, x, y, color)


def draw_line(image: bytearray, width: int, height: int, start: tuple[float, float], end: tuple[float, float], thickness: int, color: Color) -> None:
    x1, y1 = start
    x2, y2 = end
    steps = max(1, int(max(abs(x2 - x1), abs(y2 - y1))))
    for index in range(steps + 1):
        ratio = index / steps
        x = round(x1 + (x2 - x1) * ratio)
        y = round(y1 + (y2 - y1) * ratio)
        draw_disk(image, width, height, x, y, max(1, thickness // 2), color)


def draw_number(image: bytearray, width: int, height: int, number: object, cx: int, cy: int, color: Color) -> None:
    text = str(number)
    scale = 2 if len(text) <= 2 else 1
    glyph_width = 3 * scale
    spacing = scale
    total_width = len(text) * glyph_width + max(0, len(text) - 1) * spacing
    start_x = cx - total_width // 2
    start_y = cy - (5 * scale) // 2
    for position, character in enumerate(text):
        glyph = DIGITS.get(character)
        if not glyph:
            continue
        base_x = start_x + position * (glyph_width + spacing)
        for row, bits in enumerate(glyph):
            for column, bit in enumerate(bits):
                if bit == "1":
                    for dy in range(scale):
                        for dx in range(scale):
                            set_pixel(image, width, height, base_x + column * scale + dx, start_y + row * scale + dy, color)


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def write_png(path: Path, width: int, height: int, pixels: bytearray) -> None:
    rows = []
    stride = width * 3
    for y in range(height):
        rows.append(b"\x00" + bytes(pixels[y * stride : (y + 1) * stride]))
    payload = b"\x89PNG\r\n\x1a\n"
    payload += png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    payload += png_chunk(b"IDAT", zlib.compress(b"".join(rows), level=9))
    payload += png_chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def render(layout_file: Path, output_file: Path, require_checkpoints: bool = True) -> Path:
    layout = json.loads(layout_file.read_text(encoding="utf-8"))
    canvas = layout.get("canvas") or {}
    width = int(canvas.get("width", 900))
    height = int(canvas.get("height", 1200))
    points = [(float(point["x"]), float(point["y"])) for point in layout.get("simplified_points") or []]
    checkpoints = layout.get("checkpoints") or []
    if len(points) < 2:
        raise ValueError("layout JSON has no usable simplified route")
    if require_checkpoints and not checkpoints:
        raise ValueError("layout JSON has no numbered checkpoints; rerun route_to_svg.py with --checkpoints-json")
    if width <= 0 or height <= 0 or width > 5000 or height > 5000:
        raise ValueError("invalid canvas dimensions")

    image = bytearray((255, 253, 247) * (width * height))
    for first, second in zip(points, points[1:]):
        draw_line(image, width, height, first, second, 14, (255, 255, 255))
    for first, second in zip(points, points[1:]):
        draw_line(image, width, height, first, second, 8, (216, 67, 21))
    if layout.get("closed"):
        draw_line(image, width, height, points[-1], points[0], 14, (255, 255, 255))
        draw_line(image, width, height, points[-1], points[0], 8, (216, 67, 21))

    for checkpoint in checkpoints:
        anchor = checkpoint.get("anchor") or {}
        x = round(float(anchor["x"]))
        y = round(float(anchor["y"]))
        draw_disk(image, width, height, x, y, 11, (255, 255, 255))
        draw_disk(image, width, height, x, y, 8, (198, 40, 40))
        draw_disk(image, width, height, x, y, 5, (255, 255, 255))
        draw_number(image, width, height, checkpoint.get("number", ""), x, y, (127, 0, 0))

    write_png(output_file, width, height, image)
    return output_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a PNG route preview from route_to_svg layout JSON.")
    parser.add_argument("layout_json", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--allow-no-checkpoints", action="store_true", help="Only for early internal previews")
    args = parser.parse_args()
    output = args.output or args.layout_json.with_name(args.layout_json.stem.replace("轨迹布局", "轨迹预览") + ".png")
    try:
        result = render(args.layout_json, output, not args.allow_no_checkpoints)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc
    print(result)


if __name__ == "__main__":
    main()
