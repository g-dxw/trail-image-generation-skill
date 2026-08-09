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

    def test_workflow_keeps_prompt_and_image_generation_as_separate_gates(self):
        content = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        expected = [
            "基础信息确认无误",
            "打卡点和标志性图片确认无误",
            "generate_contour_reference.py",
            "生图所用基础信息摘要",
            "生图画面规格确认无误",
            "为每张图片生成一份独立提示词",
            "全部确认，开始生图",
        ]
        positions = [content.index(value) for value in expected]
        self.assertEqual(positions, sorted(positions))

    def test_route_svg_avoids_backslash_inside_fstring_expression(self):
        source = (SKILL_DIR / "scripts" / "route_to_svg.py").read_text(encoding="utf-8")
        self.assertNotIn("{''.join(f'", source)


if __name__ == "__main__":
    unittest.main()
