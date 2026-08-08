# 高级路线核对模板

Use this reference only when the user requests detailed route/photo analysis or when ambiguity blocks checkpoint selection or route-map generation. Append the required sections to the existing review file; do not restart the default workflow.

## 路线结构与分段

```markdown
## 高级 A｜路线整体结构

| 项目 | 信息 |
|---|---|
| 路线类型 | `<环线/穿越线/往返线>` |
| 行进方向 | `<描述>` |
| 是否形成闭环 | `<是/否>` |
| 是否存在折返 | `<是/否>` |
| 是否存在重复路段 | `<是/否>` |
| 是否存在明显分支 | `<是/否>` |
| 建议路段数量 | `<数量>` |

行程顺序：`<起点> → <过程节点> → <终点>`

整体过程：`<爬升、平缓、山脊起伏、下降等>`

### 候选路线分段

#### 第一段：<名称>

| 项目 | 信息 |
|---|---|
| 起点 | `<位置>` |
| 终点 | `<位置>` |
| 轨迹进度 | `<范围>` |
| 距离 | `<距离>` |
| 海拔变化 | `<变化>` |
| 海拔趋势 | `<上升/下降/起伏/平缓>` |
| 主要路况 | `<内容>` |
| 对应照片 | `<照片>` |

路段说明：`<描述>`

### 重要路线边界

| 顺序 | 边界位置 | 轨迹进度 | 边界依据 |
|---:|---|---:|---|
| 1 | `<位置>` | `<进度>` | `<海拔、路况或方向变化>` |

路线边界不自动成为编号打卡点。

### 路线结构确认

请检查行进方向、路线顺序、路段数量和分段边界。如果信息没有问题，请回复：`高级路线结构确认无误`
```

## 完整照片顺序与内容

Sort photos by matched track progress. Group consecutive photos from the same place. Keep time, coordinates, and matching evidence internal unless needed to resolve an ambiguity.

默认先展示元数据带标注或用户指定的照片。未标注照片只保留坐标、时间、轨迹进度和热点统计，不逐张解析；只有进入候选热点照片组后，才在用户请求下补充视觉分析。

```markdown
## 高级 B0｜照片预筛选

| 照片 | 分析状态 | 标注来源 | 轨迹进度 | 热点依据 | 跳过原因 |
|---|---|---|---:|---|---|
| `<照片>` | `<labeled/unlabeled/hotspot_only/selected/skipped>` | `<kml_name/user_confirmed/photo_group/无>` | `<进度>` | `<照片密集/局部折返/无>` | `<默认跳过逐张视觉解析/无>` |

当前策略：`metadata_labeled_first`

如需补充解析，可选择：`解析全部照片`、`只解析指定照片`、`解析某个候选热点照片组`。
```

```markdown
## 高级 B｜照片行程顺序

| 顺序 | 照片或照片组 | 轨迹进度 | 临时场景名称 |
|---:|---|---:|---|
| 1 | `<照片>` | `<进度>` | `<名称>` |

## 照片内容

### 照片 01

![照片01](<相对路径>)

- 画面内容：`<实际可见内容>`
- 已识别文字：`<文字或无>`

### 照片 02—04

![照片02](<相对路径>)

- 共同场景：`<实际可见内容>`
- 已识别文字：`<文字或无>`

### 完整照片确认

请检查照片顺序、分组、可见内容和识别文字。如果信息没有问题，请回复：`高级照片内容确认无误`
```

## 候选点与最终点位属性

Use temporary scene names when reliable names are unavailable. Do not query a map or invent formal landmark names solely from appearance.

```markdown
## 高级 C｜候选打卡点

| 顺序 | 候选名称 | 轨迹进度 | 海拔 | 照片 | 候选依据 | 展示建议 |
|---:|---|---:|---:|---|---|---|
| 1 | `<名称>` | `<进度>` | `<海拔>` | `<照片>` | `<依据>` | `<保留/可选/不建议>` |

自动候选的依据可包括：`照片密集`、`轨迹异常聚集`、`局部折返`、`明显停留`、`来源命名`、`用户已确认`。轨迹信号只表示值得重点查看，不得单独推断洞穴、天坑或休息点名称。

## 最终展示点位属性

| 编号 | 点位名称 | 所属路段 | 轨迹进度 | 场景属性 | 功能标签 | 参考照片 |
|---:|---|---|---:|---|---|---|
| 1 | `<名称>` | `<路段>` | `<进度>` | `<场景属性>` | `<一个或多个标签>` | `<照片>` |

### 1. <点位名称>

- 场景属性：`<自然风景、山峰、岩壁、森林、村落、建筑等>`
- 功能标签：`<起点、终点、拍照、补给、休息、停车、导航、风险等>`
- 画面场景：`<照片与用户说明>`
- 可用补给：`<只在用户确认后填写>`
- 安全提示：`<只在相关且已确认时填写>`
- 关键特征：`<生图必须保留>`
- 避免生成：`<容易画错的内容>`
- 参考照片：`<照片>`

### 最终点位属性确认

请检查点位属性、功能标签、补给、安全信息和详细场景。如果信息没有问题，请回复：`高级点位属性确认无误`
```

Only include supply fields for confirmed supply/water points. Only include safety fields when relevant. Treat access status, drinking-water suitability, parking, and supplies as user knowledge or external facts, not visual inference.

## 不编号的路线过程

```markdown
## 高级 D｜不编号的路线过程

| 路线过程 | 所属路段 | 说明 |
|---|---|---|
| `<名称>` | `<路段>` | `<作为环境或分段边界，不显示编号>` |
```

Use this for junctions, generic slopes, highest points, segment boundaries, route closures, and environmental transitions that should not become numbered checkpoints.
