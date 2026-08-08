---
name: trail-image-generation
description: 将 GPX、KML 或 KMZ 徒步/旅行轨迹转换为可核对的路线资料、打卡点方案和一致的生图提示词；先核对事实与点位，再执行图像生成。
---

# 轨迹生图 Skill

完整工作流与约束见 `README.md` 及 `references/`。执行时必须先读取原始轨迹、生成路线骨架和候选点，再创建路线核对单；用户确认“打卡点和标志性图片确认无误”后，才编写最终提示词或生成图片。

核心脚本：`inspect_kmz.py`、`route_to_svg.py`、`detect_checkpoint_candidates.py`、`route_intensity.py`。
