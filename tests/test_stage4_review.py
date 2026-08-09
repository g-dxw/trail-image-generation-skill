from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from validate_stage4_review import validate  # noqa: E402


COMPLETE_REVIEW = """# 测试路线核对单

## 九、图片生成计划
| 必确认项 | 当前设置 | 状态 |
|---|---|---|
| 画面风格 | 手绘旅行地图 | 待用户确认 |
| 生图数量 | 1 张 | 待用户确认 |
| 图中文字 | 标题：测试路线 | 待用户确认 |
| 轨迹精度 | 精确轨迹 | 待用户确认 |
| 图片编号 | 图片名称 | 用途 |
|---|---|---|
| 图01 | 测试路线总览 | 小红书总览 |

### 逐图完整画面规格
#### 图01 测试路线总览
| 项目 | 完整设置 |
|---|---|
| P0 几何 | 开放路线，严格遵循轨迹 |
| P1 内容 | 标题和手绘地标 |
| 参考图角色 | /tmp/route.png = route_geometry |
| 验收条件 | 路线和编号清晰 |

## 十、统一视觉与轨迹规则
SVG：/tmp/route.svg
PNG：/tmp/route.png
布局 JSON：/tmp/route.json

## 十一、点位视觉来源
1 起点，AI 场景

## 十二、文案与信息
主标题：测试路线

## 十三、生图所用基础信息摘要
路线事实：开放路线

## 十四、生图规格确认
回复：生图画面规格确认无误
"""


class Stage4ReviewTests(unittest.TestCase):
    def test_complete_persisted_review_passes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "测试路线-路线核对单.md"
            path.write_text(COMPLETE_REVIEW, encoding="utf-8")
            self.assertEqual(validate(path), [])

    def test_chat_style_summary_and_placeholders_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "测试路线-路线核对单.md"
            path.write_text("## 九、图片生成计划\n画面风格：<待填写>\n", encoding="utf-8")
            errors = validate(path)
            self.assertTrue(any("missing required heading" in error for error in errors))
            self.assertTrue(any("unresolved placeholder" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
