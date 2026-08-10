#!/usr/bin/env python3
"""Validate and select non-secret image-provider profiles by generation purpose."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse


ALLOWED_FORMATS = {"openai-responses", "openai-images", "custom"}
ALLOWED_RESULTS = {"url", "base64", "binary"}
ALLOWED_PURPOSES = {"landmark_prepaint", "route_final"}
ALLOWED_COST_CLASSES = {"budget", "standard", "premium", "unknown"}
ALLOWED_QUALITY_CLASSES = {"draft", "final", "user_approved_for_drafts", "user_approved_for_final", "unknown"}
ALLOWED_CAPABILITY_SOURCES = {
    "runtime_tool_schema",
    "provider_config",
    "provider_documentation",
    "user_approved_sample",
    "unknown",
}
SECRET_FIELDS = {"api_key", "token", "access_token", "secret", "password", "authorization"}
SIZE_PATTERN = re.compile(r"^[1-9][0-9]*x[1-9][0-9]*$")
TRISTATE = {True, False, "unknown"}


def effective_max_reference_images(provider: dict) -> int | str:
    """Return the backward-compatible reference-image capacity."""
    value = provider.get("max_reference_images")
    if value is None:
        supports = provider.get("supports_reference_images")
        if supports is True:
            return 1
        if supports == "unknown":
            return "unknown"
        return 0
    if value == "unknown":
        return "unknown"
    return value


def effective_purposes(provider: dict) -> list[str]:
    """Legacy provider profiles are allowed for both stages until explicitly restricted."""
    purposes = provider.get("allowed_purposes")
    return list(purposes) if isinstance(purposes, list) else sorted(ALLOWED_PURPOSES)


def load_config(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("provider config must be a JSON object")
    return payload


def load_capability_report(path: Path) -> dict:
    try:
        report = json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read capability report: {exc}") from exc
    if not isinstance(report, dict):
        raise ValueError("capability report must be an object")
    errors = validate_capability_report(report)
    if errors:
        raise ValueError("invalid capability report: " + "; ".join(errors))
    return report


def validate_capability_report(report: dict) -> list[str]:
    errors: list[str] = []
    if report.get("schema_version") != 1 or report.get("report_type") != "image_capability_report":
        errors.append("invalid capability report schema or type")
    if not report.get("executor"):
        errors.append("capability report missing executor")
    if report.get("executor_type") not in {"current_session", "relay"}:
        errors.append("capability report has invalid executor_type")
    if not isinstance(report.get("model"), str) or not report.get("model"):
        errors.append("capability report missing model")
    if report.get("capability_source") not in ALLOWED_CAPABILITY_SOURCES:
        errors.append("capability report has invalid capability_source")
    capabilities = report.get("capabilities")
    if not isinstance(capabilities, dict):
        return errors + ["capability report missing capabilities object"]
    for field in ("can_generate", "can_use_reference_image", "can_edit_image", "selectable_model", "selectable_size", "selectable_quality"):
        if capabilities.get(field) not in TRISTATE:
            errors.append(f"capability report {field} must be true, false, or unknown")
    capacity = capabilities.get("max_reference_images", "unknown")
    if capacity != "unknown" and (not isinstance(capacity, int) or isinstance(capacity, bool) or not 0 <= capacity <= 16):
        errors.append("capability report max_reference_images must be an integer in 0..16 or unknown")
    for field in ("supported_output_sizes", "supported_quality_levels"):
        values = capabilities.get(field, [])
        if not isinstance(values, list):
            errors.append(f"capability report {field} must be a unique list")
        elif any(not isinstance(item, str) for item in values) or len(set(values)) != len(values):
            errors.append(f"capability report {field} must be a unique string list")
        elif field == "supported_output_sizes" and any(not isinstance(item, str) or not SIZE_PATTERN.match(item) for item in values):
            errors.append("capability report supported_output_sizes contains an invalid size")
        elif field == "supported_quality_levels" and any(not isinstance(item, str) or not item for item in values):
            errors.append("capability report supported_quality_levels contains an invalid quality")
    for field, allowed in (("cost_class", ALLOWED_COST_CLASSES), ("quality_class", ALLOWED_QUALITY_CLASSES)):
        if capabilities.get(field, "unknown") not in allowed:
            errors.append(f"capability report has invalid {field}")
    return errors


def merge_capability_report(summary: dict, report: dict) -> dict:
    """Overlay runtime evidence on a provider summary without inventing missing values."""
    capabilities = report["capabilities"]
    merged = dict(summary)
    if report.get("model") != "tool-managed/unknown":
        merged["model"] = report["model"]
    for key in ("supports_reference_images", "supports_image_editing"):
        report_key = "can_use_reference_image" if key == "supports_reference_images" else "can_edit_image"
        if capabilities[report_key] != "unknown":
            merged[key] = capabilities[report_key]
    report_capacity = capabilities.get("max_reference_images", "unknown")
    if report_capacity != "unknown":
        merged["max_reference_images"] = report_capacity
    for key, report_key in (("supported_output_sizes", "supported_output_sizes"), ("supported_quality_levels", "supported_quality_levels")):
        if capabilities.get(report_key):
            merged[key] = capabilities[report_key]
    for key in ("cost_class", "quality_class"):
        if capabilities.get(key, "unknown") != "unknown":
            merged[key] = capabilities[key]
    merged["capability_source"] = report.get("capability_source", merged.get("capability_source", "unknown"))
    merged["capability_report"] = report.get("executor")
    return merged


def validate_execution_against_report(
    report: dict,
    *,
    provider: str,
    model: str,
    purpose: str,
    capacity: int,
    requested_size: str = "provider-default",
    requested_quality: str = "provider-default",
    cost_class: str = "unknown",
    quality_class: str = "unknown",
) -> list[str]:
    errors: list[str] = []
    if report.get("executor") != provider:
        errors.append("capability report executor does not match manifest provider")
    report_model = report.get("model")
    if report_model == "tool-managed/unknown":
        if model != "tool-managed/unknown":
            errors.append("manifest cannot claim a model hidden by the capability report")
    elif model != report_model:
        errors.append("manifest model differs from capability report")
    capabilities = report.get("capabilities") or {}
    if capabilities.get("can_generate") is not True:
        errors.append("capability report does not confirm image generation")
    if capabilities.get("can_use_reference_image") is not True:
        errors.append("capability report does not confirm reference-image input")
    if purpose == "landmark_prepaint" and capabilities.get("can_edit_image") is not True:
        errors.append("capability report does not confirm image editing for landmark prepaint")
    report_capacity = capabilities.get("max_reference_images", "unknown")
    if report_capacity == "unknown":
        errors.append("capability report does not confirm maximum reference-image capacity")
    elif capacity > report_capacity:
        errors.append("manifest reference-image capacity exceeds capability report")
    sizes = capabilities.get("supported_output_sizes") or []
    if requested_size not in {"provider-default", "smallest-supported", "unknown"} and requested_size not in sizes:
        errors.append("requested image size is not supported by capability report")
    if requested_size == "smallest-supported" and not sizes:
        errors.append("smallest-supported requires a non-empty supported size list")
    qualities = capabilities.get("supported_quality_levels") or []
    if requested_quality not in {"provider-default", "unknown"} and requested_quality not in qualities:
        errors.append("requested quality is not supported by capability report")
    report_cost = capabilities.get("cost_class", "unknown")
    if report_cost != "unknown" and cost_class != report_cost:
        errors.append("manifest cost class differs from capability report")
    report_quality = capabilities.get("quality_class", "unknown")
    if report_quality != "unknown" and quality_class != report_quality:
        errors.append("manifest quality class differs from capability report")
    return errors


def validate_config(payload: dict) -> list[str]:
    errors: list[str] = []
    schema_version = payload.get("schema_version", 1)
    if schema_version not in {1, 2}:
        errors.append("schema_version must be 1 or 2")
    providers = payload.get("providers")
    if not isinstance(providers, dict) or not providers:
        return errors + ["providers must be a non-empty object"]

    default_provider = payload.get("default_provider")
    if default_provider is not None and default_provider not in providers:
        errors.append("default_provider must name an existing provider")
    defaults = payload.get("defaults") or {}
    if defaults and not isinstance(defaults, dict):
        errors.append("defaults must be an object")
        defaults = {}
    for purpose in ALLOWED_PURPOSES:
        selected = defaults.get(f"{purpose}_provider")
        if selected is not None and selected not in providers:
            errors.append(f"default {purpose} provider must name an existing provider")

    for name, provider in providers.items():
        if not isinstance(provider, dict):
            errors.append(f"provider {name} must be an object")
            continue
        leaked = SECRET_FIELDS.intersection(key.lower() for key in provider)
        if leaked:
            errors.append(f"provider {name} contains secret fields: {', '.join(sorted(leaked))}")
        provider_type = provider.get("type")
        if provider_type not in {"current_session", "relay"}:
            errors.append(f"provider {name} has invalid type")
            continue
        model = provider.get("model")
        if not isinstance(model, str) or not model:
            errors.append(f"provider {name} is missing model; use tool-managed/unknown when the tool hides it")

        purposes = provider.get("allowed_purposes")
        if purposes is not None and (
            not isinstance(purposes, list)
            or not purposes
            or any(item not in ALLOWED_PURPOSES for item in purposes)
            or len(set(purposes)) != len(purposes)
        ):
            errors.append(f"provider {name} allowed_purposes must contain unique supported purposes")
        if provider.get("cost_class", "unknown") not in ALLOWED_COST_CLASSES:
            errors.append(f"provider {name} has invalid cost_class")
        if provider.get("quality_class", "unknown") not in ALLOWED_QUALITY_CLASSES:
            errors.append(f"provider {name} has invalid quality_class")
        if provider.get("capability_source", "unknown") not in ALLOWED_CAPABILITY_SOURCES:
            errors.append(f"provider {name} has invalid capability_source")

        sizes = provider.get("supported_output_sizes")
        if sizes is not None and (
            not isinstance(sizes, list)
            or any(not isinstance(item, str) or not SIZE_PATTERN.match(item) for item in sizes)
            or len(set(sizes)) != len(sizes)
        ):
            errors.append(f"provider {name} supported_output_sizes must contain unique WIDTHxHEIGHT values")
        qualities = provider.get("supported_quality_levels")
        if qualities is not None and (
            not isinstance(qualities, list)
            or any(not isinstance(item, str) or not item for item in qualities)
            or len(set(qualities)) != len(qualities)
        ):
            errors.append(f"provider {name} supported_quality_levels must contain unique strings")
        preferred_size = provider.get("preferred_output_size")
        if preferred_size is not None and (not sizes or preferred_size not in sizes):
            errors.append(f"provider {name} preferred_output_size must be listed in supported_output_sizes")
        preferred_quality = provider.get("preferred_quality")
        if preferred_quality is not None and (not qualities or preferred_quality not in qualities):
            errors.append(f"provider {name} preferred_quality must be listed in supported_quality_levels")

        max_reference_images = provider.get("max_reference_images")
        if max_reference_images is not None and max_reference_images != "unknown" and (
            not isinstance(max_reference_images, int)
            or isinstance(max_reference_images, bool)
            or not 0 <= max_reference_images <= 16
        ):
            errors.append(f"provider {name} max_reference_images must be an integer in 0..16 or unknown")
        for field in ("supports_reference_images", "supports_image_editing"):
            if provider.get(field, "unknown") not in TRISTATE:
                errors.append(f"provider {name} {field} must be true, false, or unknown")
        if isinstance(max_reference_images, int) and not isinstance(max_reference_images, bool) and max_reference_images > 0 and provider.get("supports_reference_images") is False:
            errors.append(f"provider {name} cannot set max_reference_images when supports_reference_images is false")
        if "landmark_prepaint" in effective_purposes(provider) and provider.get("supports_image_editing") is False:
            errors.append(f"provider {name} cannot allow landmark_prepaint when supports_image_editing is false")

        if provider_type == "relay":
            parsed = urlparse(str(provider.get("base_url", "")))
            if parsed.scheme not in {"https", "http"} or not parsed.netloc:
                errors.append(f"provider {name} has invalid base_url")
            if provider.get("api_format") not in ALLOWED_FORMATS:
                errors.append(f"provider {name} has invalid api_format")
            if provider.get("result_format") not in ALLOWED_RESULTS:
                errors.append(f"provider {name} has invalid result_format")
            env_name = provider.get("api_key_env")
            if not isinstance(env_name, str) or not env_name or not env_name.replace("_", "A").isalnum() or env_name.upper() != env_name:
                errors.append(f"provider {name} has invalid api_key_env")
            timeout = provider.get("timeout_seconds", 180)
            retries = provider.get("max_retries", 1)
            if not isinstance(timeout, int) or not 10 <= timeout <= 600:
                errors.append(f"provider {name} timeout_seconds must be 10..600")
            if not isinstance(retries, int) or not 0 <= retries <= 3:
                errors.append(f"provider {name} max_retries must be 0..3")
    return errors


def provider_summary(payload: dict, name: str) -> dict:
    provider = (payload.get("providers") or {}).get(name)
    if not isinstance(provider, dict):
        raise ValueError(f"unknown provider: {name}")
    model = provider.get("model") or payload.get("default_model") or "tool-managed/unknown"
    return {
        "provider": name,
        "type": provider.get("type"),
        "enabled": provider.get("enabled", True),
        "base_url": provider.get("base_url", "current-session-tool"),
        "api_format": provider.get("api_format", "current-session-native"),
        "model": model,
        "api_key_env": provider.get("api_key_env", "not-applicable"),
        "allowed_purposes": effective_purposes(provider),
        "supports_reference_images": provider.get("supports_reference_images", "unknown"),
        "max_reference_images": effective_max_reference_images(provider),
        "supports_image_editing": provider.get("supports_image_editing", "unknown"),
        "supported_output_sizes": provider.get("supported_output_sizes", []),
        "supported_quality_levels": provider.get("supported_quality_levels", []),
        "preferred_output_size": provider.get("preferred_output_size", "unknown"),
        "preferred_quality": provider.get("preferred_quality", "unknown"),
        "cost_class": provider.get("cost_class", "unknown"),
        "quality_class": provider.get("quality_class", "unknown"),
        "capability_source": provider.get("capability_source", "unknown"),
        "result_format": provider.get("result_format", "tool-result"),
    }


def select_provider(payload: dict, purpose: str, name: str | None = None, capability_report: Path | None = None) -> dict:
    if purpose not in ALLOWED_PURPOSES:
        raise ValueError(f"unsupported purpose: {purpose}")
    defaults = payload.get("defaults") or {}
    selected = name or defaults.get(f"{purpose}_provider") or payload.get("default_provider")
    if not selected:
        raise ValueError(f"no default provider configured for {purpose}")
    summary = provider_summary(payload, selected)
    if capability_report:
        report = load_capability_report(capability_report)
        if report.get("executor") not in {selected, summary.get("base_url"), "current-session-image-tool"}:
            raise ValueError(f"capability report executor does not match provider {selected}")
        summary = merge_capability_report(summary, report)
    if purpose not in summary["allowed_purposes"]:
        raise ValueError(f"provider {selected} is not allowed for {purpose}")
    if not summary["enabled"]:
        raise ValueError(f"provider {selected} is disabled")
    if purpose == "landmark_prepaint":
        if summary["max_reference_images"] == "unknown" or summary["max_reference_images"] < 1:
            raise ValueError(f"provider {selected} cannot accept the required source photo")
        if summary["supports_image_editing"] is not True:
            raise ValueError(f"provider {selected} image-editing capability is not confirmed")
    if purpose == "route_final" and (summary["max_reference_images"] == "unknown" or summary["max_reference_images"] < 1):
        raise ValueError(f"provider {selected} cannot accept route geometry")
    summary["purpose"] = purpose
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("config", type=Path)
    show_parser = subparsers.add_parser("show")
    show_parser.add_argument("config", type=Path)
    show_parser.add_argument("--provider", required=True)
    select_parser = subparsers.add_parser("select")
    select_parser.add_argument("config", type=Path)
    select_parser.add_argument("--purpose", choices=sorted(ALLOWED_PURPOSES), required=True)
    select_parser.add_argument("--provider")
    select_parser.add_argument("--capability-report", type=Path)
    args = parser.parse_args()

    try:
        payload = load_config(args.config)
        errors = validate_config(payload)
        if errors:
            raise ValueError("; ".join(errors))
        if args.command == "validate":
            print("provider config is valid")
        elif args.command == "show":
            print(json.dumps(provider_summary(payload, args.provider), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(select_provider(payload, args.purpose, args.provider, args.capability_report), ensure_ascii=False, indent=2))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
