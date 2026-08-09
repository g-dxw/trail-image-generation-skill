#!/usr/bin/env python3
"""Build a reproducible preflight manifest for one route image generation task."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolved_file(path: Path, label: str) -> Path:
    result = path.expanduser().resolve()
    if not result.is_file():
        raise ValueError(f"{label} does not exist: {result}")
    return result


def parse_reference(raw: str) -> dict[str, str]:
    if "=" not in raw:
        raise ValueError("reference must use ROLE=PATH")
    role, raw_path = raw.split("=", 1)
    if role not in {"route_geometry", "real_photo", "ai_scene", "style_reference"}:
        raise ValueError(f"unsupported reference role: {role}")
    path = resolved_file(Path(raw_path), "reference")
    return {"role": role, "path": str(path), "sha256": sha256(path)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--fidelity-mode", choices=("exact", "similar", "free"), default="exact")
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--route-png", type=Path, required=True)
    parser.add_argument("--route-svg", type=Path, required=True)
    parser.add_argument("--layout-json", type=Path, required=True)
    parser.add_argument("--segment-start", type=float, default=0.0)
    parser.add_argument("--segment-end", type=float, default=1.0)
    parser.add_argument("--reference", action="append", default=[], metavar="ROLE=PATH")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if not 0.0 <= args.segment_start < args.segment_end <= 1.0:
        raise SystemExit("segment range must satisfy 0 <= start < end <= 1")

    try:
        prompt = resolved_file(args.prompt_file, "prompt file")
        route_png = resolved_file(args.route_png, "route PNG")
        route_svg = resolved_file(args.route_svg, "route SVG")
        layout_json = resolved_file(args.layout_json, "layout JSON")
        references = [parse_reference(item) for item in args.reference]
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if not any(item["role"] == "route_geometry" and Path(item["path"]) == route_png for item in references):
        references.insert(0, {"role": "route_geometry", "path": str(route_png), "sha256": sha256(route_png)})

    try:
        layout = json.loads(layout_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot read layout JSON: {exc}") from exc

    checkpoints = []
    for checkpoint in layout.get("checkpoints") or []:
        checkpoints.append(
            {
                "number": checkpoint.get("number"),
                "name": checkpoint.get("name"),
                "track_progress": checkpoint.get("track_progress"),
                "anchor": checkpoint.get("anchor"),
            }
        )

    manifest = {
        "schema_version": 1,
        "task_id": args.task_id,
        "fidelity_mode": args.fidelity_mode,
        "prompt_file": str(prompt),
        "prompt_sha256": sha256(prompt),
        "route_reference_png": str(route_png),
        "route_svg": str(route_svg),
        "layout_json": str(layout_json),
        "geometry_sha256": {
            "route_png": sha256(route_png),
            "route_svg": sha256(route_svg),
            "layout_json": sha256(layout_json),
        },
        "route_closed": bool(layout.get("closed")),
        "checkpoint_count": len(checkpoints),
        "checkpoints": checkpoints,
        "segment_start": args.segment_start,
        "segment_end": args.segment_end,
        "references": references,
    }
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
