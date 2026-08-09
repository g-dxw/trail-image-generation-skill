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
                    "checkpoints": checkpoints,
                }
            ),
            encoding="utf-8",
        )
        return layout, output

    def test_renders_valid_png_with_expected_dimensions(self):
        checkpoint = {"number": 1, "anchor": {"x": 20, "y": 20}}
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


if __name__ == "__main__":
    unittest.main()
