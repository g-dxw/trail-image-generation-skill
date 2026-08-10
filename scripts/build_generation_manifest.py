#!/usr/bin/env python3
"""Build a reproducible preflight manifest for one route image generation task."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from provider_config import load_capability_report, validate_execution_against_report


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
    if role not in {"route_geometry", "landmark_reference_board", "real_photo", "ai_scene", "style_reference"}:
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
    parser.add_argument("--landmark-board", type=Path)
    parser.add_argument("--landmark-board-sidecar", type=Path)
    parser.add_argument("--source-material", action="append", default=[], type=Path)
    parser.add_argument("--provider-max-reference-images", type=int, required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--selection-method", choices=("configured", "runtime_tool_schema", "user_approved_sample"), required=True)
    parser.add_argument("--requested-quality", default="provider-default")
    parser.add_argument("--provider-cost-class", choices=("budget", "standard", "premium", "unknown"), default="unknown")
    parser.add_argument("--provider-quality-class", choices=("final", "user_approved_for_final", "unknown"), default="unknown")
    parser.add_argument("--capability-report", type=Path, required=True)
    parser.add_argument("--allow-route-only-fallback", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if not 0.0 <= args.segment_start < args.segment_end <= 1.0:
        raise SystemExit("segment range must satisfy 0 <= start < end <= 1")
    if not 0 <= args.provider_max_reference_images <= 16:
        raise SystemExit("provider max reference images must be in 0..16")
    if args.fidelity_mode == "exact" and args.provider_max_reference_images < 1:
        raise SystemExit("exact mode requires a provider that accepts at least one reference image")
    if bool(args.landmark_board) != bool(args.landmark_board_sidecar):
        raise SystemExit("--landmark-board and --landmark-board-sidecar must be provided together")

    try:
        prompt = resolved_file(args.prompt_file, "prompt file")
        route_png = resolved_file(args.route_png, "route PNG")
        route_svg = resolved_file(args.route_svg, "route SVG")
        layout_json = resolved_file(args.layout_json, "layout JSON")
        legacy_references = [parse_reference(item) for item in args.reference]
        source_materials = [resolved_file(item, "source material") for item in args.source_material]
        landmark_board = resolved_file(args.landmark_board, "landmark board") if args.landmark_board else None
        landmark_sidecar = resolved_file(args.landmark_board_sidecar, "landmark board sidecar") if args.landmark_board_sidecar else None
        capability_report = resolved_file(args.capability_report, "capability report")
        report = load_capability_report(capability_report)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    forbidden_legacy = [item for item in legacy_references if item["role"] in {"real_photo", "ai_scene", "style_reference"}]
    if forbidden_legacy:
        raise SystemExit("individual photo references are no longer uploaded; build a landmark reference board first")
    legacy_boards = [item for item in legacy_references if item["role"] == "landmark_reference_board"]
    if len(legacy_boards) > 1:
        raise SystemExit("only one landmark reference board is allowed")
    if legacy_boards:
        legacy_board_path = Path(legacy_boards[0]["path"])
        if landmark_board and legacy_board_path != landmark_board:
            raise SystemExit("legacy landmark board reference conflicts with --landmark-board")
        if not landmark_board:
            landmark_board = legacy_board_path
            raise SystemExit("legacy landmark board references also require --landmark-board-sidecar")

    report_errors = validate_execution_against_report(
        report,
        provider=args.provider,
        model=args.model,
        purpose="route_final",
        capacity=args.provider_max_reference_images,
        requested_quality=args.requested_quality,
        cost_class=args.provider_cost_class,
        quality_class=args.provider_quality_class,
    )
    if report_errors:
        raise SystemExit("final capability validation failed:\n- " + "\n- ".join(report_errors))

    actual_uploads = [{"role": "route_geometry", "path": str(route_png), "sha256": sha256(route_png)}]
    reference_mode = "route_only"
    omitted_landmark_board = None
    if landmark_board:
        if args.provider_max_reference_images >= 2:
            actual_uploads.append({"role": "landmark_reference_board", "path": str(landmark_board), "sha256": sha256(landmark_board)})
            reference_mode = "two_image"
        elif args.allow_route_only_fallback:
            reference_mode = "route_only_fallback"
            omitted_landmark_board = {"path": str(landmark_board), "sha256": sha256(landmark_board)}
        else:
            raise SystemExit("provider accepts only one reference image; explicitly approve --allow-route-only-fallback or choose another provider")

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
        "schema_version": 2,
        "generation_purpose": "route_final",
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
        "reference_mode": reference_mode,
        "provider_max_reference_images": args.provider_max_reference_images,
        "provider": args.provider,
        "model": args.model,
        "selection_method": args.selection_method,
        "requested_quality": args.requested_quality,
        "provider_cost_class": args.provider_cost_class,
        "provider_quality_class": args.provider_quality_class,
        "capability_report": str(capability_report),
        "capability_report_sha256": sha256(capability_report),
        "actual_uploads": actual_uploads,
        "references": actual_uploads,
        "landmark_board": str(landmark_board) if landmark_board else None,
        "landmark_board_sidecar": str(landmark_sidecar) if landmark_sidecar else None,
        "landmark_board_sidecar_sha256": sha256(landmark_sidecar) if landmark_sidecar else None,
        "omitted_landmark_board": omitted_landmark_board,
        "source_materials": [{"path": str(path), "sha256": sha256(path)} for path in source_materials],
    }
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
