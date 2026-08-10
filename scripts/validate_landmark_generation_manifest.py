#!/usr/bin/env python3
"""Validate a landmark-simplification manifest before or after generation."""

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


def image_metadata(path: Path) -> dict:
    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError("Pillow is required to validate landmark image dimensions") from exc
    try:
        with Image.open(path) as image:
            return {"format": image.format, "width": image.width, "height": image.height, "mode": image.mode}
    except OSError as exc:
        raise ValueError(f"cannot inspect landmark image: {path}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--require-output", action="store_true")
    args = parser.parse_args()

    try:
        manifest_path = args.manifest.expanduser().resolve()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot read landmark manifest: {exc}") from exc

    errors: list[str] = []
    schema_version = manifest.get("schema_version")
    if schema_version not in {1, 2} or manifest.get("task_type") != "landmark_simplification":
        errors.append("invalid landmark manifest schema or task type")
    if schema_version == 2:
        if manifest.get("generation_purpose") != "landmark_prepaint":
            errors.append("landmark manifest must use generation_purpose landmark_prepaint")
        if manifest.get("selection_method") not in {"configured", "runtime_tool_schema", "user_approved_sample", "unknown"}:
            errors.append("invalid landmark provider selection method")
        if manifest.get("provider_cost_class") not in {"budget", "standard", "premium", "unknown"}:
            errors.append("invalid provider_cost_class")
        if manifest.get("provider_quality_class") not in {"draft", "final", "user_approved_for_drafts", "unknown"}:
            errors.append("invalid provider_quality_class")
        if not manifest.get("requested_size") or not manifest.get("requested_quality"):
            errors.append("missing requested landmark size or quality")
        report_raw = manifest.get("capability_report")
        report_hash = manifest.get("capability_report_sha256")
        if not report_raw or not report_hash:
            errors.append("schema v2 landmark manifest requires a capability report and SHA-256")
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
                            purpose="landmark_prepaint",
                            capacity=manifest.get("provider_max_reference_images", 0),
                            requested_size=str(manifest.get("requested_size", "provider-default")),
                            requested_quality=str(manifest.get("requested_quality", "provider-default")),
                            cost_class=str(manifest.get("provider_cost_class", "unknown")),
                            quality_class=str(manifest.get("provider_quality_class", "unknown")),
                        )
                    )
    if manifest.get("provider_authorized") is not True:
        errors.append("provider/source-photo upload is not authorized")
    capacity = manifest.get("provider_max_reference_images")
    if not isinstance(capacity, int) or isinstance(capacity, bool) or not 1 <= capacity <= 16:
        errors.append("provider cannot accept the one required source photo")
    checkpoint = manifest.get("checkpoint") or {}
    if not isinstance(checkpoint.get("number"), int) or checkpoint.get("number") < 1 or not checkpoint.get("name"):
        errors.append("invalid checkpoint")
    features = manifest.get("must_preserve") or []
    if not 1 <= len(features) <= 3:
        errors.append("must_preserve must contain 1..3 features")
    if not manifest.get("privacy_treatment"):
        errors.append("missing privacy_treatment")

    for label, hash_label in (("source_photo", "source_photo_sha256"), ("prompt_file", "prompt_sha256")):
        raw_path = manifest.get(label)
        if not raw_path:
            errors.append(f"missing {label}")
            continue
        path = Path(raw_path).expanduser().resolve()
        if not path.is_file():
            errors.append(f"missing file for {label}: {path}")
        elif sha256(path) != manifest.get(hash_label):
            errors.append(f"{label} SHA-256 changed")

    prompt_path = Path(str(manifest.get("prompt_file", ""))).expanduser().resolve()
    if prompt_path.is_file():
        prompt = prompt_path.read_text(encoding="utf-8")
        if "[LANDMARK_SIMPLIFICATION_LOCK_BEGIN]" not in prompt or "[LANDMARK_SIMPLIFICATION_LOCK_END]" not in prompt:
            errors.append("landmark prompt lacks the simplification lock block")

    output_path = Path(str(manifest.get("output_image", ""))).expanduser().resolve()
    output_hash = manifest.get("output_sha256")
    if args.require_output:
        if not output_path.is_file():
            errors.append(f"generated landmark output is missing: {output_path}")
        elif not output_hash:
            errors.append("manifest has no generated output SHA-256; rebuild it after generation")
        elif sha256(output_path) != output_hash:
            errors.append("generated landmark output SHA-256 changed")
        else:
            try:
                board_metadata = image_metadata(output_path)
            except ValueError as exc:
                errors.append(str(exc))
            else:
                normalized_raw = manifest.get("normalized_output_image")
                board_size = manifest.get("board_asset_size", 512)
                if normalized_raw:
                    normalized_path = Path(normalized_raw).expanduser().resolve()
                    if output_path != normalized_path:
                        errors.append("output_image must point to normalized_output_image when normalization is recorded")
                    if board_metadata.get("format") != "PNG":
                        errors.append("normalized landmark board asset must be PNG")
                    if (board_metadata.get("width"), board_metadata.get("height")) != (board_size, board_size):
                        errors.append("normalized landmark board asset has the wrong dimensions")
                elif board_metadata.get("width") != board_metadata.get("height") or max(board_metadata.get("width", 0), board_metadata.get("height", 0)) > 1024:
                    errors.append("raw landmark output must be square and at most 1024px, or provide a normalized board asset")
    elif output_hash and (not output_path.is_file() or sha256(output_path) != output_hash):
        errors.append("recorded generated landmark output changed")

    if schema_version == 2:
        raw_path = Path(str(manifest.get("raw_output_image", ""))).expanduser().resolve()
        raw_hash = manifest.get("raw_output_sha256")
        if args.require_output:
            if not raw_path.is_file():
                errors.append(f"raw generated landmark output is missing: {raw_path}")
            elif not raw_hash or sha256(raw_path) != raw_hash:
                errors.append("raw generated landmark output hash is missing or changed")
            else:
                try:
                    actual_raw_metadata = image_metadata(raw_path)
                except ValueError as exc:
                    errors.append(str(exc))
                else:
                    if actual_raw_metadata != manifest.get("raw_output_metadata"):
                        errors.append("raw generated landmark image metadata changed")
        normalized_raw = manifest.get("normalized_output_image")
        if normalized_raw:
            normalized_path = Path(normalized_raw).expanduser().resolve()
            normalized_hash = manifest.get("normalized_output_sha256")
            if args.require_output and (not normalized_path.is_file() or not normalized_hash or sha256(normalized_path) != normalized_hash):
                errors.append("normalized landmark output hash is missing or changed")

    if errors:
        raise SystemExit("landmark manifest validation failed:\n- " + "\n- ".join(errors))
    print("landmark manifest validation passed")


if __name__ == "__main__":
    main()
