from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SKILL_DIR = Path(__file__).resolve().parents[1]


class LandmarkGenerationManifestTests(unittest.TestCase):
    def write_report(self, root: Path, capacity: int = 1) -> Path:
        report = root / "capabilities.json"
        report.write_text(
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
                        "can_edit_image": True,
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
        return report

    def test_preflight_and_completed_manifest(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source.jpg"
            Image.new("RGB", (80, 60), "green").save(source)
            prompt = root / "prompt.md"
            prompt.write_text("[LANDMARK_SIMPLIFICATION_LOCK_BEGIN]\nlocked\n[LANDMARK_SIMPLIFICATION_LOCK_END]\n", encoding="utf-8")
            generated = root / "generated.png"
            manifest = root / "manifest.json"
            report = self.write_report(root)
            builder = SKILL_DIR / "scripts" / "build_landmark_generation_manifest.py"
            validator = SKILL_DIR / "scripts" / "validate_landmark_generation_manifest.py"
            command = [
                sys.executable,
                str(builder),
                "--task-id", "landmark-3",
                "--checkpoint-number", "3",
                "--checkpoint-name", "三块石",
                "--source-photo", str(source),
                "--prompt-file", str(prompt),
                "--provider", "builtin",
                "--model", "tool-managed/unknown",
                "--selection-method", "runtime_tool_schema",
                "--requested-size", "provider-default",
                "--requested-quality", "provider-default",
                "--provider-cost-class", "unknown",
                "--provider-quality-class", "unknown",
                "--capability-report", str(report),
                "--provider-max-reference-images", "1",
                "--style", "watercolor",
                "--must-preserve", "three weathered rocks",
                "--privacy-treatment", "remove people",
                "--output-image", str(generated),
                "--provider-authorized",
                "--output", str(manifest),
            ]
            self.assertEqual(subprocess.run(command, capture_output=True, text=True).returncode, 0)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], 2)
            self.assertEqual(payload["generation_purpose"], "landmark_prepaint")
            self.assertEqual(subprocess.run([sys.executable, str(validator), str(manifest)], capture_output=True, text=True).returncode, 0)
            before_output = subprocess.run([sys.executable, str(validator), str(manifest), "--require-output"], capture_output=True, text=True)
            self.assertNotEqual(before_output.returncode, 0)
            Image.new("RGB", (512, 512), "blue").save(generated)
            self.assertEqual(subprocess.run(command, capture_output=True, text=True).returncode, 0)
            completed = subprocess.run([sys.executable, str(validator), str(manifest), "--require-output"], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(payload["raw_output_metadata"]["width"], 512)
            source.write_bytes(source.read_bytes() + b"changed")
            changed = subprocess.run([sys.executable, str(validator), str(manifest)], capture_output=True, text=True)
            self.assertNotEqual(changed.returncode, 0)
            self.assertIn("source_photo SHA-256 changed", changed.stderr)

    def test_large_raw_output_requires_normalized_board_asset(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source.jpg"
            Image.new("RGB", (20, 20), "green").save(source)
            prompt = root / "prompt.md"
            prompt.write_text("[LANDMARK_SIMPLIFICATION_LOCK_BEGIN]\nx\n[LANDMARK_SIMPLIFICATION_LOCK_END]", encoding="utf-8")
            report = self.write_report(root)
            generated = root / "large.png"
            Image.new("RGB", (1536, 1536), "blue").save(generated)
            manifest = root / "manifest.json"
            command = [
                sys.executable, str(SKILL_DIR / "scripts" / "build_landmark_generation_manifest.py"),
                "--task-id", "x", "--checkpoint-number", "1", "--checkpoint-name", "x",
                "--source-photo", str(source), "--prompt-file", str(prompt), "--provider", "builtin",
                "--model", "tool-managed/unknown", "--selection-method", "runtime_tool_schema",
                "--capability-report", str(report), "--style", "plain", "--must-preserve", "shape",
                "--privacy-treatment", "remove people", "--output-image", str(generated),
                "--provider-authorized", "--provider-max-reference-images", "1", "--output", str(manifest),
            ]
            self.assertEqual(subprocess.run(command, capture_output=True, text=True).returncode, 0)
            result = subprocess.run([sys.executable, str(SKILL_DIR / "scripts" / "validate_landmark_generation_manifest.py"), str(manifest), "--require-output"], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("normalized board asset", result.stderr)

    def test_zero_reference_capacity_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source.jpg"
            Image.new("RGB", (20, 20), "green").save(source)
            prompt = root / "prompt.md"
            prompt.write_text("[LANDMARK_SIMPLIFICATION_LOCK_BEGIN]\nx\n[LANDMARK_SIMPLIFICATION_LOCK_END]", encoding="utf-8")
            report = self.write_report(root, capacity=0)
            result = subprocess.run(
                [
                    sys.executable, str(SKILL_DIR / "scripts" / "build_landmark_generation_manifest.py"),
                    "--task-id", "x", "--checkpoint-number", "1", "--checkpoint-name", "x",
                    "--source-photo", str(source), "--prompt-file", str(prompt), "--provider", "builtin",
                    "--model", "tool-managed/unknown", "--selection-method", "runtime_tool_schema",
                    "--capability-report", str(report), "--style", "plain", "--must-preserve", "shape",
                    "--privacy-treatment", "remove people", "--output-image", str(root / "out.png"),
                    "--provider-authorized", "--provider-max-reference-images", "0", "--output", str(root / "manifest.json"),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("at least one reference image", result.stderr)

    def test_manifest_capacity_cannot_exceed_capability_report(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source.jpg"
            Image.new("RGB", (20, 20), "green").save(source)
            prompt = root / "prompt.md"
            prompt.write_text("[LANDMARK_SIMPLIFICATION_LOCK_BEGIN]\nx\n[LANDMARK_SIMPLIFICATION_LOCK_END]", encoding="utf-8")
            report = self.write_report(root, capacity=0)
            result = subprocess.run(
                [
                    sys.executable, str(SKILL_DIR / "scripts" / "build_landmark_generation_manifest.py"),
                    "--task-id", "x", "--checkpoint-number", "1", "--checkpoint-name", "x",
                    "--source-photo", str(source), "--prompt-file", str(prompt), "--provider", "builtin",
                    "--model", "tool-managed/unknown", "--selection-method", "runtime_tool_schema",
                    "--capability-report", str(report), "--style", "plain", "--must-preserve", "shape",
                    "--privacy-treatment", "remove people", "--output-image", str(root / "out.png"),
                    "--provider-authorized", "--provider-max-reference-images", "1", "--output", str(root / "manifest.json"),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("exceeds capability report", result.stderr)


if __name__ == "__main__":
    unittest.main()
