from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from render_route_preview import render  # noqa: E402


class RoutePreviewTests(unittest.TestCase):
    def write_layout(self, folder: str, checkpoints: list[dict]) -> tuple[Path, Path]:
        layout = Path(folder) / "route-轨迹布局.json"
        output = Path(folder) / "route-轨迹预览.png"
        layout.write_text(
            json.dumps(
                {
                    "canvas": {"width": 120, "height": 160},
                    "closed": False,
                    "simplified_points": [{"x": 20, "y": 20}, {"x": 100, "y": 140}],
                    "simplified_progress": [0.0, 1.0],
                    "checkpoints": checkpoints,
                }
            ),
            encoding="utf-8",
        )
        return layout, output

    def test_renders_valid_png_with_expected_dimensions(self):
        checkpoint = {"number": 1, "track_progress": 0.0, "anchor": {"x": 20, "y": 20}}
        with tempfile.TemporaryDirectory() as folder:
            layout, output = self.write_layout(folder, [checkpoint])
            render(layout, output)
            content = output.read_bytes()
        self.assertEqual(content[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", content[16:24])
        self.assertEqual((width, height), (120, 160))

    def test_final_preview_rejects_missing_checkpoints(self):
        with tempfile.TemporaryDirectory() as folder:
            layout, output = self.write_layout(folder, [])
            with self.assertRaisesRegex(ValueError, "no numbered checkpoints"):
                render(layout, output)

    def test_segment_render_keeps_valid_png(self):
        checkpoints = [
            {"number": 9, "track_progress": 0.66, "anchor": {"x": 55, "y": 80}},
            {"number": 10, "track_progress": 0.68, "anchor": {"x": 60, "y": 90}},
        ]
        with tempfile.TemporaryDirectory() as folder:
            layout, output = self.write_layout(folder, checkpoints)
            render(layout, output, progress_start=0.6, progress_end=0.8)
            self.assertEqual(output.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    unittest.main()
