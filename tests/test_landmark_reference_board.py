from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from build_landmark_reference_board import BOARD_SIZE, crop_to_tile, grid_for, render_board  # noqa: E402


class LandmarkReferenceBoardTests(unittest.TestCase):
    def make_items(self, root: Path, count: int) -> list[dict]:
        items = []
        for number in range(1, count + 1):
            path = root / f"landmark-{number}.png"
            Image.new("RGB", (120 + number, 80 + number), (20 * number % 255, 80, 140)).save(path)
            items.append(
                {
                    "checkpoint_number": number,
                    "checkpoint_name": f"point-{number}",
                    "path": str(path),
                    "focus_x": 0.35,
                    "focus_y": 0.65,
                    "approved": True,
                }
            )
        return items

    def test_adaptive_grids(self):
        self.assertEqual(grid_for(1), (2, 2))
        self.assertEqual(grid_for(4), (2, 2))
        self.assertEqual(grid_for(6), (3, 2))
        self.assertEqual(grid_for(9), (3, 3))
        self.assertEqual(grid_for(12), (4, 3))

    def test_board_is_deterministic_and_numbered(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            items = self.make_items(root, 12)
            first = render_board(items, root / "first.png")
            second = render_board(items, root / "second.png")
            self.assertEqual(first["sha256"], second["sha256"])
            self.assertEqual(first["size"], list(BOARD_SIZE))
            self.assertEqual(first["grid"], {"columns": 4, "rows": 3})
            self.assertEqual([item["checkpoint_number"] for item in first["items"]], list(range(1, 13)))

    def test_exif_orientation_is_applied_before_focal_crop(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "rotated.jpg"
            image = Image.new("RGB", (40, 20), "red")
            exif = image.getexif()
            exif[274] = 6
            image.save(path, exif=exif)
            with Image.open(path) as source:
                _, _, source_size = crop_to_tile(source, (100, 100), 0.5, 0.5)
            self.assertEqual(source_size, [20, 40])

    def test_review_mode_splits_more_than_twelve_and_final_rejects(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = root / "spec.json"
            spec.write_text(json.dumps({"items": self.make_items(root, 13)}), encoding="utf-8")
            script = SKILL_DIR / "scripts" / "build_landmark_reference_board.py"
            review = subprocess.run(
                [sys.executable, str(script), str(spec), "--mode", "review", "--output", str(root / "review.png"), "--sidecar", str(root / "review.json")],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(review.returncode, 0, review.stderr)
            self.assertTrue((root / "review-01.png").is_file())
            self.assertTrue((root / "review-02.png").is_file())
            final = subprocess.run(
                [sys.executable, str(script), str(spec), "--mode", "final", "--output", str(root / "final.png"), "--sidecar", str(root / "final.json")],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(final.returncode, 0)
            self.assertIn("at most 12", final.stderr)


if __name__ == "__main__":
    unittest.main()
