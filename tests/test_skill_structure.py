from __future__ import annotations

import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]


class SkillStructureTests(unittest.TestCase):
    def test_skill_name_matches_repository_folder(self):
        content = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(f"name: {SKILL_DIR.name}", content)

    def test_openai_metadata_uses_current_skill_name(self):
        metadata = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn(f"${SKILL_DIR.name}", metadata)
        self.assertNotIn("$trail-image-prompt", metadata)

    def test_final_workflow_requires_contour_generator(self):
        content = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("generate_contour_reference.py", content)
        self.assertIn("缺少点位", content)


if __name__ == "__main__":
    unittest.main()
