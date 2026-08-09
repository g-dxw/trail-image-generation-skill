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

## 阶段四：图片生成计划与画面规格

Only enter this stage after `打卡点和标志性图片确认无误` and after the final numbered route SVG has been generated. Append this stage to the existing review file; do not create a disconnected document.

This is a file-persistence gate, not a chat-only response. Before asking for confirmation:

1. Read the existing `<路线名称>-路线核对单.md` from disk.
2. Preserve all confirmed earlier sections and corrections.
3. Write sections 九 through 十四 into that same file with real values.
4. Do not leave angle-bracket placeholders, blank cells, `待补充`, or references such as “见前文”.
5. Re-read the saved file and run `python3 scripts/validate_stage4_review.py <核对单文件>`.
6. Show the clickable file path and the complete saved stage-4 content to the user.

If the review file is missing, reconstruct its confirmed earlier sections first. A Markdown block shown only in chat does not satisfy this stage.

This is workflow stage 4. Before continuing, require explicit values for exactly these four core decisions:

1. `画面风格`：写出可执行的风格描述，不能只写“好看”“高级”。
2. `生图数量`：默认 `1 张`；只有用户明确要求时才增加。
3. `图中文字`：按图片逐张列出需要出现的全部文字，并区分模型生成、后期添加或无文字。确认内容必须在第 7 阶段逐项原样进入对应图片的提示词，不得只保留在核对单中。
4. `轨迹精度`：默认 `精确轨迹/严格遵循轨迹`。只有用户明确要求时才可改为 `结构相似` 或 `氛围自由`；风格词和“直接生成完整效果图”都不构成降级授权。

任一项未填写或存在歧义时，停在本阶段继续核对。

