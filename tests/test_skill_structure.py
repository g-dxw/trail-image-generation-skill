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

    def test_final_workflow_requires_numbered_route_svg(self):
        content = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("route_to_svg.py --checkpoints-json", content)
        self.assertIn("SVG 路线骨架、PNG 路线预览、布局 JSON 和其全部编号标注点", content)
        self.assertIn("render_route_preview.py", content)
        self.assertIn("PNG 路线预览", content)
        self.assertNotIn("generate_contour_reference.py", content)

    def test_workflow_keeps_prompt_and_image_generation_as_separate_gates(self):
        content = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        expected = [
            "基础信息确认无误",
            "打卡点和标志性图片确认无误",
            "route_to_svg.py --checkpoints-json",
            "路线文案与注意事项确认无误",
            "生图所用基础信息摘要",
            "生图画面规格确认无误",
            "为每张图片生成一份独立、完整、可直接调用的最终提示词",
            "生图提示词确认无误",
            "提示词确认后展示生成方式选择",
        ]
        positions = [content.index(value) for value in expected]
        self.assertEqual(positions, sorted(positions))

    def test_prompt_completion_requires_user_selected_generation_mode(self):
        content = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("直接生成完整效果图", content)
        self.assertIn("不使用 SVG 后期确定性叠加", content)
        self.assertIn("只保留提示词", content)
        self.assertIn("不根据模型名称自动判断强弱", content)
        self.assertIn("不默认执行任何一种生成方式", content)

    def test_provider_selection_is_runtime_discovered_without_secret_storage(self):
        content = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        example = (SKILL_DIR / "assets" / "provider-config.example.json").read_text(encoding="utf-8")
        self.assertIn("tool-managed/unknown", content)
        self.assertIn("build_image_capability_report.py", content)
        self.assertIn("landmark_prepaint", content)
        self.assertIn("route_final", content)
        self.assertIn("使用已配置中转站", content)
        self.assertIn('"api_key_env"', example)
        self.assertNotIn('"api_key"', example)

    def test_readme_matches_runtime_workflow(self):
        readme = (SKILL_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("--checkpoints-json", readme)
        self.assertIn("build_image_capability_report.py", readme)
        self.assertIn("normalize_landmark_draft.py", readme)
        self.assertIn("--capability-report", readme)
        self.assertIn("<路线名称>-路线核对单.md", readme)
        self.assertNotIn("<路线名>-路线核对.md", readme)
        self.assertIn("实际像素如实记录", readme)

    def test_stage_four_gate_is_mandatory(self):
        content = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("画面风格", content)
        self.assertIn("生图数量", content)
        self.assertIn("默认 `1 张`", content)
        self.assertIn("图中文字", content)
        self.assertIn("轨迹精度", content)
        self.assertIn("不得生成独立提示词", content)
        self.assertIn("聊天消息不能替代核对单文件", content)
        self.assertIn("validate_stage4_review.py", content)
        self.assertIn("核对单持久化合同", content)
        self.assertIn("路线文案与注意事项确认无误", content)

    def test_prompt_review_gate_requires_complete_locked_prompts(self):
        content = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        rules = (SKILL_DIR / "references" / "prompt-rules.md").read_text(encoding="utf-8")
        self.assertIn("生图提示词确认无误", content)
        self.assertIn("不得使用“同上”", content)
        self.assertIn("[GEOMETRY_LOCK_BEGIN]", rules)
        self.assertIn("[TEXT_LOCK_BEGIN]", rules)
        self.assertIn("验收清单：", rules)

    def test_landmark_prepaint_and_two_image_contract(self):
        content = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        rules = (SKILL_DIR / "references" / "prompt-rules.md").read_text(encoding="utf-8")
        self.assertIn("地标简化规格确认无误", content)
        self.assertIn("地标简化稿确认无误", content)
        self.assertIn("landmark_reference_board", content)
        self.assertIn("最终每个路线图任务最多上传两张图", content)
        self.assertIn("[LANDMARK_SIMPLIFICATION_LOCK_BEGIN]", rules)
        self.assertIn("实际上传参考图：", rules)
        self.assertIn("素材事实来源（不上传）：", rules)
        self.assertIn("点位完整性：", rules)
        self.assertIn("点位对应：", rules)
        self.assertIn("地标连接方式：", rules)
        self.assertIn("Do not draw connector lines by default", rules)
        self.assertIn("must still list every confirmed string verbatim", rules)
        self.assertIn("Clean route-map composition default", rules)
        self.assertIn("low contrast and atmospheric perspective", rules)

    def test_route_svg_avoids_backslash_inside_fstring_expression(self):
        source = (SKILL_DIR / "scripts" / "route_to_svg.py").read_text(encoding="utf-8")
        self.assertNotIn("{''.join(f'", source)
        self.assertIn("--start-label", source)
        self.assertIn("--finish-label", source)
        self.assertIn('"endpoints": endpoints', source)


if __name__ == "__main__":
    unittest.main()
