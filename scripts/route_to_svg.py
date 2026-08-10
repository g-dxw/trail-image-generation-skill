#!/usr/bin/env python3
"""Convert a GPX, KML, or KMZ track into a simplified SVG route skeleton."""

from __future__ import annotations

import argparse
import html
import json
import math
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


EARTH_RADIUS_M = 6371008.8


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_coordinate_text(text: str, separator: str = ",") -> list[tuple[float, float, float | None]]:
    result = []
    for token in text.replace("\n", " ").split():
        values = token.split(separator)
        if len(values) < 2:
            continue
        try:
            lon = float(values[0])
            lat = float(values[1])
            ele = float(values[2]) if len(values) > 2 and values[2] else None
        except ValueError:
            continue
        result.append((lon, lat, ele))
    return result


def parse_kml(xml_bytes: bytes) -> list[list[tuple[float, float, float | None]]]:
    root = ET.fromstring(xml_bytes)
    tracks = []
    for element in root.iter():
        name = local_name(element.tag)
        if name == "Track":
            points = []
            for child in element.iter():
                if local_name(child.tag) != "coord" or not (child.text or "").strip():
                    continue
                values = child.text.split()
                if len(values) < 2:
                    continue
                try:
                    points.append((float(values[0]), float(values[1]), float(values[2]) if len(values) > 2 else None))
                except ValueError:
                    pass
            if len(points) >= 2:
                tracks.append(points)
        elif name == "LineString":
            coordinate_element = next(
                (child for child in element.iter() if local_name(child.tag) == "coordinates" and (child.text or "").strip()),
                None,
            )
            if coordinate_element is not None:
                points = parse_coordinate_text(coordinate_element.text or "")
                if len(points) >= 2:
                    tracks.append(points)
    return tracks


def parse_gpx(xml_bytes: bytes) -> list[list[tuple[float, float, float | None]]]:
    root = ET.fromstring(xml_bytes)
    tracks = []
    for segment in (element for element in root.iter() if local_name(element.tag) == "trkseg"):
        points = []
        for point in (child for child in segment if local_name(child.tag) == "trkpt"):
            try:
                lon = float(point.attrib["lon"])
                lat = float(point.attrib["lat"])
            except (KeyError, ValueError):
                continue
            elevation_text = next(((child.text or "").strip() for child in point if local_name(child.tag) == "ele"), "")
            try:
                elevation = float(elevation_text) if elevation_text else None
            except ValueError:
                elevation = None
            points.append((lon, lat, elevation))
        if len(points) >= 2:
            tracks.append(points)
    if tracks:
        return tracks
    route_points = []
    for point in (element for element in root.iter() if local_name(element.tag) == "rtept"):
        try:
            route_points.append((float(point.attrib["lon"]), float(point.attrib["lat"]), None))
        except (KeyError, ValueError):
            pass
    return [route_points] if len(route_points) >= 2 else []


def load_tracks(source: Path) -> list[list[tuple[float, float, float | None]]]:
    suffix = source.suffix.lower()
    if suffix == ".kmz":
        tracks = []
        with zipfile.ZipFile(source) as archive:
            for member in archive.infolist():
                if Path(member.filename).suffix.lower() == ".kml":
                    tracks.extend(parse_kml(archive.read(member)))
        return tracks
    data = source.read_bytes()
    if suffix == ".kml":
        return parse_kml(data)
    if suffix == ".gpx":
        return parse_gpx(data)
    raise ValueError(f"Unsupported route format: {source.suffix}")


def remove_consecutive_duplicates(points: list[tuple[float, float, float | None]]) -> list[tuple[float, float, float | None]]:
    result = []
    for point in points:
        if result and point[0] == result[-1][0] and point[1] == result[-1][1]:
            continue
        result.append(point)
    return result


def project(points: list[tuple[float, float, float | None]]) -> list[tuple[float, float]]:
    latitude_origin = math.radians(sum(point[1] for point in points) / len(points))
    return [
        (
            EARTH_RADIUS_M * math.radians(point[0]) * math.cos(latitude_origin),
            EARTH_RADIUS_M * math.radians(point[1]),
        )
        for point in points
    ]


