from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from generate_contour_reference import generate  # noqa: E402


SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 1200">
<rect width="100%" height="100%" fill="#fff"/>
<path id="route-underlay" d="M 100 100 L 800 1000" fill="none"/>
<circle cx="100" cy="100" r="8"/><text x="100" y="104">1</text>
</svg>
"""


class ContourReferenceTests(unittest.TestCase):
    def write_inputs(self, folder: str, checkpoints: list[dict]) -> tuple[Path, Path, Path]:
        root = Path(folder)
        layout = root / "route-轨迹布局.json"
        route_svg = root / "route-轨迹骨架.svg"
        output = root / "route-轨迹等高线参考.svg"
        layout.write_text(
            json.dumps(
                {
                    "simplified_points": [{"x": 100, "y": 100}, {"x": 800, "y": 1000}],
                    "checkpoints": checkpoints,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        route_svg.write_text(SVG, encoding="utf-8")
        return layout, route_svg, output

    def test_generates_contours_and_preserves_numbered_route_layer(self):
        with tempfile.TemporaryDirectory() as folder:
            layout, route_svg, output = self.write_inputs(folder, [{"number": 1, "name": "起点"}])
            generate(layout, route_svg, output, count=5)
            content = output.read_text(encoding="utf-8")
            manifest = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertIn('id="schematic-contours"', content)
        self.assertIn('id="route-underlay"', content)
        self.assertIn(">1</text>", content)
        self.assertEqual(manifest["numbered_checkpoint_count"], 1)
        self.assertEqual(manifest["contour_type"], "schematic_non_dem")

    def test_final_reference_rejects_missing_checkpoints(self):
        with tempfile.TemporaryDirectory() as folder:
            layout, route_svg, output = self.write_inputs(folder, [])
            with self.assertRaisesRegex(ValueError, "no numbered checkpoints"):
                generate(layout, route_svg, output, count=5)


if __name__ == "__main__":
    unittest.main()
