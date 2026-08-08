#!/usr/bin/env python3
"""Inspect a KMZ, extract embedded photos, and emit a JSON route summary."""

from __future__ import annotations

import argparse
import json
import math
import re
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from route_intensity import calculate_for_source
from detect_checkpoint_candidates import detect_source as detect_checkpoint_candidates


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
REVIEW_METADATA_KEYS = {
    "TrackId",
    "TrackTags",
    "BeginTime",
    "EndTime",
    "TimeUsed",
    "PauseTime",
    "PosStartName",
    "PosEndName",
    "Distance",
    "ElevationGain",
    "ElevationLoss",
    "SportAvgSpeed",
    "Privacy",
}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def safe_filename(name: str) -> str:
    value = Path(name).name
    value = re.sub(r"[^\w.()\-\u4e00-\u9fff]+", "_", value)
    return value or "asset"


def unique_path(folder: Path, filename: str) -> Path:
    candidate = folder / filename
    if not candidate.exists():
        return candidate
    stem, suffix = candidate.stem, candidate.suffix
    index = 2
    while True:
        candidate = folder / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon1, lat1 = map(math.radians, a)
    lon2, lat2 = map(math.radians, b)
    dlon, dlat = lon2 - lon1, lat2 - lat1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6371008.8 * math.asin(min(1.0, math.sqrt(h)))


def parse_coordinates(text: str) -> list[tuple[float, float, float | None]]:
    points = []
    for token in text.replace("\n", " ").split():
        values = token.split(",")
        if len(values) < 2:
            continue
        try:
            lon, lat = float(values[0]), float(values[1])
            ele = float(values[2]) if len(values) > 2 and values[2] else None
        except ValueError:
            continue
        points.append((lon, lat, ele))
    return points


def inspect_kml(xml_bytes: bytes) -> dict:
    root = ET.fromstring(xml_bytes)
    gx_points: list[tuple[float, float, float | None]] = []
    regular_points: list[tuple[float, float, float | None]] = []
    times: list[str] = []
    names: list[str] = []
    extended: dict[str, str] = {}

    for element in root.iter():
        name = local_name(element.tag)
        text = (element.text or "").strip()
        if name == "coord" and text:
            values = text.split()
            if len(values) >= 2:
                try:
                    gx_points.append((float(values[0]), float(values[1]), float(values[2]) if len(values) > 2 else None))
                except ValueError:
                    pass
        elif name == "coordinates" and text:
            regular_points.extend(parse_coordinates(text))
        elif name == "when" and text:
            times.append(text)
        elif name == "Placemark":
            child_name = next(((child.text or "").strip() for child in element if local_name(child.tag) == "name"), "")
            if child_name:
                names.append(child_name)
        elif name == "Data":
            key = element.attrib.get("name", "").strip()
            value = next(((child.text or "").strip() for child in element if local_name(child.tag) == "value"), "")
            if key in REVIEW_METADATA_KEYS and value:
                extended[key] = value

    points = gx_points or regular_points
    distance = sum(haversine_m((a[0], a[1]), (b[0], b[1])) for a, b in zip(points, points[1:]))
    elevations = [point[2] for point in points if point[2] is not None]
    ascent = sum(max(0.0, b - a) for a, b in zip(elevations, elevations[1:]))
    descent = sum(max(0.0, a - b) for a, b in zip(elevations, elevations[1:]))
    parsed_times = [parsed for parsed in (parse_time(value) for value in times) if parsed]
    duration = (parsed_times[-1] - parsed_times[0]).total_seconds() if len(parsed_times) >= 2 else None

    return {
        "track_points": len(points),
        "start_coordinate": list(points[0]) if points else None,
        "end_coordinate": list(points[-1]) if points else None,
        "start_time": times[0] if times else None,
        "end_time": times[-1] if times else None,
        "duration_seconds": duration,
        "calculated_distance_km": round(distance / 1000, 3),
        "calculated_ascent_m": round(ascent, 2) if elevations else None,
        "calculated_descent_m": round(descent, 2) if elevations else None,
        "minimum_elevation_m": round(min(elevations), 2) if elevations else None,
        "maximum_elevation_m": round(max(elevations), 2) if elevations else None,
        "placemark_names": names,
        "extended_data": extended,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kmz", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    source = args.kmz.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    photo_dir = output_dir / f"{source.stem}-照片"
    photo_dir.mkdir(parents=True, exist_ok=True)

    kml_summaries = []
    extracted_photos = []
    with zipfile.ZipFile(source) as archive:
        for member in archive.infolist():
            suffix = Path(member.filename).suffix.lower()
            if suffix == ".kml":
                summary = inspect_kml(archive.read(member))
                summary["member"] = member.filename
                kml_summaries.append(summary)
            elif suffix in IMAGE_EXTENSIONS and not member.is_dir():
                destination = unique_path(photo_dir, safe_filename(member.filename))
                destination.write_bytes(archive.read(member))
                extracted_photos.append(destination.name)

    result = {
        "source_kmz": str(source),
        "kml_files": len(kml_summaries),
        "photos_extracted": len(extracted_photos),
        "photo_directory": str(photo_dir),
        "photos": extracted_photos,
        "tracks": kml_summaries,
        "notes": [
            "Calculated ascent and descent use raw consecutive elevation samples and may differ from the source app.",
            "Treat all values as review candidates until the user confirms them.",
        ],
    }
    result["route_intensity"] = calculate_for_source(source)
    # Keep candidate-point discovery in the same machine-readable summary so
    # review generation can prioritize photo/geometry hotspots without making
    # a formal landmark-name inference.
    try:
        result["checkpoint_candidates"] = detect_checkpoint_candidates(source)
        result["photo_analysis_policy"] = result["checkpoint_candidates"].get("photo_analysis_policy", {})
        result["photo_records"] = result["checkpoint_candidates"].get("photos", [])
    except (OSError, ValueError, ET.ParseError, zipfile.BadZipFile) as exc:
        result["checkpoint_candidates"] = {
            "candidates": [],
            "warnings": [f"candidate_detection_failed: {exc}"],
        }
    output_file = output_dir / f"{source.stem}-轨迹摘要.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output_file)


if __name__ == "__main__":
    main()
