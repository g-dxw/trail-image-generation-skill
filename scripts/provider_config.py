#!/usr/bin/env python3
"""Validate and display non-secret image-provider configuration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse


ALLOWED_FORMATS = {"openai-responses", "openai-images", "custom"}
ALLOWED_RESULTS = {"url", "base64", "binary"}
SECRET_FIELDS = {"api_key", "token", "access_token", "secret", "password", "authorization"}


def load_config(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("provider config must be a JSON object")
    return payload


def validate_config(payload: dict) -> list[str]:
    errors: list[str] = []
    if payload.get("default_model") != "gpt-image-2":
        errors.append("default_model must be gpt-image-2")
    providers = payload.get("providers")
    if not isinstance(providers, dict) or not providers:
        return errors + ["providers must be a non-empty object"]
    default_provider = payload.get("default_provider")
    if default_provider not in providers:
        errors.append("default_provider must name an existing provider")
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
        if not provider.get("model"):
            errors.append(f"provider {name} is missing model")
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
    return {
        "provider": name,
        "type": provider.get("type"),
        "enabled": provider.get("enabled", True),
        "base_url": provider.get("base_url", "current-session-tool"),
        "api_format": provider.get("api_format", "current-session-native"),
        "model": provider.get("model") or payload.get("default_model", "gpt-image-2"),
        "api_key_env": provider.get("api_key_env", "not-applicable"),
        "supports_reference_images": provider.get("supports_reference_images"),
        "supports_image_editing": provider.get("supports_image_editing"),
        "result_format": provider.get("result_format", "tool-result"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate image-provider configuration without reading secret values.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("config", type=Path)
    show_parser = subparsers.add_parser("show")
    show_parser.add_argument("config", type=Path)
    show_parser.add_argument("--provider", required=True)
    args = parser.parse_args()

    try:
        payload = load_config(args.config)
        errors = validate_config(payload)
        if errors:
            raise ValueError("; ".join(errors))
        if args.command == "validate":
            print("provider config is valid")
        else:
            print(json.dumps(provider_summary(payload, args.provider), ensure_ascii=False, indent=2))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
