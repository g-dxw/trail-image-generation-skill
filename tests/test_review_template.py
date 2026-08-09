from __future__ import annotations

import unittest
from pathlib import Path


TEMPLATE = Path(__file__).resolve().parents[1] / "references" / "review-template.md"


class ReviewTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = TEMPLATE.read_text(encoding="utf-8")
        cls.default_content, cls.advanced_content = cls.content.split("## 按需高级核对附录", 1)

    def test_basic_information_and_intensity_are_preserved(self):
        self.assertIn("## 一、路线基本信息", self.default_content)
        self.assertIn("## 四、路线强度", self.default_content)
        self.assertIn("基础信息确认无误", self.default_content)

    def test_second_stage_is_checkpoint_and_primary_photo_only(self):
        self.assertIn("## 阶段二：打卡点与标志性主图", self.default_content)
        self.assertIn("| 编号 | 打卡点名称 | 标志性主图 | 必须保留的特征 | 辅助图（可选） |", self.default_content)
        self.assertIn("打卡点和标志性图片确认无误", self.default_content)
        self.assertNotIn("候选路线分段", self.default_content)
        self.assertNotIn("照片行程顺序", self.default_content)

    def test_advanced_capabilities_remain_available(self):
        self.assertIn("路线结构与分段", self.advanced_content)
        self.assertIn("完整照片顺序与内容", self.advanced_content)
        self.assertIn("候选点与最终点位属性", self.advanced_content)
        self.assertIn("不编号的路线过程", self.advanced_content)

    def test_checkpoint_first_scope_is_decided_in_plan(self):
        self.assertIn("是否包含或跳过总览图必须在图片生成计划中明确", self.default_content)
        self.assertIn("全部确认，只生成提示词", self.default_content)

    def test_image_spec_stage_has_explicit_summary_and_confirmation_gate(self):
        self.assertIn("## 十三、生图所用基础信息摘要", self.default_content)
        self.assertIn("路线事实", self.default_content)
        self.assertIn("路线几何", self.default_content)
        self.assertIn("等高线参考", self.default_content)
        self.assertIn("必须在当前阶段把上述摘要实际展示给用户", self.default_content)
        self.assertIn("## 十四、生图规格确认", self.default_content)
        self.assertIn("生图画面规格确认无误", self.default_content)


if __name__ == "__main__":
    unittest.main()
