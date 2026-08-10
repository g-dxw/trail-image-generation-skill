#!/usr/bin/env python3
"""Validate that a route-generation manifest still matches its approved inputs."""

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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()

    try:
        manifest = json.loads(args.manifest.expanduser().resolve().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot read manifest: {exc}") from exc

    errors: list[str] = []
    schema_version = manifest.get("schema_version", 1)
    if schema_version not in {1, 2}:
        errors.append("unsupported schema_version")
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
        required_labels = ("参考图角色：", "负面约束：", "验收清单：") if schema_version == 1 else (
            "实际上传参考图：",
            "地标参考板编号映射：",
            "点位完整性：",
            "点位对应：",
            "地标连接方式：",
            "素材事实来源（不上传）：",
            "校验资产（不上传）：",
            "单图兼容分支：",
            "负面约束：",
            "验收清单：",
        )
        for required_label in required_labels:
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

    references = (manifest.get("references") or []) if schema_version == 1 else (manifest.get("actual_uploads") or [])
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

    if schema_version == 2:
        if manifest.get("generation_purpose") not in {None, "route_final"}:
            errors.append("final manifest must use generation_purpose route_final")
        if manifest.get("selection_method") not in {"configured", "runtime_tool_schema", "user_approved_sample"}:
            errors.append("invalid final provider selection method")
        if manifest.get("provider_quality_class", "unknown") not in {"final", "user_approved_for_final", "unknown"}:
            errors.append("invalid final provider quality class")
        report_raw = manifest.get("capability_report")
        report_hash = manifest.get("capability_report_sha256")
        if not report_raw or not report_hash:
            errors.append("schema v2 final manifest requires a capability report and SHA-256")
        else:
            report_path = Path(report_raw).expanduser().resolve()
            if not report_path.is_file():
                errors.append(f"capability report is missing: {report_path}")
            elif sha256(report_path) != report_hash:
                errors.append("capability report SHA-256 changed")
            else:
                try:
                    report = load_capability_report(report_path)
                except ValueError as exc:
                    errors.append(str(exc))
                else:
                    errors.extend(
                        validate_execution_against_report(
                            report,
                            provider=str(manifest.get("provider", "")),
                            model=str(manifest.get("model", "")),
                            purpose="route_final",
                            capacity=manifest.get("provider_max_reference_images", 0),
                            requested_quality=str(manifest.get("requested_quality", "provider-default")),
                            cost_class=str(manifest.get("provider_cost_class", "unknown")),
                            quality_class=str(manifest.get("provider_quality_class", "unknown")),
                        )
                    )
        provider_limit = manifest.get("provider_max_reference_images")
        if not isinstance(provider_limit, int) or isinstance(provider_limit, bool) or not 0 <= provider_limit <= 16:
            errors.append("invalid provider_max_reference_images")
            provider_limit = 0
        if len(references) > 2:
            errors.append("two-image mode allows at most two actual uploads")
        if len(references) > provider_limit:
            errors.append("actual uploads exceed provider reference-image capacity")
        if not references or references[0].get("role") != "route_geometry":
            errors.append("first actual upload must be route_geometry")
        if references and route_png and Path(str(references[0].get("path", ""))).expanduser().resolve() != route_png:
            errors.append("first actual upload must be the approved route PNG")
        if len(references) == 2 and references[1].get("role") != "landmark_reference_board":
            errors.append("second actual upload must be landmark_reference_board")
        allowed_roles = {"route_geometry", "landmark_reference_board"}
        if any(item.get("role") not in allowed_roles for item in references):
            errors.append("actual uploads contain an unsupported role")
        forbidden_upload_paths = {str(path) for label, path in resolved.items() if label in {"route_svg", "layout_json"}}
        for upload in references:
            if upload.get("path") in forbidden_upload_paths:
                errors.append("SVG or layout JSON cannot be an actual upload")

        mode = manifest.get("reference_mode")
        if mode not in {"route_only", "route_only_fallback", "two_image"}:
            errors.append("invalid reference_mode")
        if mode == "two_image" and len(references) != 2:
            errors.append("two_image mode requires route PNG plus landmark board")
        if mode == "route_only" and len(references) != 1:
            errors.append("route_only mode requires exactly one upload")
        if mode == "route_only_fallback":
            if len(references) != 1 or not manifest.get("omitted_landmark_board"):
                errors.append("route_only_fallback must record the omitted landmark board")

        board_path_raw = manifest.get("landmark_board")
        sidecar_raw = manifest.get("landmark_board_sidecar")
        if bool(board_path_raw) != bool(sidecar_raw):
            errors.append("landmark board and sidecar must be recorded together")
        if board_path_raw and sidecar_raw:
            board_path = Path(board_path_raw).expanduser().resolve()
            sidecar_path = Path(sidecar_raw).expanduser().resolve()
            if not board_path.is_file():
                errors.append(f"landmark board is missing: {board_path}")
            if len(references) == 2 and Path(str(references[1].get("path", ""))).expanduser().resolve() != board_path:
                errors.append("second actual upload does not match the approved landmark board")
            if not sidecar_path.is_file():
                errors.append(f"landmark board sidecar is missing: {sidecar_path}")
            elif sha256(sidecar_path) != manifest.get("landmark_board_sidecar_sha256"):
                errors.append("landmark board sidecar SHA-256 changed")
            else:
                try:
                    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    errors.append(f"invalid landmark board sidecar: {exc}")
                else:
                    boards = sidecar.get("boards") or []
                    matched_board = next((item for item in boards if Path(str(item.get("path", ""))).expanduser().resolve() == board_path), None)
                    if not matched_board:
                        errors.append("landmark board is not present in its sidecar")
                    elif board_path.is_file() and sha256(board_path) != matched_board.get("sha256"):
                        errors.append("landmark board SHA-256 differs from sidecar")
                    if sidecar.get("board_type") != "landmark_reference_board":
                        errors.append("final generation requires a landmark_reference_board sidecar")
                    for board in boards:
                        for item in board.get("items") or []:
                            source_path = Path(str(item.get("path", ""))).expanduser().resolve()
                            if not source_path.is_file():
                                errors.append(f"simplified landmark source is missing: {source_path}")
                            elif sha256(source_path) != item.get("sha256"):
                                errors.append(f"simplified landmark source SHA-256 changed: {source_path}")
                            generation_manifest = item.get("generation_manifest")
                            if generation_manifest:
                                generation_path = Path(generation_manifest).expanduser().resolve()
                                if not generation_path.is_file():
                                    errors.append(f"landmark generation manifest is missing: {generation_path}")
                                else:
                                    try:
                                        generation = json.loads(generation_path.read_text(encoding="utf-8"))
                                    except json.JSONDecodeError as exc:
                                        errors.append(f"invalid landmark generation manifest: {exc}")
                                    else:
                                        if Path(str(generation.get("output_image", ""))).expanduser().resolve() != source_path:
                                            errors.append("landmark generation manifest output does not match board source")
                                        if generation.get("output_sha256") != item.get("sha256"):
                                            errors.append("landmark generation manifest hash does not match board source")

        for source in manifest.get("source_materials") or []:
            path = Path(str(source.get("path", ""))).expanduser().resolve()
            if not path.is_file():
                errors.append(f"source material is missing: {path}")
            elif sha256(path) != source.get("sha256"):
                errors.append(f"source material SHA-256 changed: {path}")

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
