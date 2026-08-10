from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]


class ImageCapabilityReportTests(unittest.TestCase):
    def test_records_unknown_without_generation_request(self):
        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw) / "capabilities.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SKILL_DIR / "scripts" / "build_image_capability_report.py"),
                    "--executor", "current-session-image-tool",
                    "--executor-type", "current_session",
                    "--source", "runtime_tool_schema",
                    "--can-generate", "true",
                    "--can-use-reference-image", "true",
                    "--can-edit-image", "unknown",
                    "--selectable-model", "false",
                    "--selectable-size", "false",
                    "--selectable-quality", "false",
                    "--output", str(output),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["model"], "tool-managed/unknown")
            self.assertEqual(payload["capabilities"]["can_edit_image"], "unknown")
            self.assertEqual(payload["capabilities"]["cost_class"], "unknown")


if __name__ == "__main__":
    unittest.main()
