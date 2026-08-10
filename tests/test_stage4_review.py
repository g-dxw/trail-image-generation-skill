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
| 背景环境 | 无 | 待用户确认 |
| 地标连接方式 | 默认无连线 | 待用户确认 |
| 图片编号 | 图片名称 | 用途 |
|---|---|---|
| 图01 | 测试路线总览 | 小红书总览 |

### 逐图完整画面规格
#### 图01 测试路线总览
| 项目 | 完整设置 |
|---|---|
| P0 几何 | 开放路线，严格遵循轨迹 |
| P1 内容 | 标题和手绘地标 |
| 背景环境 | 无 |
| 地标连接方式 | 默认无引导连线 |
| 地标简化状态 | 无照片跳过 |
| 实际上传参考图 | /tmp/route.png = route_geometry |
| 地标参考板编号映射 | 无 |
| 素材事实来源（不上传） | 无 |
| 校验资产（不上传） | /tmp/route.svg 和 /tmp/route.json |
| 单图兼容分支 | 只上传轨迹 PNG |
| 验收条件 | 路线和编号清晰 |

地标简化规格状态：`skipped_no_photos`
地标简化稿状态：`not_applicable`
预绘能力报告：`skipped_no_photos`

## 十、统一视觉与轨迹规则
SVG：/tmp/route.svg
PNG：/tmp/route.png
布局 JSON：/tmp/route.json

## 十一、点位视觉来源
1 起点，AI 场景

## 十二、文案与信息
主标题：测试路线

### 路线文案调研（步骤 4.5）
#### 信息来源
| 来源编号 | 来源标题 | 来源类型 | 链接 | 发布/更新日期 | 查询日期 | 支持的结论 | 可信度 |
|---|---|---|---|---|---|---|---|
| S1 | 测试来源 | 官方 | https://example.com/route | 2026-08-01 | 2026-08-09 | 季节和安全 | 高 |
#### 筛选后的路线信息
适合时间/季节：春秋
适合人群：有基础徒步经验者
不适合人群：恶劣天气出行者
装备建议：防滑鞋和饮水
天气与路况风险：雨天湿滑
补给与饮水：自备饮水
交通或停车：出发前核实
通行限制/开放状态：出发前核实
环保与安全注意事项：不离开路线
查询日期：2026-08-09
可信度：高
#### 更新后的逐图文字
图01：春秋适合；有基础徒步经验者；雨天湿滑；自备饮水
路线文案与注意事项确认无误

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