```markdown
> 当前阶段：`image_plan_review / 图片生成计划核对中`

## 九、图片生成计划

### 第 4 阶段四个必确认项

| 必确认项 | 当前设置 | 状态 |
|---|---|---|
| 画面风格 | `<具体风格、媒介、色彩和氛围>` | `<待确认/已确认>` |
| 生图数量 | `1 张` | `<待确认/已确认>` |
| 图中文字 | `<逐条列出文字；或“无文字”；或“全部后期添加”>` | `<待确认/已确认>` |
| 轨迹精度 | `精确轨迹/严格遵循轨迹` | `<待确认/已确认>` |

确认短语：`风格、数量、图中文字和轨迹精度确认无误`

| 图片编号 | 图片名称 | 用途 | 图片类型 | 展示范围 | 画面比例 | 轨迹分段 | 包含点位 | 文字方式 |
|---|---|---|---|---|---|---|---|---|
| 图01 | `<名称>` | `<小红书封面/总览/详图等>` | `<路线总览图>` | `<完整路线>` | `<比例>` | `<0.0—1.0>` | `<全局编号及名称>` | `<模型生成/后期添加/无文字>` |

默认只规划图01，共 1 张。只有用户明确要求增加时，才加入路段详图、点位场景图或信息说明图。详图继续使用全局点位编号。

### 逐图完整画面规格

每张图片都必须建立独立小节，不得只用上方一行表格代替：

#### 图01 `<图片名称>`

| 项目 | 完整设置 |
|---|---|
| 用途与目标 | `<发布平台、阅读场景、用户一眼应理解什么>` |
| 画面比例与尺寸 | `<比例和建议像素>` |
| 构图层级 | `<前景、中景、背景和留白>` |
| 轨迹范围 | `<完整路线或精确进度范围>` |
| P0 几何 | `<路线类型、方向、起终点、分段、inset、点位锚点>` |
| P1 内容 | `<地标、文字、信息卡、背景和装饰>` |
| 包含点位 | `<全局编号、名称和视觉方式>` |
| 图片文字 | `<逐条完整列出，或明确无文字/全部后期添加>` |
| 参考图角色 | `<绝对路径和 route_geometry/real_photo/ai_scene/style_reference>` |
| 安全与补给 | `<本图显示内容或明确不显示>` |
| 负面约束 | `<禁止的路线、点位、文字和画面错误>` |
| 验收条件 | `<轨迹、点位、文字、地标、构图和清晰度>` |

## 十、统一视觉与轨迹规则

| 项目 | 设置 |
|---|---|
| 画面风格 | `<风格>` |
| 主色调 | `<颜色>` |
| 路段颜色 | `<颜色规则>` |
| 中文文字方式 | `<模型生成/后期添加>` |
| 轨迹保真程度 | `精确轨迹/严格遵循轨迹（默认；仅用户明确要求时降级）` |
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

在生成“生图所用基础信息摘要”之前，必须执行步骤 4.5 的联网调研。搜索当前路线名称与季节、天气、路况、开放状态、适合人群、装备、补给、交通和安全相关资料。优先官方或权威来源；体验性信息可以用可靠的本地户外资料补充，但要降低可信度标记。动态信息记录查询日期，图片文案不得把临时状态写成永久事实。

| 项目 | 内容 |
|---|---|
| 主标题 | `<标题>` |
| 副标题 | `<内容或不显示>` |
| 路线数据 | `<显示内容或不显示>` |
| 安全提示 | `<用户提供内容或不显示>` |
| 补给提示 | `<用户提供内容或不显示>` |
| 其他文案 | `<内容或不显示>` |

图中文字必须逐项核对。文字采用“模型直接生成”“模型预留区域后期添加”或“无文字”，必须由用户在第 4 阶段明确选择；Skill 不主动推荐或默认其中一种。不得让模型自行补充未经确认的标题、地名、距离、海拔或警告。

每张图片应使用独立文字清单，后续提示词必须包含完整的 `[TEXT_LOCK_BEGIN]` 区块。共享标题可在多张图中重复，但不能把仅属于某张图的文案自动复制到其他图片。

### 路线文案调研（步骤 4.5）

#### 信息来源

| 来源编号 | 来源标题 | 来源类型 | 链接 | 发布/更新日期 | 查询日期 | 支持的结论 | 可信度 |
|---|---|---|---|---|---|---|---|
| S1 | `<标题>` | `<官方/气象/交通/本地户外/其他>` | `<URL>` | `<日期或未标注>` | `<YYYY-MM-DD>` | `<该来源实际支持的结论>` | `<高/中/低>` |

不得把搜索结果摘要、论坛单条评论或没有正文支持的标题直接当作结论。涉及开放状态、施工、天气和交通时，优先使用当前有效的官方信息，并注明“出发前再次核实”。

#### 筛选后的路线信息

| 类别 | 拟采用内容 | 依据 | 是否放入图片 | 适用图片 |
|---|---|---|---|---|
| 适合时间/季节 | `<简洁结论>` | `<S1/用户确认/轨迹事实>` | `<是/否>` | `<图编号>` |
| 适合人群 | `<简洁结论>` | `<来源或用户确认>` | `<是/否>` | `<图编号>` |
| 不适合人群 | `<简洁结论>` | `<来源或用户确认>` | `<是/否>` | `<图编号>` |
| 装备建议 | `<简洁结论>` | `<来源或用户确认>` | `<是/否>` | `<图编号>` |
| 天气与路况风险 | `<简洁结论>` | `<来源或用户确认>` | `<是/否>` | `<图编号>` |
| 补给与饮水 | `<简洁结论或未找到可确认资料>` | `<来源或未找到可靠来源>` | `<是/否>` | `<图编号>` |
| 交通或停车 | `<简洁结论或未找到可确认资料>` | `<来源或未找到可靠来源>` | `<是/否>` | `<图编号>` |
| 通行限制/开放状态 | `<当前结论及查询日期，或未找到可确认资料>` | `<官方来源或未找到可靠来源>` | `<是/否>` | `<图编号>` |
| 环保与安全注意事项 | `<简洁结论>` | `<来源或通用安全原则>` | `<是/否>` | `<图编号>` |

#### 更新后的逐图文字

| 图片编号 | 最终拟采用文字 | 信息来源 | 排版优先级 |
|---|---|---|---|
| 图01 | `<标题、副标题、数据、季节、人群、注意事项等逐条列出>` | `<轨迹事实/用户确认/S1等>` | `<主标题/信息卡/角标>` |

核对单保留完整来源和依据；图片只使用经过筛选的短句，不默认显示网址、来源编号或大段说明。若某项对路线不适用或没有可靠资料，明确写出，不得用常识猜测补齐。

请核对调研结论和拟放入各图片的文字。如果没有问题，请回复：`路线文案与注意事项确认无误`

## 十三、生图所用基础信息摘要

只有收到 `风格、数量、图中文字和轨迹精度确认无误` 以及 `路线文案与注意事项确认无误` 后，才进入本摘要。在请求确认前，必须完整展示本轮提示词将使用的内容：

| 类别 | 已确认内容 |
|---|---|
| 路线事实 | `<名称、类型、起终点、方向、距离、爬升、下降、海拔、时长、强度>` |
| 多日分段 | `<每天起终点、跨夜点、每日统计；单日则写不适用>` |
| 全局打卡点 | `<编号、名称、顺序>` |
| 图片任务 | `<总览图、每日详图、点位场景图等>` |
| 视觉与比例 | `<风格、主色、画面比例、用途>` |
| 路线几何 | `<SVG 文件、PNG 预览、布局 JSON、标注点数量、方向、分段颜色>` |
| 轨迹精度与优先级 | `<精确轨迹/结构相似/氛围自由；P0 几何和 P1 视觉内容>` |
| 参考图角色 | `<逐项列出 route_geometry/real_photo/ai_scene/style_reference>` |
| 地标与照片 | `<主图、AI 场景或原图框方式>` |
| 文案信息 | `<标题、数据卡、图例、警告>` |
| 补给与住宿 | `<已确认信息或无>` |
| 安全信息 | `<已确认风险或无>` |
| 负面约束 | `<不得镜像、重排、漏点、乱码等>` |

不得只回复“基础信息已确认”或引用旧核对单路径；必须在当前阶段把上述摘要实际展示给用户。

## 十四、生图规格确认

保存后校验命令：`python3 scripts/validate_stage4_review.py <路线名称>-路线核对单.md`

只有校验通过后，才提供核对单文件路径并请用户检查图片数量、逐图完整规格、范围、风格、比例、轨迹结构、点位主图、基础信息摘要和附加文案。如果信息没有问题，请回复：`生图画面规格确认无误`

## 十五、执行方式

进入执行方式前，必须先逐张完整展示最终生图提示词。不得只展示摘要、提示词片段或共享计划。请用户逐张核对轨迹约束、图片文字、地标、文案、构图、参考图角色、负面约束和验收条件。

提示词确认短语：`生图提示词确认无误`

任何提示词发生修改后，原确认失效，必须重新展示完整正文并再次确认。

| 项目 | 设置 |
|---|---|
| 执行方式 | `<自动检测/只生成提示词/直接生成图片>` |
| 多图生成方式 | `<先生成小尺寸打卡点图供判断并跳过总览图/总览图确认后继续/一次生成全部>` |
| 是否需要图片编辑 | `<是/否>` |
| 是否需要真实照片合成 | `<是/否>` |

打卡点优先模式是可选的：当点位场景或主图存在不确定性时，最终授权后先生成小尺寸点位图供用户判断；用户确认后按已批准的图片任务生成详图。是否包含或跳过总览图必须在图片生成计划中明确，不得由 Agent 临时决定。

提示词生成完成后，先选择图像提供方：

1. `使用当前会话生图`：默认请求 `gpt-image-2`。
2. `使用已配置中转站`：调用前显示地址、模型、格式和上传清单，并再次确认。
3. `只保留提示词`：不调用生图工具。

选择提供方后，使用 `直接生成完整效果图`。该方式继承已确认的轨迹精度，不会自动降级。本 Skill 不用 SVG 后期确定性叠加修正轨迹；正式调用前必须生成并校验执行清单，确保轨迹 PNG 实际作为 `route_geometry` 参考图传入。

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
