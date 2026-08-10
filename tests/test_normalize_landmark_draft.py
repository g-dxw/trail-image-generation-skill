from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SKILL_DIR = Path(__file__).resolve().parents[1]


class NormalizeLandmarkDraftTests(unittest.TestCase):
    def test_normalizes_deterministically_to_512_square(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source.png"
            output1 = root / "one.png"
            output2 = root / "two.png"
            Image.new("RGB", (1024, 768), "orange").save(source)
            base = [
                sys.executable,
                str(SKILL_DIR / "scripts" / "normalize_landmark_draft.py"),
                str(source),
            ]
            for output in (output1, output2):
                result = subprocess.run(base + ["--output", str(output)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            with Image.open(output1) as image:
                self.assertEqual(image.size, (512, 512))
            self.assertEqual(hashlib.sha256(output1.read_bytes()).hexdigest(), hashlib.sha256(output2.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