def point_segment_distance(point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    if dx == 0 and dy == 0:
        return math.hypot(point[0] - start[0], point[1] - start[1])
    t = max(0.0, min(1.0, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / (dx * dx + dy * dy)))
    nearest = (start[0] + t * dx, start[1] + t * dy)
    return math.hypot(point[0] - nearest[0], point[1] - nearest[1])


def rdp_indices(points: list[tuple[float, float]], epsilon: float, offset: int = 0) -> list[int]:
    if len(points) <= 2:
        return [offset, offset + len(points) - 1] if len(points) == 2 else [offset]
    maximum_distance = -1.0
    maximum_index = 0
    for index in range(1, len(points) - 1):
        distance = point_segment_distance(points[index], points[0], points[-1])
        if distance > maximum_distance:
            maximum_distance = distance
            maximum_index = index
    if maximum_distance > epsilon:
        left = rdp_indices(points[: maximum_index + 1], epsilon, offset)
        right = rdp_indices(points[maximum_index:], epsilon, offset + maximum_index)
        return left[:-1] + right
    return [offset, offset + len(points) - 1]


def simplify_with_forced(points: list[tuple[float, float]], epsilon: float, forced: set[int]) -> list[int]:
    boundaries = sorted({0, len(points) - 1, *forced})
    selected = []
    for start, end in zip(boundaries, boundaries[1:]):
        indices = rdp_indices(points[start : end + 1], epsilon, start)
        selected.extend(indices if not selected else indices[1:])
    return sorted(set(selected))


def cumulative_distances(points: list[tuple[float, float]]) -> list[float]:
    values = [0.0]
    for start, end in zip(points, points[1:]):
        values.append(values[-1] + math.hypot(end[0] - start[0], end[1] - start[1]))
    return values


def progress_to_index(cumulative: list[float], progress: float) -> int:
    target = max(0.0, min(1.0, progress)) * cumulative[-1]
    return min(range(len(cumulative)), key=lambda index: abs(cumulative[index] - target))


def parse_progress(raw_progress: object) -> float:
    if isinstance(raw_progress, str) and raw_progress.endswith("%"):
        progress = float(raw_progress[:-1]) / 100.0
    else:
        progress = float(raw_progress)
        if progress > 1:
            progress /= 100.0
    return max(0.0, min(1.0, progress))


def load_route_spec(path: Path | None, cumulative: list[float]) -> tuple[list[dict], list[dict], list[dict], set[int], dict]:
    if path is None:
        return [], [], [], set(), {"start": {"name": "起点"}, "finish": {"name": "终点"}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        payload = {"checkpoints": payload}
    checkpoints = payload.get("checkpoints", payload if isinstance(payload, list) else [])
    checkpoint_result = []
    boundary_result = []
    segment_result = []
    forced = set()
    for position, checkpoint in enumerate(checkpoints, start=1):
        raw_progress = checkpoint.get("track_progress", checkpoint.get("progress"))
        if raw_progress is None:
            continue
        progress = parse_progress(raw_progress)
        index = progress_to_index(cumulative, progress)
        forced.add(index)
        checkpoint_result.append(
            {
                "number": checkpoint.get("number", position),
                "name": checkpoint.get("name", f"checkpoint-{position}"),
                "track_progress": progress,
                "track_point_index": index,
            }
        )
    for boundary in payload.get("boundaries", []):
        raw_progress = boundary.get("track_progress", boundary.get("progress"))
        if raw_progress is None:
            continue
        progress = parse_progress(raw_progress)
        index = progress_to_index(cumulative, progress)
        forced.add(index)
        boundary_result.append(
            {
                "name": boundary.get("name", "分段边界"),
                "track_progress": progress,
                "track_point_index": index,
                "show_marker": bool(boundary.get("show_marker", True)),
                "label_dx": float(boundary.get("label_dx", 14)),
                "label_dy": float(boundary.get("label_dy", -14)),
            }
        )
    for position, segment in enumerate(payload.get("segments", []), start=1):
        start_progress = parse_progress(segment.get("start_progress", 0))
        end_progress = parse_progress(segment.get("end_progress", 1))
        if end_progress < start_progress:
            raise ValueError(f"Segment {segment.get('name', position)} ends before it starts")
        start_index = progress_to_index(cumulative, start_progress)
        end_index = progress_to_index(cumulative, end_progress)
        forced.update((start_index, end_index))
        segment_result.append(
            {
                "name": segment.get("name", f"路段 {position}"),
                "description": segment.get("description", ""),
                "color": segment.get("color", "#d84315"),
                "start_progress": start_progress,
                "end_progress": end_progress,
                "start_track_point_index": start_index,
                "end_track_point_index": end_index,
            }
        )
    start_spec = payload.get("start") if isinstance(payload.get("start"), dict) else {}
    finish_spec = payload.get("finish") if isinstance(payload.get("finish"), dict) else {}
    endpoints = {
        "start": {"name": str(start_spec.get("name") or payload.get("start_name") or "起点")},
        "finish": {"name": str(finish_spec.get("name") or payload.get("finish_name") or "终点")},
    }
    return checkpoint_result, boundary_result, segment_result, forced, endpoints


def endpoint_label_svg(role: str, name: str, x: float, y: float, width: int) -> str:
    is_start = role == "start"
    role_label = "起点" if is_start else "终点"
    color = "#2e7d32" if is_start else "#c62828"
    label = html.escape(f"{role_label}：{name}")
    place_left = x >= width / 2
    label_x = x - 18 if place_left else x + 18
    text_anchor = "end" if place_left else "start"
    return (
        f'<line x1="{x}" y1="{y}" x2="{label_x}" y2="{y}" stroke="#ffffff" stroke-width="6"/>'
        f'<line x1="{x}" y1="{y}" x2="{label_x}" y2="{y}" stroke="{color}" stroke-width="2"/>'
        f'<text x="{label_x}" y="{y - 10}" text-anchor="{text_anchor}" font-size="17" font-family="sans-serif" '
        f'font-weight="700" fill="{color}" stroke="#fffdf7" stroke-width="5" paint-order="stroke">{label}</text>'
    )


def detect_closed(points: list[tuple[float, float]], mode: str, threshold_m: float) -> bool:
    if mode == "yes":
        return True
    if mode == "no":
        return False
    return math.hypot(points[-1][0] - points[0][0], points[-1][1] - points[0][1]) <= threshold_m


def simplify_to_target(points: list[tuple[float, float]], target: int, forced: set[int]) -> tuple[list[int], float]:
    if len(points) <= target:
        return list(range(len(points))), 0.0
    xs, ys = zip(*points)
    diagonal = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
    low, high = 0.0, diagonal
    best = simplify_with_forced(points, high, forced)
    for _ in range(36):
        middle = (low + high) / 2
        candidate = simplify_with_forced(points, middle, forced)
        if len(candidate) > target:
            low = middle
        else:
            high = middle
            best = candidate
    return best, high


def normalize(points: list[tuple[float, float]], width: int, height: int, padding: float) -> list[tuple[float, float]]:
    xs, ys = zip(*points)
    minimum_x, maximum_x = min(xs), max(xs)
    minimum_y, maximum_y = min(ys), max(ys)
    span_x = max(maximum_x - minimum_x, 1.0)
    span_y = max(maximum_y - minimum_y, 1.0)
    available_width = width - 2 * padding
    available_height = height - 2 * padding
    scale = min(available_width / span_x, available_height / span_y)
    offset_x = padding + (available_width - span_x * scale) / 2
    offset_y = padding + (available_height - span_y * scale) / 2
    return [
        (
            round(offset_x + (point[0] - minimum_x) * scale, 1),
            round(offset_y + (maximum_y - point[1]) * scale, 1),
        )
        for point in points
    ]


def path_data(points: list[tuple[float, float]], closed: bool) -> str:
    commands = [f"M {points[0][0]:g} {points[0][1]:g}"]
    commands.extend(f"L {point[0]:g} {point[1]:g}" for point in points[1:])
    if closed:
        commands.append("Z")
    return " ".join(commands)


def arrow_svg(points: list[tuple[float, float]], color: str) -> str:
    if len(points) < 2:
        return ""
    distances = cumulative_distances(points)
    target = distances[-1] * 0.58
    index = min(range(1, len(distances)), key=lambda value: abs(distances[value] - target))
    start = points[index - 1]
    end = points[index]
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    center_x = (start[0] + end[0]) / 2
    center_y = (start[1] + end[1]) / 2
    length, width = 13.0, 7.0
    tip = (center_x + math.cos(angle) * length, center_y + math.sin(angle) * length)
    left = (center_x + math.cos(angle + 2.45) * width, center_y + math.sin(angle + 2.45) * width)
    right = (center_x + math.cos(angle - 2.45) * width, center_y + math.sin(angle - 2.45) * width)
    return f'<polygon points="{tip[0]:.1f},{tip[1]:.1f} {left[0]:.1f},{left[1]:.1f} {right[0]:.1f},{right[1]:.1f}" fill="{html.escape(color)}" stroke="#fffdf7" stroke-width="2"/>'


def checkpoint_badge_positions(checkpoints: list[dict], width: int, height: int) -> list[tuple[float, float]]:
    positions: list[tuple[float, float]] = []
    offsets = ((0, 0), (34, 0), (-34, 0), (0, 34), (0, -34), (28, 28), (-28, 28), (28, -28), (-28, -28))
    minimum_distance_sq = 32 * 32
    for checkpoint in checkpoints:
        anchor = checkpoint["anchor"]
        anchor_x, anchor_y = float(anchor["x"]), float(anchor["y"])
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("route", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--track-index", type=int, default=None, help="Track index after sorting by point count; default uses longest")
    parser.add_argument("--target-points", type=int, default=60)
    parser.add_argument("--width", type=int, default=900)
    parser.add_argument("--height", type=int, default=1200)
    parser.add_argument("--padding", type=float, default=60.0)
    parser.add_argument("--closed", choices=("auto", "yes", "no"), default="auto")
    parser.add_argument("--loop-threshold-m", type=float, default=100.0)
    parser.add_argument("--checkpoints-json", type=Path)
    parser.add_argument("--start-label", help="Confirmed start name; overrides the route specification")
    parser.add_argument("--finish-label", help="Confirmed finish name; overrides the route specification")
    args = parser.parse_args()

    source = args.route.resolve()
    tracks = [remove_consecutive_duplicates(track) for track in load_tracks(source)]
    tracks = sorted((track for track in tracks if len(track) >= 2), key=len, reverse=True)
    if not tracks:
        raise SystemExit("No usable track found")
    selected_index = args.track_index or 0
    if selected_index < 0 or selected_index >= len(tracks):
        raise SystemExit(f"track-index must be between 0 and {len(tracks) - 1}")
    geographic = tracks[selected_index]
    projected = project(geographic)
    cumulative = cumulative_distances(projected)
    checkpoints, boundaries, segments, specification_forced, endpoints = load_route_spec(args.checkpoints_json, cumulative)
    if args.start_label:
        endpoints["start"]["name"] = args.start_label
    if args.finish_label:
        endpoints["finish"]["name"] = args.finish_label

    xs, ys = zip(*projected)
    extrema = {xs.index(min(xs)), xs.index(max(xs)), ys.index(min(ys)), ys.index(max(ys))}
    closed = detect_closed(projected, args.closed, args.loop_threshold_m)
    forced = set(specification_forced) | extrema
    if closed:
        forced.add(max(range(len(projected)), key=lambda index: math.hypot(projected[index][0] - projected[0][0], projected[index][1] - projected[0][1])))

    simplified_indices, epsilon = simplify_to_target(projected, max(8, args.target_points), forced)
    canvas_all = normalize(projected, args.width, args.height, args.padding)
    canvas_simplified = [canvas_all[index] for index in simplified_indices]
    route_path = path_data(canvas_simplified, closed)

    for checkpoint in checkpoints:
        x, y = canvas_all[checkpoint["track_point_index"]]
        checkpoint["anchor"] = {"x": x, "y": y}
    for boundary in boundaries:
        x, y = canvas_all[boundary["track_point_index"]]
        boundary["anchor"] = {"x": x, "y": y}

    segment_svg = []
    arrow_layers = []
    for segment in segments:
        indices = [
            index
            for index in simplified_indices
            if segment["start_track_point_index"] <= index <= segment["end_track_point_index"]
        ]
        segment_points = [canvas_all[index] for index in indices]
        if closed and segment["end_progress"] == 1.0 and segment_points[-1] != canvas_all[0]:
            segment_points.append(canvas_all[0])
        segment["svg_path_d"] = path_data(segment_points, False)
        segment_svg.append(
            f'<path d="{segment["svg_path_d"]}" fill="none" stroke="{html.escape(segment["color"])}" '
            'stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>'
        )
        arrow_layers.append(arrow_svg(segment_points, segment["color"]))

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = output_dir / source.stem
    svg_file = prefix.with_name(f"{source.stem}-轨迹骨架.svg")
    json_file = prefix.with_name(f"{source.stem}-轨迹布局.json")
    prompt_file = prefix.with_name(f"{source.stem}-轨迹提示片段.md")

    checkpoint_svg = []
    badge_positions = checkpoint_badge_positions(checkpoints, args.width, args.height)
    for checkpoint, (badge_x, badge_y) in zip(checkpoints, badge_positions):
        anchor = checkpoint["anchor"]
        label = html.escape(str(checkpoint["number"]))
        if (badge_x, badge_y) != (anchor["x"], anchor["y"]):
            checkpoint_svg.append(
                f'<line x1="{anchor["x"]}" y1="{anchor["y"]}" x2="{badge_x}" y2="{badge_y}" stroke="#ffffff" stroke-width="6"/>'
                f'<line x1="{anchor["x"]}" y1="{anchor["y"]}" x2="{badge_x}" y2="{badge_y}" stroke="#c62828" stroke-width="2"/>'
                f'<circle cx="{anchor["x"]}" cy="{anchor["y"]}" r="4" fill="#c62828" stroke="#ffffff" stroke-width="2"/>'
            )
        checkpoint_svg.append(
            f'<circle cx="{badge_x}" cy="{badge_y}" r="14" fill="#ffffff" stroke="#c62828" stroke-width="4"/>'
            f'<text x="{badge_x}" y="{badge_y + 5}" text-anchor="middle" font-size="16" font-family="sans-serif" font-weight="700" fill="#690000" stroke="#ffffff" stroke-width="2.5" paint-order="stroke">{label}</text>'
        )
    boundary_svg = []
    for boundary in boundaries:
        anchor = boundary["anchor"]
        if boundary["show_marker"]:
            boundary_svg.append(
                f'<rect x="{anchor["x"] - 7}" y="{anchor["y"] - 7}" width="14" height="14" '
                'rx="2" transform="rotate(45 '
                f'{anchor["x"]} {anchor["y"]})" fill="#fffdf7" stroke="#37474f" stroke-width="3"/>'
            )
        label_x = anchor["x"] + boundary["label_dx"]
        label_y = anchor["y"] + boundary["label_dy"]
        label = html.escape(boundary["name"])
        boundary_svg.append(
            f'<text x="{label_x}" y="{label_y}" font-size="16" font-family="sans-serif" font-weight="700" '
            f'fill="#37474f" stroke="#fffdf7" stroke-width="5" paint-order="stroke">{label}</text>'
        )
    legend_svg = []
    if segments:
        legend_height = 42 + len(segments) * 30
        legend_svg.append(
            f'<rect x="600" y="55" width="245" height="{legend_height}" rx="14" fill="#fffdf7" '
            'fill-opacity="0.92" stroke="#d7ccc8" stroke-width="2"/>'
        )
        legend_svg.append('<text x="620" y="84" font-size="18" font-family="sans-serif" font-weight="700" fill="#37474f">路线分段</text>')
        for position, segment in enumerate(segments):
            y = 110 + position * 30
            legend_svg.append(
                f'<line x1="620" y1="{y}" x2="660" y2="{y}" stroke="{html.escape(segment["color"])}" stroke-width="8" stroke-linecap="round"/>'
                f'<text x="675" y="{y + 6}" font-size="16" font-family="sans-serif" fill="#37474f">{html.escape(segment["name"])}</text>'
            )
    start_x, start_y = canvas_all[0]
    finish_x, finish_y = canvas_all[-1]
    endpoints["start"].update({"role": "start", "track_progress": 0.0, "anchor": {"x": start_x, "y": start_y}})
    endpoints["finish"].update({"role": "finish", "track_progress": 1.0, "anchor": {"x": finish_x, "y": finish_y}})
    if closed:
        endpoint_svg = (
            f'<circle cx="{start_x}" cy="{start_y}" r="12" fill="#2e7d32" stroke="#c62828" stroke-width="5"/>'
            + endpoint_label_svg("start", f'{endpoints["start"]["name"]} / {endpoints["finish"]["name"]}', start_x, start_y, args.width).replace("起点：", "起点/终点：", 1)
        )
    else:
        endpoint_svg = (
            f'<circle cx="{start_x}" cy="{start_y}" r="11" fill="#2e7d32" stroke="#ffffff" stroke-width="3"/>'
            f'<circle cx="{finish_x}" cy="{finish_y}" r="9" fill="#c62828" stroke="#ffffff" stroke-width="3"/>'
            + endpoint_label_svg("start", endpoints["start"]["name"], start_x, start_y, args.width)
            + endpoint_label_svg("finish", endpoints["finish"]["name"], finish_x, finish_y, args.width)
        )
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {args.width} {args.height}" width="{args.width}" height="{args.height}" preserveAspectRatio="xMidYMid meet">
  <rect width="100%" height="100%" fill="#fffdf7"/>
  <path id="route-underlay" d="{route_path}" fill="none" stroke="#fffdf7" stroke-width="15" stroke-linecap="round" stroke-linejoin="round"/>
  {''.join(segment_svg) if segment_svg else f'<path id="route" d="{route_path}" fill="none" stroke="#d84315" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>'}
  {''.join(arrow_layers)}
  {endpoint_svg}
  {''.join(boundary_svg)}
  {''.join(checkpoint_svg)}
  {''.join(legend_svg)}
</svg>
'''
    svg_file.write_text(svg, encoding="utf-8")

    layout = {
        "source": str(source),
        "selected_track_index": selected_index,
        "original_point_count": len(projected),
        "simplified_point_count": len(simplified_indices),
        "simplification_epsilon_m": round(epsilon, 3),
        "closed": closed,
        "canvas": {"width": args.width, "height": args.height, "padding": args.padding},
        "simplified_original_indices": simplified_indices,
        "simplified_points": [{"x": x, "y": y} for x, y in canvas_simplified],
        "simplified_progress": [round(cumulative[index] / cumulative[-1], 8) for index in simplified_indices],
        "svg_path_d": route_path,
        "endpoints": endpoints,
        "checkpoints": checkpoints,
        "boundaries": boundaries,
        "segments": segments,
    }
    json_file.write_text(json.dumps(layout, ensure_ascii=False, indent=2), encoding="utf-8")

    segment_lines = "".join(
        f'- 路段：{segment["name"]}（{segment["start_progress"] * 100:.1f}%—{segment["end_progress"] * 100:.1f}%）\n'
        for segment in segments
    )
    route_type = "闭合路线" if closed else "开放路线"
    fragment = f'''# {source.stem}轨迹几何参考

- SVG 文件：`{svg_file.name}`
- 原始轨迹点：{len(projected)}
- 简化后折点：{len(simplified_indices)}
- 路线类型：{route_type}
- 起点：{endpoints["start"]["name"]}
- 终点：{endpoints["finish"]["name"]}
- 画布：{args.width}×{args.height}
{segment_lines}

## 提示词中的轨迹约束

将 `{svg_file.name}` 及其 PNG 预览作为 P0 最高优先级路线几何参考。严格保留完整轨迹轮廓、全部主要转折、行进顺序、起终点、分段边界和编号锚点。允许水彩化线条，但不得重画、简化、镜像、旋转、非等比拉伸、改变路线类型或调换打卡点顺序；冲突时移动或缩小文字、地标和装饰。

精简 SVG path：

```svg
<path d="{route_path}" fill="none" />
```

> 优先把 SVG 或其 PNG 预览作为图片参考。上述 path 代码只作为文本补充，不能保证生图模型像浏览器一样执行 SVG。
'''
    prompt_file.write_text(fragment, encoding="utf-8")
    print(svg_file)
    print(json_file)
    print(prompt_file)


if __name__ == "__main__":
    main()
