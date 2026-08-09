# 路线核对单模板

Create one Markdown review file and update values in place as the user corrects them. The default workflow has three user-facing stages: basic information, checkpoints with representative photos, and image specification/execution. Keep detailed route structure and photo analysis internal unless ambiguity or an explicit user request requires the advanced appendix.

## 阶段一：基础信息

```markdown
# <路线名称>路线核对单

> 原始轨迹包：`<文件名>`
> 当前阶段：`basic_info_review / 基础信息核对中`

## 一、路线基本信息

| 项目 | 信息 |
|---|---|
| 路线名称 | `<路线名称>` |
| 路线类型 | `<环线/穿越线/往返线>` |
| 起点 | `<起点名称>` |
| 终点 | `<终点名称>` |
| 开始时间 | `<时间>` |
| 结束时间 | `<时间>` |
| 总用时 | `<用时>` |
| 距离 | `<来源记录；计算候选>` |
| 累计爬升 | `<来源记录；计算候选>` |
| 累计下降 | `<来源记录；计算候选>` |
| 最低海拔 | `<最低海拔>` |
| 最高海拔 | `<最高海拔>` |
| 平均海拔 | `<平均海拔或缺失>` |
| 轨迹点数量 | `<数量>` |
| 照片数量 | `<数量>` |

## 二、起点与终点

| 项目 | 起点 | 终点 |
|---|---|---|
| 名称 | `<名称>` | `<名称>` |
| 坐标 | `<经度>, <纬度>` | `<经度>, <纬度>` |
| 海拔 | `<海拔>` | `<海拔>` |
| 附近照片 | `<照片或无>` | `<照片或无>` |

- 起终点直线距离：约 `<距离>` 米
- 路线类型判断：`<说明>`

## 三、数据来源与差异

- 距离采用：`<来源应用/轨迹计算>`
- 爬升采用：`<来源应用/清洗后轨迹计算>`
- 下降采用：`<来源应用/清洗后轨迹计算>`
- 海拔采用：`<轨迹有效海拔/缺失>`
- 明显轨迹断点：`<没有或说明>`
- 需要用户判断的差异：`<没有或说明>`

## 四、路线强度

| 项目 | 数值 |
|---|---:|
| 采用里程 | `<km>` |
| 采用爬升 | `<m>` |
| 采用下降 | `<m>` |
| 平均海拔 | `<m 或缺失>` |
| 估算负重 | `<kg>` |
| 海拔强度系数 | `<数值>` |
| 路线强度原始值 | `<数值>` |
| 路线强度 | `<保留一位小数>` |
| 强度等级 | `<休闲/初级/中级/大强度/超大强度/数据不足>` |

计算公式：

`估算负重 = 4 + 里程/10×0.5 + 爬升/1000×0.5`

`海拔强度系数 = 1 + 平均海拔/5500`

`路线强度 = (里程/10 + 爬升/1000 + 下降/1000) × 估算负重/10 × 海拔强度系数`

- 数据警告：`<没有或 route_intensity.warnings>`
- 洞穴、湿滑、临崖、施工和梯道不参与强度公式，另作为安全提示。

## 五、照片提取结果

| 项目 | 数量 |
|---|---:|
| 轨迹包内照片 | `<数量>` |
| 成功提取或下载 | `<数量>` |
| 可匹配轨迹位置 | `<数量>` |
| 损坏或无法读取 | `<数量>` |

照片目录：`<路线名称>-照片/`

## 六、基础信息确认

请检查路线名称、起终点、采用的距离/爬升/下降数据和路线强度。如果信息没有问题，请回复：`基础信息确认无误`
```

Do not add signatures, confirmation timestamps, per-field status columns, or raw metadata dumps.

## 阶段二：打卡点与标志性主图

Internally sort photos by matched track progress and retain coordinates, progress, route segments, matching evidence, and candidate history. Do not display those details in the default review.

照片默认采用“元数据标注优先”策略：先处理 KML/KMZ 中带名称或用户确认标记的照片；未标注照片只参与热点统计，不逐张做视觉解析。只有进入热点候选组或用户主动指定时，才补充解析未标注照片。

Choose exactly one primary photo per checkpoint. Add a supporting photo only when the primary photo cannot show a confirmed essential structure, such as a descent ladder belonging to a sinkhole. Prefer the user's firsthand naming and photo choice.

```markdown
## 七、打卡点与标志性图片

| 编号 | 打卡点名称 | 标志性主图 | 必须保留的特征 | 辅助图（可选） |
|---:|---|---|---|---|
| 1 | `<名称>` | [照片01](<相对路径>) | `<最有辨识度的场景或物体>` | `<没有或照片>` |

点位顺序：

`1 <名称> → 2 <名称> → 3 <名称> → …… → <终点或返回1>`

### 图片预览

![打卡点照片联系表](<相对路径>)

## 八、打卡点确认

请检查：

1. 打卡点是否遗漏或多余；
2. 点位名称和顺序是否正确；
3. 每个点的标志性主图是否准确；
4. “必须保留的特征”是否与照片和现场认知一致。

如果信息没有问题，请回复：`打卡点和标志性图片确认无误`
```

Do not require scene attributes, function tags, supply fields, safety fields, full photo descriptions, or route-segment confirmation in the default stage. Record user-provided supply and safety facts directly for later prompt use.

## 阶段三：图片生成计划与画面规格

Only enter this stage after `打卡点和标志性图片确认无误` and after the final numbered route SVG has been generated. Append this stage to the existing review file; do not create a disconnected document.

