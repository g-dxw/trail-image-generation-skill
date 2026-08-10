#!/usr/bin/env python3
"""Record evidence-backed image-tool capabilities without making a generation request."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


TRISTATE = {"true", "false", "unknown"}
SOURCES = {"runtime_tool_schema", "provider_config", "provider_documentation", "user_approved_sample", "unknown"}


def tristate(value: str):
    if value not in TRISTATE:
        raise argparse.ArgumentTypeError("must be true, false, or unknown")
    return {"true": True, "false": False, "unknown": "unknown"}[value]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executor", required=True)
    parser.add_argument("--executor-type", choices=("current_session", "relay"), required=True)
    parser.add_argument("--model", default="tool-managed/unknown")
    parser.add_argument("--source", choices=sorted(SOURCES), default="unknown")
    parser.add_argument("--can-generate", type=tristate, default="unknown")
    parser.add_argument("--can-use-reference-image", type=tristate, default="unknown")
    parser.add_argument("--can-edit-image", type=tristate, default="unknown")
    parser.add_argument("--selectable-model", type=tristate, default="unknown")
    parser.add_argument("--selectable-size", type=tristate, default="unknown")
    parser.add_argument("--selectable-quality", type=tristate, default="unknown")
    parser.add_argument("--max-reference-images", type=int)
    parser.add_argument("--supported-size", action="append", default=[])
    parser.add_argument("--supported-quality", action="append", default=[])
    parser.add_argument("--cost-class", choices=("budget", "standard", "premium", "unknown"), default="unknown")
    parser.add_argument("--quality-class", choices=("draft", "final", "user_approved_for_drafts", "user_approved_for_final", "unknown"), default="unknown")
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.max_reference_images is not None and not 0 <= args.max_reference_images <= 16:
        raise SystemExit("max reference images must be in 0..16")

    report = {
        "schema_version": 1,
        "report_type": "image_capability_report",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "executor": args.executor,
        "executor_type": args.executor_type,
        "model": args.model,
        "capability_source": args.source,
        "capabilities": {
            "can_generate": args.can_generate,
            "can_use_reference_image": args.can_use_reference_image,
            "can_edit_image": args.can_edit_image,
            "selectable_model": args.selectable_model,
            "selectable_size": args.selectable_size,
            "selectable_quality": args.selectable_quality,
            "max_reference_images": args.max_reference_images if args.max_reference_images is not None else "unknown",
            "supported_output_sizes": args.supported_size,
            "supported_quality_levels": args.supported_quality,
            "cost_class": args.cost_class,
            "quality_class": args.quality_class,
        },
        "evidence": args.evidence,
    }
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
