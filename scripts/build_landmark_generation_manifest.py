#!/usr/bin/env python3
"""Build a reproducible manifest for one landmark-simplification image task."""

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


def image_metadata(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError("Pillow is required to inspect generated landmark images") from exc
    try:
        with Image.open(path) as image:
            return {"format": image.format, "width": image.width, "height": image.height, "mode": image.mode}
    except OSError as exc:
        raise ValueError(f"cannot inspect generated landmark image: {path}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--checkpoint-number", type=int, required=True)
    parser.add_argument("--checkpoint-name", required=True)
    parser.add_argument("--source-photo", type=Path, required=True)
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--selection-method", choices=("configured", "runtime_tool_schema", "user_approved_sample", "unknown"), default="unknown")
    parser.add_argument("--requested-size", default="provider-default")
    parser.add_argument("--requested-quality", default="provider-default")
    parser.add_argument("--provider-cost-class", choices=("budget", "standard", "premium", "unknown"), default="unknown")
    parser.add_argument("--provider-quality-class", choices=("draft", "final", "user_approved_for_drafts", "unknown"), default="unknown")
    parser.add_argument("--capability-report", type=Path, required=True)
    parser.add_argument("--style", required=True)
    parser.add_argument("--must-preserve", action="append", default=[])
    parser.add_argument("--avoid", action="append", default=[])
    parser.add_argument("--privacy-treatment", required=True)
    parser.add_argument("--provider-max-reference-images", type=int, required=True)
    parser.add_argument("--output-image", type=Path, required=True)
    parser.add_argument("--normalized-output-image", type=Path)
    parser.add_argument("--board-asset-size", type=int, default=512)
    parser.add_argument("--provider-authorized", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.checkpoint_number < 1:
        raise SystemExit("checkpoint number must be positive")
    if not 1 <= len(args.must_preserve) <= 3:
        raise SystemExit("landmark task requires 1..3 --must-preserve features")
    if not args.provider_authorized:
        raise SystemExit("landmark source upload requires --provider-authorized")
    if not 1 <= args.provider_max_reference_images <= 16:
        raise SystemExit("landmark simplification requires a provider that accepts at least one reference image")

    try:
        source_photo = resolved_file(args.source_photo, "source photo")
        prompt_file = resolved_file(args.prompt_file, "prompt file")
        capability_report = resolved_file(args.capability_report, "capability report")
        report = load_capability_report(capability_report)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    prompt = prompt_file.read_text(encoding="utf-8")
    if "[LANDMARK_SIMPLIFICATION_LOCK_BEGIN]" not in prompt or "[LANDMARK_SIMPLIFICATION_LOCK_END]" not in prompt:
        raise SystemExit("landmark prompt lacks the simplification lock block")

    report_errors = validate_execution_against_report(
        report,
        provider=args.provider,
        model=args.model,
        purpose="landmark_prepaint",
        capacity=args.provider_max_reference_images,
        requested_size=args.requested_size,
        requested_quality=args.requested_quality,
        cost_class=args.provider_cost_class,
        quality_class=args.provider_quality_class,
    )
    if report_errors:
        raise SystemExit("landmark capability validation failed:\n- " + "\n- ".join(report_errors))
    if not 128 <= args.board_asset_size <= 1024:
        raise SystemExit("board asset size must be in 128..1024")

    raw_output_image = args.output_image.expanduser().resolve()
    normalized_output_image = args.normalized_output_image.expanduser().resolve() if args.normalized_output_image else None
    board_source_image = normalized_output_image or raw_output_image
    try:
        raw_metadata = image_metadata(raw_output_image)
        normalized_metadata = image_metadata(normalized_output_image) if normalized_output_image else None
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    manifest = {
        "schema_version": 2,
        "task_type": "landmark_simplification",
        "generation_purpose": "landmark_prepaint",
        "task_id": args.task_id,
        "checkpoint": {"number": args.checkpoint_number, "name": args.checkpoint_name},
        "source_photo": str(source_photo),
        "source_photo_sha256": sha256(source_photo),
        "prompt_file": str(prompt_file),
        "prompt_sha256": sha256(prompt_file),
        "provider": args.provider,
        "model": args.model,
        "selection_method": args.selection_method,
        "requested_size": args.requested_size,
        "requested_quality": args.requested_quality,
        "provider_cost_class": args.provider_cost_class,
        "provider_quality_class": args.provider_quality_class,
        "capability_report": str(capability_report),
        "capability_report_sha256": sha256(capability_report),
        "provider_authorized": True,
        "provider_max_reference_images": args.provider_max_reference_images,
        "style": args.style,
        "must_preserve": args.must_preserve,
        "avoid": args.avoid,
        "privacy_treatment": args.privacy_treatment,
        "raw_output_image": str(raw_output_image),
        "raw_output_sha256": sha256(raw_output_image) if raw_output_image.is_file() else None,
        "raw_output_metadata": raw_metadata,
        "normalized_output_image": str(normalized_output_image) if normalized_output_image else None,
        "normalized_output_sha256": sha256(normalized_output_image) if normalized_output_image and normalized_output_image.is_file() else None,
        "normalized_output_metadata": normalized_metadata,
        "board_asset_size": args.board_asset_size,
        "output_image": str(board_source_image),
        "output_sha256": sha256(board_source_image) if board_source_image.is_file() else None,
    }
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
