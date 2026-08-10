#!/usr/bin/env python3
"""Render a PNG preview from route_to_svg layout JSON, including start/finish labels."""

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
    "S": ("111", "100", "111", "001", "111"),
    "F": ("111", "100", "110", "100", "100"),
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
    # Keep two-digit checkpoint numbers legible in the 3:4 reference PNG.
    # The marker is intentionally larger than the route stroke so the label
    # remains readable after the image is resized by a generation model.
    scale = 3 if len(text) <= 2 else 2
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


def endpoint_records(layout: dict, points: list[tuple[float, float]]) -> list[dict]:
    configured = layout.get("endpoints") or {}
    result = []
    for role, default_name, anchor in (("start", "起点", points[0]), ("finish", "终点", points[-1])):
        item = configured.get(role) if isinstance(configured.get(role), dict) else {}
        configured_anchor = item.get("anchor") if isinstance(item.get("anchor"), dict) else {}
        result.append(
            {
                "role": role,
                "name": str(item.get("name") or default_name),
                "anchor": {
                    "x": float(configured_anchor.get("x", anchor[0])),
                    "y": float(configured_anchor.get("y", anchor[1])),
                },
            }
        )
    return result


def overlay_endpoint_names(image: bytearray, width: int, height: int, endpoints: list[dict], closed: bool) -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return
    font = None
    for candidate in (
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/msyh.ttc",
    ):
        try:
            font = ImageFont.truetype(candidate, 17)
            break
        except OSError:
            continue
    if font is None:
        return
    canvas = Image.frombytes("RGB", (width, height), bytes(image))
    draw = ImageDraw.Draw(canvas)
    records = endpoints[:1] if closed else endpoints
    for endpoint in records:
        role = endpoint["role"]
        prefix = "起点/终点" if closed else ("起点" if role == "start" else "终点")
        text_value = f"{prefix}：{endpoint['name']}"
        x = round(float(endpoint["anchor"]["x"]))
        y = round(float(endpoint["anchor"]["y"]))
        bbox = draw.textbbox((0, 0), text_value, font=font, stroke_width=1)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        place_left = x >= width / 2
        left = x - text_width - 34 if place_left else x + 24
        left = max(6, min(width - text_width - 18, left))
        top = max(6, min(height - text_height - 18, y - text_height - 18))
        color = (46, 125, 50) if role == "start" else (198, 40, 40)
        box = (left - 7, top - 5, left + text_width + 7, top + text_height + 7)
        target_x = box[2] if place_left else box[0]
        target_y = (box[1] + box[3]) // 2
        draw.line((x, y, target_x, target_y), fill=(255, 255, 255), width=6)
        draw.line((x, y, target_x, target_y), fill=color, width=2)
        draw.rounded_rectangle(box, radius=7, fill=(255, 253, 247), outline=color, width=2)
        draw.text((left, top), text_value, font=font, fill=color, stroke_width=1, stroke_fill=(255, 253, 247))
    image[:] = canvas.tobytes()


def checkpoint_badge_positions(checkpoints: list[dict], width: int, height: int) -> list[tuple[int, int]]:
    """Keep badges readable while retaining an explicit leader to the true anchor."""
    positions: list[tuple[int, int]] = []
    offsets = ((0, 0), (34, 0), (-34, 0), (0, 34), (0, -34), (28, 28), (-28, 28), (28, -28), (-28, -28))
    minimum_distance_sq = 32 * 32
    for checkpoint in checkpoints:
        anchor = checkpoint.get("anchor") or {}
        anchor_x = round(float(anchor["x"]))
        anchor_y = round(float(anchor["y"]))
        selected = (anchor_x, anchor_y)
        for offset_x, offset_y in offsets:
            candidate = (anchor_x + offset_x, anchor_y + offset_y)
            if not (18 <= candidate[0] < width - 18 and 18 <= candidate[1] < height - 18):
                continue
            if all((candidate[0] - x) ** 2 + (candidate[1] - y) ** 2 >= minimum_distance_sq for x, y in positions):
                selected = candidate
                break
        positions.append(selected)
    return positions


