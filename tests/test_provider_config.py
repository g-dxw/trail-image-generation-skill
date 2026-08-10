from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from provider_config import effective_max_reference_images, load_config, provider_summary, select_provider, validate_config  # noqa: E402


class ProviderConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.example = SKILL_DIR / "assets" / "provider-config.example.json"
        cls.payload = load_config(cls.example)

    def write_report(self, root: Path, *, editing=True, capacity=2) -> Path:
        path = root / "capabilities.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "report_type": "image_capability_report",
                    "observed_at": "2026-08-10T00:00:00+00:00",
                    "executor": "builtin",
                    "executor_type": "current_session",
                    "model": "tool-managed/unknown",
                    "capability_source": "runtime_tool_schema",
                    "capabilities": {
                        "can_generate": True,
                        "can_use_reference_image": True,
                        "can_edit_image": editing,
                        "selectable_model": False,
                        "selectable_size": False,
                        "selectable_quality": False,
                        "max_reference_images": capacity,
                        "supported_output_sizes": [],
                        "supported_quality_levels": [],
                        "cost_class": "unknown",
                        "quality_class": "unknown",
                    },
                    "evidence": ["test"],
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_example_is_valid_and_uses_purpose_defaults(self):
        self.assertEqual(validate_config(self.payload), [])
        self.assertEqual(self.payload["schema_version"], 2)
        self.assertEqual(self.payload["defaults"]["landmark_prepaint_provider"], "builtin")
        self.assertEqual(self.payload["defaults"]["route_final_provider"], "builtin")

    def test_summary_never_resolves_secret_value(self):
        summary = provider_summary(self.payload, "draft-relay")
        self.assertEqual(summary["api_key_env"], "TRAIL_DRAFT_RELAY_API_KEY")
        self.assertNotIn("api_key", summary)
        self.assertEqual(summary["model"], "configured-draft-model")
        self.assertEqual(summary["max_reference_images"], 1)
        self.assertEqual(summary["preferred_output_size"], "512x512")

    def test_selects_provider_by_generation_purpose(self):
        with tempfile.TemporaryDirectory() as raw:
            report = self.write_report(Path(raw))
            prepaint = select_provider(self.payload, "landmark_prepaint", capability_report=report)
            final = select_provider(self.payload, "route_final", capability_report=report)
            self.assertEqual(prepaint["purpose"], "landmark_prepaint")
            self.assertEqual(final["purpose"], "route_final")
            self.assertEqual(prepaint["model"], "tool-managed/unknown")

    def test_rejects_cross_purpose_selection(self):
        with self.assertRaisesRegex(ValueError, "not allowed"):
            select_provider(self.payload, "route_final", "draft-relay")

    def test_legacy_reference_flag_maps_to_one_or_zero(self):
        self.assertEqual(effective_max_reference_images({"supports_reference_images": True}), 1)
        self.assertEqual(effective_max_reference_images({"supports_reference_images": False}), 0)

    def test_rejects_reference_capacity_conflicting_with_false_flag(self):
        payload = json.loads(json.dumps(self.payload))
        payload["providers"]["draft-relay"]["supports_reference_images"] = False
        payload["providers"]["draft-relay"]["max_reference_images"] = 2
        self.assertTrue(any("cannot set max_reference_images" in error for error in validate_config(payload)))

    def test_rejects_literal_secret_fields(self):
        payload = json.loads(json.dumps(self.payload))
        payload["providers"]["draft-relay"]["api_key"] = "secret"
        self.assertTrue(any("secret fields" in error for error in validate_config(payload)))

    def test_rejects_unconfirmed_editing_for_prepaint(self):
        with tempfile.TemporaryDirectory() as raw:
            report = self.write_report(Path(raw), editing="unknown", capacity=1)
            with self.assertRaisesRegex(ValueError, "not confirmed"):
                select_provider(self.payload, "landmark_prepaint", capability_report=report)

    def test_rejects_invalid_capability_field_types(self):
        payload = json.loads(json.dumps(self.payload))
        payload["providers"]["builtin"]["supports_reference_images"] = "yes"
        payload["providers"]["builtin"]["supports_image_editing"] = "maybe"
        errors = validate_config(payload)
        self.assertTrue(any("supports_reference_images" in error for error in errors))
        self.assertTrue(any("supports_image_editing" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
