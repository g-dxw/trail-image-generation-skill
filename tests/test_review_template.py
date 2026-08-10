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
        self.assertIn("直接生成完整效果图", self.default_content)
        self.assertIn("不用 SVG 后期确定性叠加修正轨迹", self.default_content)
        self.assertIn("只保留提示词", self.default_content)
        self.assertIn("未选择前不得生图", self.default_content)

    def test_image_spec_stage_has_explicit_summary_and_confirmation_gate(self):
        self.assertIn("## 十三、生图所用基础信息摘要", self.default_content)
        self.assertIn("路线事实", self.default_content)
        self.assertIn("路线几何", self.default_content)
        self.assertIn("路线几何", self.default_content)
        self.assertIn("必须在当前阶段把上述摘要实际展示给用户", self.default_content)
        self.assertIn("## 十四、生图规格确认", self.default_content)
        self.assertIn("生图画面规格确认无误", self.default_content)

    def test_stage_four_requires_style_count_text_and_fidelity(self):
        self.assertIn("第 4 阶段四个必确认项", self.default_content)
        self.assertIn("| 画面风格 |", self.default_content)
        self.assertIn("| 生图数量 | `1 张`", self.default_content)
        self.assertIn("| 图中文字 |", self.default_content)
        self.assertIn("| 轨迹精度 | `精确轨迹/严格遵循轨迹`", self.default_content)
        self.assertIn("风格、数量、图中文字和轨迹精度确认无误", self.default_content)
        self.assertIn("默认只规划图01，共 1 张", self.default_content)
        self.assertIn("Skill 不主动推荐或默认其中一种", self.default_content)
        self.assertNotIn("优先选择“模型预留区域，后期添加正确文字”", self.default_content)

    def test_complete_prompt_requires_explicit_user_review(self):
        self.assertIn("逐张完整展示最终生图提示词", self.default_content)
        self.assertIn("生图提示词确认无误", self.default_content)
        self.assertIn("原确认失效", self.default_content)
        self.assertIn("[TEXT_LOCK_BEGIN]", self.default_content)

    def test_landmark_simplification_has_separate_gates(self):
        self.assertIn("## 阶段二点五：地标简化规格与审核板", self.default_content)
        self.assertIn("地标简化规格确认无误", self.default_content)
        self.assertIn("地标简化稿确认无误", self.default_content)
        self.assertIn("每次只向中间生图模型上传一张", self.default_content)
        self.assertIn("实际上传参考图", self.default_content)
        self.assertIn("素材事实来源（不上传）", self.default_content)
        self.assertIn("校验资产（不上传）", self.default_content)
        self.assertIn("单图兼容分支", self.default_content)

    def test_stage_four_is_a_persisted_document_gate(self):
        self.assertIn("## 阶段四：图片生成计划与画面规格", self.default_content)
        self.assertIn("same file", self.default_content)
        self.assertIn("validate_stage4_review.py", self.default_content)
        self.assertIn("逐图完整画面规格", self.default_content)
        self.assertIn("A Markdown block shown only in chat does not satisfy this stage", self.default_content)

    def test_stage_four_requires_route_copy_research_before_summary(self):
        self.assertIn("路线文案调研（步骤 4.5）", self.default_content)
        self.assertIn("适合时间/季节", self.default_content)
        self.assertIn("适合人群", self.default_content)
        self.assertIn("注意事项", self.default_content)
        self.assertIn("路线文案与注意事项确认无误", self.default_content)


if __name__ == "__main__":
    unittest.main()