```markdown
## 九、图片生成计划

| 图片编号 | 图片名称 | 图片类型 | 展示范围 | 画面比例 |
|---|---|---|---|---|
| 图01 | `<名称>` | `<路线总览图>` | `<完整路线>` | `<比例>` |

按用户需要增加路段详图、点位场景图或信息说明图。详图继续使用全局点位编号。

## 十、统一视觉与轨迹规则

| 项目 | 设置 |
|---|---|
| 画面风格 | `<风格>` |
| 主色调 | `<颜色>` |
| 路段颜色 | `<颜色规则>` |
| 中文文字方式 | `<模型生成/后期添加>` |
| 轨迹保真程度 | `<氛围自由/结构相似/精确轨迹>` |
| 是否显示方向箭头 | `<是/否>` |
| 是否允许旋转 | `<是/否>` |
| 是否允许镜像 | `<是/否>` |

根据内部轨迹结构自动填写：

- 起终点相对位置：`<位置>`
- 主要转折顺序：`<方向变化>`
- 闭环、折返或重合位置：`<说明>`
- 点位锚点与拥挤区域：`<说明>`

## 十一、点位视觉来源

| 编号 | 点位名称 | 视觉方式 | 主图 | 辅助图 | 使用说明 |
|---:|---|---|---|---|---|
| 1 | `<名称>` | `<真实照片/AI根据照片生成>` | `<照片>` | `<没有或照片>` | `<保留与避免内容>` |

## 十二、文案与信息

| 项目 | 内容 |
|---|---|
| 主标题 | `<标题>` |
| 副标题 | `<内容或不显示>` |
| 路线数据 | `<显示内容或不显示>` |
| 安全提示 | `<用户提供内容或不显示>` |
| 补给提示 | `<用户提供内容或不显示>` |
| 其他文案 | `<内容或不显示>` |

## 十三、生图所用基础信息摘要

在请求确认前，必须完整展示本轮提示词将使用的内容：

| 类别 | 已确认内容 |
|---|---|
| 路线事实 | `<名称、类型、起终点、方向、距离、爬升、下降、海拔、时长、强度>` |
| 多日分段 | `<每天起终点、跨夜点、每日统计；单日则写不适用>` |
| 全局打卡点 | `<编号、名称、顺序>` |
| 图片任务 | `<总览图、每日详图、点位场景图等>` |
| 视觉与比例 | `<风格、主色、画面比例、用途>` |
| 路线几何 | `<SVG 文件、标注点数量、方向、分段颜色>` |
| 地标与照片 | `<主图、AI 场景或原图框方式>` |
| 文案信息 | `<标题、数据卡、图例、警告>` |
| 补给与住宿 | `<已确认信息或无>` |
| 安全信息 | `<已确认风险或无>` |
| 负面约束 | `<不得镜像、重排、漏点、乱码等>` |

不得只回复“基础信息已确认”或引用旧核对单路径；必须在当前阶段把上述摘要实际展示给用户。

## 十四、生图规格确认

请检查图片数量、范围、风格、比例、轨迹结构、点位主图、基础信息摘要和附加文案。如果信息没有问题，请回复：`生图画面规格确认无误`

## 十五、执行方式

| 项目 | 设置 |
|---|---|
| 执行方式 | `<自动检测/只生成提示词/直接生成图片>` |
| 多图生成方式 | `<先生成小尺寸打卡点图供判断并跳过总览图/总览图确认后继续/一次生成全部>` |
| 是否需要图片编辑 | `<是/否>` |
| 是否需要真实照片合成 | `<是/否>` |

打卡点优先模式是可选的：当点位场景或主图存在不确定性时，最终授权后先生成小尺寸点位图供用户判断；用户确认后按已批准的图片任务生成详图。是否包含或跳过总览图必须在图片生成计划中明确，不得由 Agent 临时决定。

提示词生成完成后，再从以下方式中选择：

1. `直接生成完整效果图`：当前模型直接尝试完整构图，后续可能需要修正路线、编号或中文。
2. `生成视觉底图并后期叠加`：生成背景和地标视觉，再叠加确定性的 SVG、编号、中文和数据，推荐用于正式发布。
3. `只保留提示词`：不调用生图工具。

未选择前不得生图。
```

## 按需高级核对附录

Append these sections only when the user requests a detailed audit or when ambiguity prevents reliable checkpoint/image work. Do not insert them into the default workflow.

Read `advanced-review-template.md` for the complete optional templates. Append only the sections needed for the current ambiguity or user request.

### A. 路线结构与分段

Include route direction, loop/out-and-back/point-to-point topology, repeated sections, branches, segment boundaries, per-segment distance/elevation trend/road condition, and the reason for each boundary. Boundaries do not automatically become checkpoints.

### B. 完整照片顺序与内容

Sort all photos by matched progress. Group consecutive photos from the same place. Show visible content and recognized text only; keep timestamps, coordinates, and matching evidence internal unless needed to resolve ambiguity.

### C. 候选点与最终点位属性

When requested, include candidate evidence, track progress, elevation, scene attributes, and multi-select function tags such as viewpoint, supply, rest, navigation, parking, or risk. Do not infer supply, drinking water, access status, or safety facts from appearance alone.

### D. 不编号的路线过程

Record junctions, generic slopes, highest points, route boundaries, and environmental transitions that support route explanation but should not appear as numbered checkpoints.
