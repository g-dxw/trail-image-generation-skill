from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from provider_config import load_config, provider_summary, validate_config  # noqa: E402


class ProviderConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.example = SKILL_DIR / "assets" / "provider-config.example.json"
        cls.payload = load_config(cls.example)

    def test_example_is_valid_and_defaults_to_image2(self):
        self.assertEqual(validate_config(self.payload), [])
        self.assertEqual(self.payload["default_model"], "gpt-image-2")
        self.assertEqual(self.payload["default_provider"], "builtin")

    def test_summary_never_resolves_secret_value(self):
        summary = provider_summary(self.payload, "my-relay")
        self.assertEqual(summary["api_key_env"], "TRAIL_IMAGE_RELAY_API_KEY")
        self.assertNotIn("api_key", summary)
        self.assertEqual(summary["model"], "gpt-image-2")

    def test_rejects_literal_secret_fields(self):
        payload = json.loads(json.dumps(self.payload))
        payload["providers"]["my-relay"]["api_key"] = "secret"
        self.assertTrue(any("secret fields" in error for error in validate_config(payload)))


if __name__ == "__main__":
    unittest.main()