def render(
    layout_file: Path,
    output_file: Path,
    require_checkpoints: bool = True,
    progress_start: float = 0.0,
    progress_end: float = 1.0,
) -> Path:
    layout = json.loads(layout_file.read_text(encoding="utf-8"))
    canvas = layout.get("canvas") or {}
    width = int(canvas.get("width", 900))
    height = int(canvas.get("height", 1200))
    points = [(float(point["x"]), float(point["y"])) for point in layout.get("simplified_points") or []]
    progresses = [float(value) for value in layout.get("simplified_progress") or []]
    checkpoints = layout.get("checkpoints") or []
    if len(points) < 2:
        raise ValueError("layout JSON has no usable simplified route")
    if len(progresses) != len(points):
        indices = layout.get("simplified_original_indices") or []
        original_count = int(layout.get("original_point_count") or 0)
        if len(indices) != len(points) or original_count < 2:
            raise ValueError("layout JSON lacks simplified_progress; rerun route_to_svg.py")
        progresses = [float(index) / float(original_count - 1) for index in indices]
    if not (0.0 <= progress_start < progress_end <= 1.0):
        raise ValueError("progress range must satisfy 0 <= start < end <= 1")
    if require_checkpoints and not checkpoints:
        raise ValueError("layout JSON has no numbered checkpoints; rerun route_to_svg.py with --checkpoints-json")
    if width <= 0 or height <= 0 or width > 5000 or height > 5000:
        raise ValueError("invalid canvas dimensions")
    endpoints = endpoint_records(layout, points)

    image = bytearray((255, 253, 247) * (width * height))
    segment_mode = progress_start > 0.0 or progress_end < 1.0
    for first, second in zip(points, points[1:]):
        draw_line(image, width, height, first, second, 14, (255, 255, 255))
    for index, (first, second) in enumerate(zip(points, points[1:])):
        midpoint = (progresses[index] + progresses[index + 1]) / 2.0
        highlighted = progress_start <= midpoint <= progress_end
        color = (216, 67, 21) if highlighted else (183, 170, 160)
        thickness = 9 if highlighted else 6
        draw_line(image, width, height, first, second, thickness, color)
    if layout.get("closed"):
        draw_line(image, width, height, points[-1], points[0], 14, (255, 255, 255))
        closure_highlighted = progress_end == 1.0
        draw_line(image, width, height, points[-1], points[0], 9 if closure_highlighted else 6, (216, 67, 21) if closure_highlighted else (183, 170, 160))

    start = endpoints[0]["anchor"]
    finish = endpoints[1]["anchor"]
    start_x, start_y = round(float(start["x"])), round(float(start["y"]))
    finish_x, finish_y = round(float(finish["x"])), round(float(finish["y"]))
    if layout.get("closed"):
        draw_disk(image, width, height, start_x, start_y, 18, (255, 255, 255))
        draw_disk(image, width, height, start_x, start_y, 15, (198, 40, 40))
        draw_disk(image, width, height, start_x, start_y, 11, (46, 125, 50))
        draw_number(image, width, height, "S", start_x, start_y, (255, 255, 255))
    else:
        for x, y, color, label in (
            (start_x, start_y, (46, 125, 50), "S"),
            (finish_x, finish_y, (198, 40, 40), "F"),
        ):
            draw_disk(image, width, height, x, y, 17, (255, 255, 255))
            draw_disk(image, width, height, x, y, 14, color)
            draw_number(image, width, height, label, x, y, (255, 255, 255))

    badge_positions = checkpoint_badge_positions(checkpoints, width, height)
    for checkpoint, (badge_x, badge_y) in zip(checkpoints, badge_positions):
        checkpoint_progress = float(checkpoint.get("track_progress", 0.0))
        if segment_mode and not (progress_start <= checkpoint_progress <= progress_end):
            continue
        anchor = checkpoint.get("anchor") or {}
        x = round(float(anchor["x"]))
        y = round(float(anchor["y"]))
        if (badge_x, badge_y) != (x, y):
            draw_line(image, width, height, (x, y), (badge_x, badge_y), 6, (255, 255, 255))
            draw_line(image, width, height, (x, y), (badge_x, badge_y), 2, (198, 40, 40))
            draw_disk(image, width, height, x, y, 5, (255, 255, 255))
            draw_disk(image, width, height, x, y, 3, (198, 40, 40))
        draw_disk(image, width, height, badge_x, badge_y, 15, (255, 255, 255))
        draw_disk(image, width, height, badge_x, badge_y, 13, (198, 40, 40))
        draw_disk(image, width, height, badge_x, badge_y, 11, (255, 255, 255))
        draw_number(image, width, height, checkpoint.get("number", ""), badge_x, badge_y, (105, 0, 0))

    overlay_endpoint_names(image, width, height, endpoints, bool(layout.get("closed")))
    write_png(output_file, width, height, image)
    return output_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a PNG route preview from route_to_svg layout JSON.")
    parser.add_argument("layout_json", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--allow-no-checkpoints", action="store_true", help="Only for early internal previews")
    parser.add_argument("--progress-start", type=float, default=0.0, help="Highlight segment start, from 0.0 to 1.0")
    parser.add_argument("--progress-end", type=float, default=1.0, help="Highlight segment end, from 0.0 to 1.0")
    args = parser.parse_args()
    output = args.output or args.layout_json.with_name(args.layout_json.stem.replace("轨迹布局", "轨迹预览") + ".png")
    try:
        result = render(
            args.layout_json,
            output,
            not args.allow_no_checkpoints,
            args.progress_start,
            args.progress_end,
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc
    print(result)


if __name__ == "__main__":
    main()
