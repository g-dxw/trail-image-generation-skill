#!/usr/bin/env python3
"""Detect high-value checkpoint candidates from GPX/KML/KMZ tracks.

The detector is intentionally evidence-oriented: geometry can mark a place as
worth reviewing, but never supplies a formal landmark name on its own.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET


EARTH_RADIUS_M = 6_371_008.8
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


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
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


def parse_coordinates(text: str) -> list[tuple[float, float, float | None]]:
    result = []
    for token in text.replace("\n", " ").split():
        values = token.split(",")
        if len(values) < 2:
            continue
        try:
            result.append((float(values[0]), float(values[1]), float(values[2]) if len(values) > 2 else None))
        except ValueError:
            continue
    return result


def parse_gpx(path: Path) -> tuple[list[dict], list[dict], list[str]]:
    root = ET.parse(path).getroot()
    track = []
    for point in root.iter():
        if local_name(point.tag) != "trkpt":
            continue
        track.append({
            "lon": float(point.attrib["lon"]),
            "lat": float(point.attrib["lat"]),
            "ele": next((float(c.text) for c in point if local_name(c.tag) == "ele" and c.text), None),
            "time": next((parse_time(c.text) for c in point if local_name(c.tag) == "time" and c.text), None),
        })
    return track, [], []


def parse_kml_bytes(xml_bytes: bytes) -> tuple[list[dict], list[dict], list[str]]:
    root = ET.fromstring(xml_bytes)
    track_sequences: list[list[dict]] = []
    photos: list[dict] = []
    named: list[str] = []

    for placemark in (e for e in root.iter() if local_name(e.tag) == "Placemark"):
        name = next(((c.text or "").strip() for c in placemark if local_name(c.tag) == "name"), "")
        if name and name not in {"起点", "终点"} and not name.startswith("导航线片段"):
            named.append(name)
        coords = []
        for child in placemark.iter():
            if local_name(child.tag) == "coordinates" and (child.text or "").strip():
                coords.extend(parse_coordinates(child.text or ""))
        times = [parse_time(c.text) for c in placemark.iter() if local_name(c.tag) == "when" and c.text]
        if len(coords) > 1:
            track_sequences.append([
                {"lon": p[0], "lat": p[1], "ele": p[2], "time": times[i] if i < len(times) else None}
                for i, p in enumerate(coords)
            ])
        elif len(coords) == 1:
            description = " ".join((c.text or "") for c in placemark.iter() if local_name(c.tag) == "description")
            data_values = {
                d.attrib.get("name", ""): next(((v.text or "").strip() for v in d if local_name(v.tag) == "value"), "")
                for d in placemark.iter() if local_name(d.tag) == "Data"
            }
            file_id = data_values.get("FileId", "")
            has_embedded_or_linked_image = "<img" in description or (file_id and file_id != "0")
            if has_embedded_or_linked_image:
                label_source = "kml_name" if name else ("photo_label" if data_values.get("description") else None)
                photos.append({
                    "lon": coords[0][0], "lat": coords[0][1], "ele": coords[0][2],
                    "time": times[0] if times else None,
                    "name": name or (f"照片{file_id}" if file_id else "未命名照片"),
                    "file_id": file_id,
                    "label_source": label_source,
                    "analysis_status": "labeled" if label_source else "unlabeled",
                })

    # The route is normally the longest LineString in a recorded KML.
    track = max(track_sequences, key=len, default=[])
    return track, photos, sorted(set(named))


def parse_source(source: Path) -> tuple[list[dict], list[dict], list[str]]:
    suffix = source.suffix.lower()
    if suffix == ".gpx":
        return parse_gpx(source)
    if suffix == ".kml":
        return parse_kml_bytes(source.read_bytes())
    if suffix == ".kmz":
        with zipfile.ZipFile(source) as archive:
            kmls = [m for m in archive.infolist() if m.filename.lower().endswith(".kml")]
            if not kmls:
                return [], [], []
            return parse_kml_bytes(archive.read(kmls[0]))
    raise ValueError(f"Unsupported route format: {source.suffix}")


def cumulative_distances(track: list[dict]) -> list[float]:
    values = [0.0]
    for a, b in zip(track, track[1:]):
        values.append(values[-1] + haversine_m((a["lon"], a["lat"]), (b["lon"], b["lat"])))
    return values


def nearest_track_index(photo: dict, track: list[dict]) -> tuple[int, float]:
    distances = [haversine_m((photo["lon"], photo["lat"]), (p["lon"], p["lat"])) for p in track]
    index = min(range(len(distances)), key=distances.__getitem__)
    return index, distances[index]


def _angle(a: dict, b: dict) -> float:
    dx = (b["lon"] - a["lon"]) * math.cos(math.radians((a["lat"] + b["lat"]) / 2))
    dy = b["lat"] - a["lat"]
    return math.atan2(dy, dx)


def _norm(value: float) -> float:
    return max(0.0, min(1.0, value))


def detect_candidates(
    track: list[dict],
    photos: list[dict] | None = None,
    named_points: list[dict] | None = None,
    confirmed_points: list[dict] | None = None,
    *,
    spatial_radius_m: float = 35.0,
    progress_window_m: float = 90.0,
    min_photo_count: int = 2,
    min_score: float = 0.45,
    analysis_mode: str = "metadata_labeled_first",
    selected_photo_ids: set[str] | None = None,
) -> dict:
    photos = photos or []
    named_points = named_points or []
    confirmed_points = confirmed_points or []
    selected_photo_ids = selected_photo_ids or set()
    if len(track) < 3:
        return {"candidates": [], "thresholds": locals_thresholds(spatial_radius_m, progress_window_m, min_photo_count, min_score), "warnings": ["insufficient_track_points"]}

    cumulative = cumulative_distances(track)
    total = cumulative[-1]
    if total <= 0:
        return {"candidates": [], "thresholds": locals_thresholds(spatial_radius_m, progress_window_m, min_photo_count, min_score), "warnings": ["zero_track_distance"]}

    matched_photos = []
    for photo in photos:
        index, distance = nearest_track_index(photo, track)
        item = dict(photo)
        photo_id = item.get("name") or item.get("file_id") or f"photo-{len(matched_photos) + 1}"
        label_source = item.get("label_source")
        is_selected = photo_id in selected_photo_ids or item.get("file_id") in selected_photo_ids
        if analysis_mode == "all":
            analysis_status = "selected"
        elif analysis_mode == "selected":
            analysis_status = "selected" if is_selected else "skipped"
        else:
            analysis_status = "labeled" if label_source else "unlabeled"
        item.update({"track_index": index, "track_progress": cumulative[index] / total, "match_distance_m": round(distance, 2)})
        item["photo_id"] = photo_id
        item["analysis_status"] = analysis_status
        item["label_source"] = label_source
        if isinstance(item.get("time"), datetime):
            item["time"] = item["time"].isoformat()
        matched_photos.append(item)

    raw = []
    for i, point in enumerate(track):
        lo = i
        while lo > 0 and cumulative[i] - cumulative[lo - 1] <= progress_window_m:
            lo -= 1
        hi = i
        while hi + 1 < len(track) and cumulative[hi + 1] - cumulative[i] <= progress_window_m:
            hi += 1
        nearby = [j for j in range(lo, hi + 1) if haversine_m((point["lon"], point["lat"]), (track[j]["lon"], track[j]["lat"])) <= spatial_radius_m]
        local_path = cumulative[hi] - cumulative[lo]
        displacement = haversine_m((track[lo]["lon"], track[lo]["lat"]), (track[hi]["lon"], track[hi]["lat"]))
        return_ratio = local_path / max(displacement, spatial_radius_m)
        turn_count = 0
        for j in range(max(lo + 1, 1), min(hi, len(track) - 1)):
            before, after = _angle(track[j - 1], track[j]), _angle(track[j], track[j + 1])
            delta = abs((after - before + math.pi) % (2 * math.pi) - math.pi)
            if delta >= math.radians(60):
                turn_count += 1
        congestion = _norm((len(nearby) - 3) / 12)
        backtracking = _norm((return_ratio - 1.2) / 3.0)
        direction_noise = _norm(turn_count / 5)
        local_backtracking = max(backtracking, direction_noise)
        local_photos = [p for p in matched_photos if abs(cumulative[i] - cumulative[p["track_index"]]) <= progress_window_m or haversine_m((point["lon"], point["lat"]), (p["lon"], p["lat"])) <= spatial_radius_m]
        photo_density = _norm(len(local_photos) / max(min_photo_count * 2, 1))
        dwell = 0.0
        timed = [track[j]["time"] for j in nearby if track[j].get("time")]
        if len(timed) >= 2:
            dwell = _norm((max(timed) - min(timed)).total_seconds() / 600)
        source_named = 0.0
        source_name = ""
        for item in named_points:
            if haversine_m((point["lon"], point["lat"]), (item["lon"], item["lat"])) <= spatial_radius_m:
                source_named, source_name = 1.0, item.get("name", "")
                break
        score = 0.25 * congestion + 0.25 * local_backtracking + 0.20 * dwell + 0.30 * photo_density
        if source_named:
            score = max(score, 0.85)
        raw.append({"index": i, "score": score, "signals": {"track_congestion": congestion, "local_backtracking": local_backtracking, "dwell": dwell, "photo_density": photo_density, "source_named": source_named, "user_confirmed": 0.0}, "photo_indices": [p["track_index"] for p in local_photos], "source_name": source_name})

    selected = [x for x in raw if x["score"] >= min_score or x["signals"]["source_named"]]
    clusters: list[list[dict]] = []
    for item in selected:
        if not clusters or cumulative[item["index"]] - cumulative[clusters[-1][-1]["index"]] > progress_window_m * 1.5:
            clusters.append([item])
        else:
            clusters[-1].append(item)

    candidates = []
    for cluster in clusters:
        best = max(cluster, key=lambda x: x["score"])
        index = best["index"]
        point = track[index]
        # Keep repeated photos at the same coordinate in the count: repeated
        # captures are themselves evidence of a high-value stop. The raw
        # matched records retain their coordinates/timestamps for later
        # de-duplication or advanced review.
        cluster_photos = sorted(
            [p for p in matched_photos if any(p["track_index"] in x["photo_indices"] for x in cluster)],
            key=lambda p: p["track_progress"],
        )
        name = best["source_name"] or ("照片密集区域（候选）" if best["signals"]["photo_density"] >= 0.5 else "局部折返候选点")
        def confirmed_is_near(item: dict) -> bool:
            coordinate = item.get("coordinate")
            if coordinate and len(coordinate) >= 2:
                return haversine_m((point["lon"], point["lat"]), (coordinate[0], coordinate[1])) <= spatial_radius_m
            if "lon" in item and "lat" in item:
                return haversine_m((point["lon"], point["lat"]), (item["lon"], item["lat"])) <= spatial_radius_m
            progress = item.get("track_progress", item.get("progress"))
            return progress is not None and abs(float(progress) - cumulative[index] / total) <= progress_window_m / total

        nearby_confirmed = next((c for c in confirmed_points if confirmed_is_near(c)), None)
        if nearby_confirmed:
            name = nearby_confirmed.get("name", name)
            best["signals"]["user_confirmed"] = 1.0
        evidence = []
        if best["signals"]["photo_density"] >= 0.5: evidence.append("照片密集")
        if best["signals"]["track_congestion"] >= 0.5: evidence.append("轨迹异常聚集")
        if best["signals"]["local_backtracking"] >= 0.5: evidence.append("局部折返")
        if best["signals"]["dwell"] >= 0.5: evidence.append("明显停留")
        if best["signals"]["source_named"]: evidence.append("来源命名")
        hotspot_only = []
        for photo in cluster_photos:
            if photo["analysis_status"] == "unlabeled" and best["score"] >= min_score:
                photo["analysis_status"] = "hotspot_only"
                photo["hotspot_signals"] = evidence
                hotspot_only.append(photo)
        labeled_count = sum(1 for photo in cluster_photos if photo["analysis_status"] in {"labeled", "selected"})
        candidates.append({
            "track_progress": round(cumulative[index] / total, 6),
            "coordinate": [point["lon"], point["lat"]],
            "elevation_m": point.get("ele"),
            "score": round(best["score"], 6),
            "signals": {k: round(v, 6) for k, v in best["signals"].items()},
            "photo_count": len(cluster_photos),
            "photos": [p.get("name") or p.get("file_id") or f"photo-{n+1}" for n, p in enumerate(cluster_photos)],
            "photo_ids": [p["photo_id"] for p in cluster_photos],
            "labeled_photo_count": labeled_count,
            "hotspot_photo_count": len(hotspot_only),
            "temporary_name": name,
            "evidence": evidence,
            "review_priority": "high" if best["score"] >= 0.7 or best["signals"]["source_named"] or len(cluster_photos) >= min_photo_count * 2 else "normal",
            "source_named": bool(best["signals"]["source_named"]),
            "user_confirmed": bool(best["signals"]["user_confirmed"]),
        })
    candidates.sort(key=lambda x: x["track_progress"])
    for number, candidate in enumerate(candidates, start=1):
        candidate["number"] = number
    labeled_photo_count = sum(1 for photo in matched_photos if photo["analysis_status"] in {"labeled", "selected"})
    hotspot_photo_count = sum(1 for photo in matched_photos if photo["analysis_status"] == "hotspot_only")
    candidate_group_count = sum(1 for candidate in candidates if candidate["hotspot_photo_count"] > 0)
    return {
        "candidates": candidates,
        "matched_photos": matched_photos,
        "photos": matched_photos,
        "photo_analysis_policy": {
            "mode": analysis_mode,
            "labeled_photo_count": labeled_photo_count,
            "unlabeled_photo_count": sum(1 for photo in matched_photos if photo.get("label_source") is None),
            "candidate_group_count": candidate_group_count,
            "hotspot_photo_count": hotspot_photo_count,
            "unlabeled_visual_analysis": "skipped_by_default" if analysis_mode == "metadata_labeled_first" else analysis_mode,
        },
        "thresholds": locals_thresholds(spatial_radius_m, progress_window_m, min_photo_count, min_score),
        "warnings": [],
    }


def locals_thresholds(spatial_radius_m: float, progress_window_m: float, min_photo_count: int, min_score: float) -> dict:
    return {"spatial_radius_m": spatial_radius_m, "progress_window_m": progress_window_m, "min_photo_count": min_photo_count, "min_score": min_score}


def detect_source(source: Path, **kwargs) -> dict:
    track, photos, names = parse_source(source)
    # Named Placemark coordinates are parsed separately for reliable matching.
    named_points = []
    if source.suffix.lower() in {".kml", ".kmz"}:
        data = source.read_bytes() if source.suffix.lower() == ".kml" else None
        if source.suffix.lower() == ".kmz":
            with zipfile.ZipFile(source) as archive:
                member = next((m for m in archive.infolist() if m.filename.lower().endswith(".kml")), None)
                data = archive.read(member) if member else b""
        root = ET.fromstring(data or b"<kml/>")
        for placemark in (e for e in root.iter() if local_name(e.tag) == "Placemark"):
            name = next(((c.text or "").strip() for c in placemark if local_name(c.tag) == "name"), "")
            coords = next((parse_coordinates(c.text or "") for c in placemark.iter() if local_name(c.tag) == "coordinates" and (c.text or "").strip()), [])
            if name and len(coords) == 1 and name not in {"起点", "终点"}:
                named_points.append({"name": name, "lon": coords[0][0], "lat": coords[0][1]})
    result = detect_candidates(track, photos, named_points, **kwargs)
    result["source"] = str(source.resolve())
    result["track_points"] = len(track)
    result["photo_count"] = len(photos)
    return result


def parse_source(source: Path) -> tuple[list[dict], list[dict], list[str]]:
    if source.suffix.lower() == ".gpx":
        return parse_gpx(source)
    if source.suffix.lower() == ".kml":
        return parse_kml_bytes(source.read_bytes())
    if source.suffix.lower() == ".kmz":
        with zipfile.ZipFile(source) as archive:
            member = next((m for m in archive.infolist() if m.filename.lower().endswith(".kml")), None)
            return parse_kml_bytes(archive.read(member)) if member else ([], [], [])
    raise ValueError(f"Unsupported route format: {source.suffix}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--spatial-radius-m", type=float, default=35.0)
    parser.add_argument("--progress-window-m", type=float, default=90.0)
    parser.add_argument("--min-photo-count", type=int, default=2)
    parser.add_argument("--min-score", type=float, default=0.45)
    parser.add_argument("--confirmed-json", type=Path, help="Optional confirmed checkpoint JSON used for proximity merge")
    parser.add_argument("--analysis-mode", choices=("metadata_labeled_first", "all", "selected"), default="metadata_labeled_first")
    parser.add_argument("--photo-ids", help="Comma-separated photo names or FileIds to explicitly analyze in selected mode")
    args = parser.parse_args()
    confirmed = []
    if args.confirmed_json:
        payload = json.loads(args.confirmed_json.read_text(encoding="utf-8"))
        confirmed = payload.get("checkpoints", payload if isinstance(payload, list) else [])
    photo_ids = {value.strip() for value in (args.photo_ids or "").split(",") if value.strip()}
    result = detect_source(args.source, confirmed_points=confirmed, analysis_mode=args.analysis_mode, selected_photo_ids=photo_ids, spatial_radius_m=args.spatial_radius_m, progress_window_m=args.progress_window_m, min_photo_count=args.min_photo_count, min_score=args.min_score)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
