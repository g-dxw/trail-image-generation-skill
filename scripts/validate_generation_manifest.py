#!/usr/bin/env python3
"""Validate that a route-generation manifest still matches its approved inputs."""

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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()

    try:
        manifest = json.loads(args.manifest.expanduser().resolve().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot read manifest: {exc}") from exc

    errors: list[str] = []
    fidelity = manifest.get("fidelity_mode")
    if fidelity not in {"exact", "similar", "free"}:
        errors.append("invalid fidelity_mode")

    required_paths = {
        "prompt_file": manifest.get("prompt_file"),
        "route_reference_png": manifest.get("route_reference_png"),
        "route_svg": manifest.get("route_svg"),
        "layout_json": manifest.get("layout_json"),
    }
    resolved: dict[str, Path] = {}
    for label, raw_path in required_paths.items():
        if not raw_path:
            errors.append(f"missing {label}")
            continue
        path = Path(raw_path).expanduser().resolve()
        resolved[label] = path
        if not path.is_file():
            errors.append(f"missing file for {label}: {path}")

    start = manifest.get("segment_start")
    end = manifest.get("segment_end")
    if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or not 0.0 <= start < end <= 1.0:
        errors.append("segment range must satisfy 0 <= start < end <= 1")

    if "prompt_file" in resolved and resolved["prompt_file"].is_file():
        prompt = resolved["prompt_file"].read_text(encoding="utf-8")
        if sha256(resolved["prompt_file"]) != manifest.get("prompt_sha256"):
            errors.append("prompt SHA-256 changed after manifest creation")
        if "[GEOMETRY_LOCK_BEGIN]" not in prompt or "[GEOMETRY_LOCK_END]" not in prompt:
            errors.append("prompt lacks the geometry lock block")
        if "[TEXT_LOCK_BEGIN]" not in prompt or "[TEXT_LOCK_END]" not in prompt:
            errors.append("prompt lacks the stage-4 text lock block")
        for required_label in ("参考图角色：", "负面约束：", "验收清单："):
            if required_label not in prompt:
                errors.append(f"prompt lacks completeness field: {required_label}")
        for forbidden_shorthand in ("同上", "沿用共享设置", "参考前文", "按核对单执行", "...", "……"):
            if forbidden_shorthand in prompt:
                errors.append(f"prompt contains forbidden shorthand: {forbidden_shorthand}")
        if fidelity == "exact":
            if "P0" not in prompt and "最高优先级" not in prompt:
                errors.append("exact prompt lacks highest-priority geometry wording")
            if "禁止重画" not in prompt:
                errors.append("exact prompt lacks no-redraw wording")

    hashes = manifest.get("geometry_sha256") or {}
    for label, manifest_key in (("route_reference_png", "route_png"), ("route_svg", "route_svg"), ("layout_json", "layout_json")):
        path = resolved.get(label)
        if path and path.is_file() and sha256(path) != hashes.get(manifest_key):
            errors.append(f"{label} SHA-256 changed after manifest creation")

    references = manifest.get("references") or []
    route_png = resolved.get("route_reference_png")
    matched_route_reference = False
    for reference in references:
        raw_path = reference.get("path")
        role = reference.get("role")
        if not raw_path:
            errors.append("reference missing path")
            continue
        path = Path(raw_path).expanduser().resolve()
        if not path.is_file():
            errors.append(f"reference file missing: {path}")
            continue
        if sha256(path) != reference.get("sha256"):
            errors.append(f"reference SHA-256 changed: {path}")
        if role == "route_geometry" and route_png and path == route_png:
            matched_route_reference = True
    if fidelity == "exact" and not matched_route_reference:
        errors.append("exact mode requires route PNG in references with role route_geometry")

    layout_path = resolved.get("layout_json")
    if layout_path and layout_path.is_file():
        try:
            layout = json.loads(layout_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid layout JSON: {exc}")
        else:
            layout_checkpoints = layout.get("checkpoints") or []
            manifest_checkpoints = manifest.get("checkpoints") or []
            if manifest.get("checkpoint_count") != len(layout_checkpoints):
                errors.append("checkpoint_count differs from layout JSON")
            expected = [
                (item.get("number"), item.get("name"), item.get("track_progress"), item.get("anchor"))
                for item in layout_checkpoints
            ]
            actual = [
                (item.get("number"), item.get("name"), item.get("track_progress"), item.get("anchor"))
                for item in manifest_checkpoints
            ]
            if actual != expected:
                errors.append("checkpoint order or anchors differ from layout JSON")
            if fidelity == "exact" and not layout.get("simplified_progress"):
                errors.append("exact mode layout lacks simplified_progress; rerun route_to_svg.py")

    if errors:
        raise SystemExit("generation manifest validation failed:\n- " + "\n- ".join(errors))
    print("generation manifest validation passed")


if __name__ == "__main__":
    main()
