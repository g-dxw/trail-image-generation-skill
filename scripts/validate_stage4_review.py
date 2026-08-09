#!/usr/bin/env python3
"""Validate that a persisted route review contains a complete stage-4 plan."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


REQUIRED_HEADINGS = (
    "## 九、图片生成计划",
    "## 十、统一视觉与轨迹规则",
    "## 十一、点位视觉来源",
    "## 十二、文案与信息",
    "### 路线文案调研（步骤 4.5）",
    "#### 信息来源",
    "#### 筛选后的路线信息",
    "#### 更新后的逐图文字",
    "## 十三、生图所用基础信息摘要",
    "## 十四、生图规格确认",
)


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"review file does not exist: {path}"]
    content = path.read_text(encoding="utf-8")

    for heading in REQUIRED_HEADINGS:
        if heading not in content:
            errors.append(f"missing required heading: {heading}")
    for field in (
        "画面风格",
        "生图数量",
        "图中文字",
        "轨迹精度",
        "P0",
        "P1",
        "route_geometry",
        "SVG",
        "PNG",
        "布局 JSON",
        "适合时间/季节",
        "适合人群",
        "不适合人群",
        "装备建议",
        "天气与路况风险",
        "补给与饮水",
        "交通或停车",
        "通行限制/开放状态",
        "环保与安全注意事项",
        "查询日期",
        "可信度",
        "路线文案与注意事项确认无误",
    ):
        if field not in content:
            errors.append(f"missing stage-4 field: {field}")
    if not re.search(r"\|\s*图\d+\s*\|", content):
        errors.append("no image task row found")
    if not re.search(r"####\s*图\d+", content):
        errors.append("no per-image complete specification found")
    if not re.search(r"https?://", content) and "未找到可确认资料" not in content:
        errors.append("route copy research has neither a source URL nor an explicit no-reliable-source result")

    placeholder_patterns = (
        r"<[^>]+>",
        r"待补充",
        r"见前文",
        r"沿用共享设置",
        r"按核对单执行",
    )
    for pattern in placeholder_patterns:
        if re.search(pattern, content):
            errors.append(f"unresolved placeholder or shorthand: {pattern}")
    if re.search(r"\|[ \t]*\|", content):
        errors.append("empty table cell found")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review_file", type=Path)
    args = parser.parse_args()
    path = args.review_file.expanduser().resolve()
    errors = validate(path)
    if errors:
        raise SystemExit("stage-4 review validation failed:\n- " + "\n- ".join(errors))
    print("stage-4 review validation passed")


if __name__ == "__main__":
    main()
