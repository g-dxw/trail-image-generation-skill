# 案例三：五台山

> 当前版本是案例模板。仓库中尚未包含五台山的原始 GPX、KML 或 KMZ，因此不预填距离、爬升、海拔、时间和正式点位名称。

## 使用方式

将轨迹包放在本地后运行：

```bash
python3 scripts/inspect_kmz.py wutaishan.kmz --output-dir route-work
python3 scripts/route_to_svg.py wutaishan.kmz --output-dir route-work --width 900 --height 1200
python3 scripts/detect_checkpoint_candidates.py wutaishan.kmz --output route-work/checkpoints.json
```

随后依据生成结果填写：

- 路线类型、起点、终点和行进方向
- 距离、累计爬升、最高/最低海拔和总用时
- 五台山具体寺庙、垭口、山脊和补给点的正式名称
- 每个点位的主照片、代表性特征和隐私处理状态

## 提示词骨架

> 中国山地徒步旅行路线信息图，竖版构图，保留五台山原始轨迹的真实几何和行进方向；以山脊、寺庙、草坡、石阶和云雾作为地标插图，但只使用已经从轨迹、照片或用户说明确认的场景；编号沿行进方向递增，路线线条清晰置于视觉中心。不要擅自把候选热点命名为具体寺庙，不要把非闭环路线补成装饰性闭环，不要复制参考截图中的底图、地图标签或手机界面。

## 需要确认后才能进入生图的内容

`五台山路线事实确认`、`点位顺序确认`、`主照片确认`、`路线截图几何确认`、`打卡点和标志性图片确认无误`。
