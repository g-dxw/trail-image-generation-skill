#!/usr/bin/env python3
"""Calculate route intensity for a GPX, KML, or KMZ track."""

from __future__ import annotations

import argparse
import json
import math
import re
import zipfile
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from statistics import fmean, median
from xml.etree import ElementTree as ET

from route_to_svg import load_tracks, remove_consecutive_duplicates


EARTH_RADIUS_M = 6371008.8
SOURCE_KEYS = {
    "distance": "Distance",
    "gain": "ElevationGain",
    "loss": "ElevationLoss",
}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_number(value: object) -> float | None:
    if value is None:
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", str(value).replace(",", ""))
    if not match:
        return None
    try:
        result = float(match.group(0))
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon1, lat1 = map(math.radians, a)
    lon2, lat2 = map(math.radians, b)
    dlon, dlat = lon2 - lon1, lat2 - lat1
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(value)))


def extract_extended_data(xml_bytes: bytes) -> dict[str, str]:
    root = ET.fromstring(xml_bytes)
    result: dict[str, str] = {}
    for element in root.iter():
        if local_name(element.tag) != "Data":
            continue
        key = element.attrib.get("name", "").strip()
        if key not in SOURCE_KEYS.values():
            continue
        value = next(
            ((child.text or "").strip() for child in element if local_name(child.tag) == "value"),
            "",
        )
        if value and key not in result:
            result[key] = value
    return result


def load_extended_data(source: Path) -> dict[str, str]:
    suffix = source.suffix.lower()
    if suffix == ".kmz":
        result: dict[str, str] = {}
        with zipfile.ZipFile(source) as archive:
            for member in archive.infolist():
                if Path(member.filename).suffix.lower() != ".kml":
                    continue
                for key, value in extract_extended_data(archive.read(member)).items():
                    result.setdefault(key, value)
        return result
    if suffix == ".kml":
        return extract_extended_data(source.read_bytes())
    return {}


