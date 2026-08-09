#!/usr/bin/env python3
"""Add a deterministic schematic contour layer behind a reviewed route SVG."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path


def contour_path(cx: float, cy: float, rx: float, ry: float, phase: float, points: int = 72) -> str:
    values: list[str] = []
    for index in range(points):
        angle = 2 * math.pi * index / points
        wobble = 1 + 0.055 * math.sin(angle * 3 + phase) + 0.03 * math.sin(angle * 7 - phase)
        x = cx + rx * wobble * math.cos(angle)
        y = cy + ry * wobble * math.sin(angle)
        values.append(f"{'M' if index == 0 else 'L'} {x:.2f} {y:.2f}")
    return " ".join(values) + " Z"


def build_contours(layout: dict, count: int) -> str:
    points = layout.get("simplified_points") or []
    if len(points) < 2:
        raise ValueError("layout JSON has no usable simplified_points")
    xs = [float(point["x"]) for point in points]
    ys = [float(point["y"]) for point in points]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    paths = []
    for index in range(count):
        scale = 0.58 + index * 0.105
        d = contour_path(cx, cy, max(45, width * scale), max(45, height * scale), index * 0.83)
        paths.append(f'<path d="{d}" fill="none" stroke="#b8aa91" stroke-width="1.5" opacity="0.48"/>')
    return '<g id="schematic-contours" aria-label="示意等高线（非实测高程）">' + "".join(paths) + "</g>"


def generate(layout_file: Path, route_svg_file: Path, output_file: Path, count: int, require_checkpoints: bool = True) -> Path:
    layout = json.loads(layout_file.read_text(encoding="utf-8"))
    checkpoints = layout.get("checkpoints") or []
    if require_checkpoints and not checkpoints:
        raise ValueError("layout JSON has no numbered checkpoints; rerun route_to_svg.py with --checkpoints-json")
    svg = route_svg_file.read_text(encoding="utf-8")
    if "<svg" not in svg or "</svg>" not in svg:
        raise ValueError("route SVG is not a valid SVG document")
    contour_group = build_contours(layout, count)
    notice = '<text x="24" y="32" font-size="14" font-family="sans-serif" fill="#756b5b">示意等高线（非实测高程）</text>'
    marker = re.search(r"<path id=\"route-underlay\"", svg)
    if not marker:
        raise ValueError("route SVG is missing route-underlay")
    combined = svg[: marker.start()] + contour_group + notice + "\n  " + svg[marker.start():]
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(combined, encoding="utf-8")
    manifest = {
        "route_svg": route_svg_file.name,
        "layout_json": layout_file.name,
        "output_svg": output_file.name,
        "contour_type": "schematic_non_dem",
        "contour_count": count,
        "numbered_checkpoint_count": len(checkpoints),
        "checkpoint_numbers": [checkpoint.get("number") for checkpoint in checkpoints],
    }
    output_file.with_suffix(".json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a schematic contour reference behind a reviewed route SVG.")
    parser.add_argument("layout_json", type=Path)
    parser.add_argument("route_svg", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--count", type=int, default=7)
    parser.add_argument("--allow-no-checkpoints", action="store_true", help="Only for early geometry previews")
    args = parser.parse_args()
    if args.count < 3 or args.count > 20:
        raise SystemExit("--count must be between 3 and 20")
    output = args.output or args.route_svg.with_name(args.route_svg.stem.replace("轨迹骨架", "轨迹等高线参考") + ".svg")
    try:
        result = generate(args.layout_json, args.route_svg, output, args.count, not args.allow_no_checkpoints)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc
    print(result)


if __name__ == "__main__":
    main()
