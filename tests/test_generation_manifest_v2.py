from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SKILL_DIR = Path(__file__).resolve().parents[1]


PROMPT = """[GEOMETRY_LOCK_BEGIN]\nP0 禁止重画\n[GEOMETRY_LOCK_END]
[TEXT_LOCK_BEGIN]\n无文字\n[TEXT_LOCK_END]
实际上传参考图：route geometry and optional landmark board
地标参考板编号映射：1 → point one
点位完整性：本图共1个点位，必须显示1
点位对应：轨迹锚点1、名称和地标一一对应
地标连接方式：默认无引导连线，通过编号和邻近布局对应
素材事实来源（不上传）：source.jpg
校验资产（不上传）：route.svg and layout.json
单图兼容分支：only route PNG and confirmed text features
负面约束：wrong route
验收清单：route and landmark
"""


class GenerationManifestV2Tests(unittest.TestCase):
    def create_assets(self, root: Path):
        prompt = root / "prompt.md"
        prompt.write_text(PROMPT, encoding="utf-8")
        route_png = root / "route.png"
        Image.new("RGB", (30, 40), "white").save(route_png)
        route_svg = root / "route.svg"
        route_svg.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
        layout = root / "layout.json"
        layout.write_text(
            json.dumps(
                {
                    "closed": False,
                    "simplified_progress": [0.0, 1.0],
                    "checkpoints": [{"number": 1, "name": "point one", "track_progress": 0.0, "anchor": {"x": 1, "y": 2}}],
                }
            ),
            encoding="utf-8",
        )
        source = root / "source.jpg"
        Image.new("RGB", (60, 60), "red").save(source)
        simplified = root / "simplified.png"
        Image.new("RGB", (80, 80), "green").save(simplified)
        generation_manifest = root / "landmark-generation.json"
        generation_manifest.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "generation_purpose": "landmark_prepaint",
                    "provider_authorized": True,
                    "output_image": str(simplified.resolve()),
                    "output_sha256": hashlib.sha256(simplified.read_bytes()).hexdigest(),
                }
            ),
            encoding="utf-8",
        )
        board_spec = root / "board-spec.json"
        board_spec.write_text(
            json.dumps({"items": [{"checkpoint_number": 1, "checkpoint_name": "point one", "path": str(simplified), "generation_manifest": str(generation_manifest), "focus_x": 0.5, "focus_y": 0.5, "approved": True}]}),
            encoding="utf-8",
        )
        board = root / "board.png"
        sidecar = root / "board.json"
        board_result = subprocess.run(
            [sys.executable, str(SKILL_DIR / "scripts" / "build_landmark_reference_board.py"), str(board_spec), "--mode", "final", "--output", str(board), "--sidecar", str(sidecar)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(board_result.returncode, 0, board_result.stderr)
        return prompt, route_png, route_svg, layout, source, board, sidecar

    def build_command(self, root: Path, capacity: int, allow_fallback: bool = False):
        prompt, route_png, route_svg, layout, source, board, sidecar = self.create_assets(root)
        report = root / "final-capabilities.json"
        report.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "report_type": "image_capability_report",
                    "observed_at": "2026-08-10T00:00:00+00:00",
                    "executor": "premium-final",
                    "executor_type": "relay",
                    "model": "configured-final-model",
                    "capability_source": "provider_documentation",
                    "capabilities": {
                        "can_generate": True,
                        "can_use_reference_image": True,
                        "can_edit_image": True,
                        "selectable_model": True,
                        "selectable_size": False,
                        "selectable_quality": True,
                        "max_reference_images": capacity,
                        "supported_output_sizes": [],
                        "supported_quality_levels": ["high"],
                        "cost_class": "premium",
                        "quality_class": "final",
                    },
                    "evidence": ["test"],
                }
            ),
            encoding="utf-8",
        )
        command = [
            sys.executable,
            str(SKILL_DIR / "scripts" / "build_generation_manifest.py"),
            "--task-id",
            "overview",
            "--prompt-file",
            str(prompt),
            "--route-png",
            str(route_png),
            "--route-svg",
            str(route_svg),
            "--layout-json",
            str(layout),
            "--landmark-board",
            str(board),
            "--landmark-board-sidecar",
            str(sidecar),
            "--source-material",
            str(source),
            "--provider-max-reference-images",
            str(capacity),
            "--provider", "premium-final",
            "--model", "configured-final-model",
            "--selection-method", "configured",
            "--requested-quality", "high",
            "--provider-cost-class", "premium",
            "--provider-quality-class", "final",
            "--capability-report", str(report),
            "--output",
            str(root / "manifest.json"),
        ]
        if allow_fallback:
            command.append("--allow-route-only-fallback")
        return command

    def test_two_image_manifest_validates(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            build = subprocess.run(self.build_command(root, 2), capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            payload = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], 2)
            self.assertEqual([item["role"] for item in payload["actual_uploads"]], ["route_geometry", "landmark_reference_board"])
            validate = subprocess.run([sys.executable, str(SKILL_DIR / "scripts" / "validate_generation_manifest.py"), str(root / "manifest.json")], capture_output=True, text=True)
            self.assertEqual(validate.returncode, 0, validate.stderr)

    def test_single_image_fallback_must_be_explicit(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            blocked = subprocess.run(self.build_command(root, 1), capture_output=True, text=True)
            self.assertNotEqual(blocked.returncode, 0)
            allowed = subprocess.run(self.build_command(root, 1, True), capture_output=True, text=True)
            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            payload = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["reference_mode"], "route_only_fallback")
            self.assertEqual(len(payload["actual_uploads"]), 1)

    def test_zero_capacity_and_third_upload_are_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            zero = subprocess.run(self.build_command(root, 0), capture_output=True, text=True)
            self.assertNotEqual(zero.returncode, 0)
            self.assertIn("at least one reference image", zero.stderr)
            self.assertEqual(subprocess.run(self.build_command(root, 2), capture_output=True, text=True).returncode, 0)
            manifest_path = root / "manifest.json"
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["actual_uploads"].append(dict(payload["actual_uploads"][1]))
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")
            validate = subprocess.run([sys.executable, str(SKILL_DIR / "scripts" / "validate_generation_manifest.py"), str(manifest_path)], capture_output=True, text=True)
            self.assertNotEqual(validate.returncode, 0)
            self.assertIn("at most two", validate.stderr)

    def test_legacy_individual_photo_upload_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            command = self.build_command(root, 2)
            command.extend(["--reference", f"real_photo={root / 'source.jpg'}"])
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("build a landmark reference board", result.stderr)


if __name__ == "__main__":
    unittest.main()