def moving_median(values: list[float], window: int = 5) -> list[float]:
    if not values:
        return []
    radius = max(0, window // 2)
    return [
        float(median(values[max(0, index - radius) : min(len(values), index + radius + 1)]))
        for index in range(len(values))
    ]


def calculated_metrics(source: Path) -> dict[str, float | None]:
    tracks = load_tracks(source)
    if not tracks:
        return {
            "distance_km": None,
            "gain_m": None,
            "loss_m": None,
            "average_elevation_m": None,
        }
    points = remove_consecutive_duplicates(max(tracks, key=len))
    distance_m = sum(
        haversine_m((start[0], start[1]), (end[0], end[1]))
        for start, end in zip(points, points[1:])
    )
    elevations = [
        float(point[2])
        for point in points
        if point[2] is not None and math.isfinite(float(point[2])) and -500 <= float(point[2]) <= 10000
    ]
    if not elevations:
        return {
            "distance_km": distance_m / 1000,
            "gain_m": None,
            "loss_m": None,
            "average_elevation_m": None,
        }
    smoothed = moving_median(elevations)
    gain = 0.0
    loss = 0.0
    for start, end in zip(smoothed, smoothed[1:]):
        delta = end - start
        if delta > 2.0:
            gain += delta
        elif delta < -2.0:
            loss -= delta
    return {
        "distance_km": distance_m / 1000,
        "gain_m": gain,
        "loss_m": loss,
        "average_elevation_m": fmean(smoothed),
    }


def round_half_up_1(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def classify_intensity(score: float) -> str:
    if score <= 1.5:
        return "休闲强度"
    if score <= 3.0:
        return "初级强度"
    if score <= 5.0:
        return "中级强度"
    if score <= 8.0:
        return "大强度"
    return "超大强度"


def compute_route_intensity(
    *,
    distance_km: float | None,
    gain_m: float | None,
    loss_m: float | None,
    average_elevation_m: float | None,
    sources: dict[str, str] | None = None,
    warnings: list[str] | None = None,
) -> dict:
    sources = sources or {}
    warnings = list(warnings or [])
    inputs = {
        "distance_km": {"value": distance_km, "source": sources.get("distance_km", "unknown")},
        "elevation_gain_m": {"value": gain_m, "source": sources.get("gain_m", "unknown")},
        "elevation_loss_m": {"value": loss_m, "source": sources.get("loss_m", "unknown")},
        "average_elevation_m": {
            "value": average_elevation_m,
            "source": sources.get("average_elevation_m", "unknown"),
        },
    }
    base = {
        "formula": {
            "estimated_load": "4 + distance_km/10*0.5 + elevation_gain_m/1000*0.5",
            "altitude_factor": "1 + average_elevation_m/5500",
            "route_intensity": "(distance_km/10 + elevation_gain_m/1000 + elevation_loss_m/1000) * estimated_load_kg/10 * altitude_factor",
        },
        "inputs": inputs,
        "warnings": warnings,
    }
    if distance_km is None or (gain_m is None and loss_m is None):
        if distance_km is None:
            warnings.append("缺少距离，无法计算路线强度。")
        if gain_m is None and loss_m is None:
            warnings.append("爬升和下降均不可用，无法计算路线强度。")
        return {**base, "status": "insufficient_data", "raw_score": None, "score": None, "level": None}

    if gain_m is None:
        gain_m = 0.0
        inputs["elevation_gain_m"]["value"] = 0.0
        warnings.append("缺少爬升，公式中暂按 0 米计算。")
    if loss_m is None:
        loss_m = 0.0
        inputs["elevation_loss_m"]["value"] = 0.0
        warnings.append("缺少下降，公式中暂按 0 米计算。")

    estimated_load = 4 + distance_km / 10 * 0.5 + gain_m / 1000 * 0.5
    if average_elevation_m is None:
        altitude_factor = 1.0
        warnings.append("缺少平均海拔，海拔强度系数暂按 1.0。")
    else:
        altitude_factor = 1 + average_elevation_m / 5500
    raw_score = (
        distance_km / 10 + gain_m / 1000 + loss_m / 1000
    ) * estimated_load / 10 * altitude_factor
    score = round_half_up_1(raw_score)
    return {
        **base,
        "status": "ok",
        "estimated_load_kg": round(estimated_load, 4),
        "altitude_factor": round(altitude_factor, 6),
        "raw_score": round(raw_score, 6),
        "score": score,
        "level": classify_intensity(score),
    }


def choose_value(
    override: float | None,
    source_value: float | None,
    calculated_value: float | None,
) -> tuple[float | None, str]:
    if override is not None:
        return override, "cli_override"
    if source_value is not None:
        return source_value, "source_metadata"
    if calculated_value is not None:
        return calculated_value, "calculated_track"
    return None, "missing"


def calculate_for_source(
    source: Path,
    *,
    distance_km: float | None = None,
    gain_m: float | None = None,
    loss_m: float | None = None,
) -> dict:
    source = source.resolve()
    calculated = calculated_metrics(source)
    extended = load_extended_data(source)

    source_distance = parse_number(extended.get(SOURCE_KEYS["distance"]))
    if source_distance is not None and source_distance > 100:
        source_distance /= 1000
    source_gain = parse_number(extended.get(SOURCE_KEYS["gain"]))
    source_loss = parse_number(extended.get(SOURCE_KEYS["loss"]))

    chosen_distance, distance_source = choose_value(distance_km, source_distance, calculated["distance_km"])
    chosen_gain, gain_source = choose_value(gain_m, source_gain, calculated["gain_m"])
    chosen_loss, loss_source = choose_value(loss_m, source_loss, calculated["loss_m"])
    average_elevation = calculated["average_elevation_m"]
    warnings = [
        "轨迹计算爬升和下降使用中值滤波与 2 米死区，来源应用记录存在时优先采用来源记录。"
    ]
    result = compute_route_intensity(
        distance_km=chosen_distance,
        gain_m=chosen_gain,
        loss_m=chosen_loss,
        average_elevation_m=average_elevation,
        sources={
            "distance_km": distance_source,
            "gain_m": gain_source,
            "loss_m": loss_source,
            "average_elevation_m": "calculated_track" if average_elevation is not None else "missing",
        },
        warnings=warnings,
    )
    return {"source_file": str(source), **result}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("route", type=Path, help="GPX, KML, or KMZ route file")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--distance-km", type=float)
    parser.add_argument("--gain-m", type=float)
    parser.add_argument("--loss-m", type=float)
    args = parser.parse_args()

    result = calculate_for_source(
        args.route,
        distance_km=args.distance_km,
        gain_m=args.gain_m,
        loss_m=args.loss_m,
    )
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{args.route.stem}-路线强度.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output_file)


if __name__ == "__main__":
    main()
