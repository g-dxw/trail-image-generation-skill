# 生图提示词规则

Only read and apply this file together with `geometry-contract.md` after the user has replied `生图画面规格确认无误`. Generate prompts first. After delivering the prompts, re-discover the tools actually available in the current runtime and ask the user to choose the current-session image tool, a configured relay, or prompt-only mode. Authorized generation produces the complete image directly; this skill does not use deterministic SVG post-overlay as a route-correction step. Never claim a model name, price class, quality level, output size, or reference-image capacity that the runtime tool schema or reviewed provider configuration does not expose. Do not call or upload to an external provider before explicit confirmation.

Every final route-image prompt must be shown to the user in full and approved with `生图提示词确认无误` before final provider selection or route-image generation authorization. The separately authorized landmark-simplification stage may call an image tool earlier, but it must use its own locked prompt, one confirmed source photo, provider/upload confirmation, and landmark manifest. If the user requests any final-prompt revision, regenerate and show the complete revised prompt again.

Do not compile prompts unless the stage-4 decisions `画面风格`, `生图数量`, `图中文字`, and `轨迹精度` have been confirmed. Default image count is one. Default route fidelity is `精确轨迹/严格遵循轨迹`. Create exactly the confirmed number of independent prompts.

## 执行能力与点位优先

- 先检测当前 Agent 是否具备可调用的生图模型/工具，不根据 Agent 名称猜测能力。
- 没有生图能力，或用户明确要使用其他生图模型时，只输出独立可用的提示词、参考图清单、构图要求和负面约束，不声称已生成图片。
- 点位优先模式仅在用户于图片计划中明确选择时使用：先生成小尺寸打卡点图供判断；是否跳过总览图必须由已确认计划决定，不得由 Agent 临时推断。

## 强制几何层

- 每条路线图提示词都必须列出路线 SVG、PNG 预览和布局 JSON，但只有 PNG 作为 `route_geometry` 上传；SVG 和布局 JSON 必须明确标为“不上传的校验资产”。
- PNG 是提交给生图模型的最高优先级几何参考；SVG 和布局 JSON 用于生成前后校验点位锚点与路线拓扑。不得把 SVG 后期叠加当作默认补救手段。
- 标注点必须沿 SVG 原位置、原顺序、原编号显示，禁止遗漏、重排、镜像、旋转或移到路线外。
- 若 SVG 标注点未生成，流程阻断，先补齐参考资产。
- 默认不要求或自动生成示意等高线。只有用户提供可靠地形数据并明确要求时，才把地形图层加入提示词。

## 1. Build prompts from the current route

Never reuse screen directions, point counts, segment counts, aspect ratios, or styles from a previous route. Derive them from the approved review document and current image task.

For every image, specify:

- image type and intended use;
- image scope: full route, one segment, one checkpoint, or information card;
- target aspect ratio and shared visual style;
- route type, start and finish relationship, major-anchor sequence, and travel direction;
- included global checkpoint numbers and names;
- real-photo frames versus AI-derived landmark scenes;
- exact text, data, safety, supply, and seasonal information requested for this image;
- negative constraints and an acceptance checklist.
- mandatory geometry assets: the route SVG, PNG preview, layout JSON, and annotation points.

Each prompt must be standalone and directly executable. It must repeat all settings required for that image, even when multiple images share them. Never use `同上`, `沿用共享设置`, `参考前文`, `按核对单执行`, ellipses, placeholders, or a shared-plan reference as a substitute for actual prompt content.

Every route-map prompt must contain this non-rewritable block, filled with current-route facts:

```text
[GEOMETRY_LOCK_BEGIN]
优先级：P0，覆盖构图、美术、文字和装饰要求。
轨迹参考PNG：<absolute path; attach as route_geometry reference>
路线SVG：<absolute path; validation asset>
布局JSON：<absolute path; validation asset>
轨迹精度：精确轨迹/严格遵循轨迹
路线类型：<open/closed/out-and-back>
方向：<confirmed travel direction>
起终点：<confirmed relationship>
锚点：<global checkpoint number, name, progress, anchor interval>
点位完整性：<逐项列出本图应显示的全部编号；数量必须与已确认列表一致，不得遗漏、重复、增补或跳号；地标卡片存在不能替代轨迹锚点>
点位对应：<每个轨迹锚点编号、点位名称和地标参考板主体必须一一对应；地标卡片存在不能替代轨迹锚点>
地标连接方式：<默认无引导连线，通过相同编号、名称和邻近布局对应；只有用户明确要求时才允许连线>
分段/inset：<confirmed segment and inset rules>
禁止重画、简化、镜像、旋转、闭合、移动锚点、改变编号或改变分段边界。
冲突时移动或缩小文字、地标、信息卡和装饰，始终保持轨迹完整可读。
[GEOMETRY_LOCK_END]
```

Keep the block verbatim from the approved prompt file at execution time. Do not summarize, translate, shorten, or recreate it from memory.

Every image prompt must also contain the stage-4 text decision as a non-rewritable block:

```text
[TEXT_LOCK_BEGIN]
文字方式：<模型直接生成/模型预留区域后期添加/无文字>
必须出现：<按该图片逐条列出已确认标题、副标题、地名、数据、提示和图例；没有则写“无”>
禁止出现：<未经确认的标题、地名、距离、海拔、警告或模型自行补充的文字>
排版避让：文字和信息卡属于 P1，必须避让 P0 轨迹、编号锚点、方向和分段。
[TEXT_LOCK_END]
```

Copy confirmed wording exactly. Do not paraphrase, shorten, merge, translate, or reuse text assigned to another image. If the decision is `全部后期添加`, the text lock must still list every confirmed string verbatim and reserve a distinct adequate region for each title, endpoint, data item, checkpoint label, and notice; never replace the list with a category summary. Instruct the model not to render those strings or placeholder characters. If it is `无文字`, explicitly prohibit all decorative lettering and fake map labels.

The text lock must incorporate the image-specific wording selected during step 4.5 route-copy research. Include confirmed short text for applicable items such as suitable season/time, suitable or unsuitable participants, equipment, weather/road risks, supply, access restrictions, and safety reminders. Do not automatically place source URLs, source IDs, confidence labels, or long research explanations in the image; keep those in the review document unless the user explicitly requests citations on the artwork. Never add a researched item to an image that the stage-4.5 table marked `否`.

When route intensity is shown, use the confirmed `route_intensity.score` and `route_intensity.level`. Do not convert cave, wet surface, cliff exposure, construction status, or ladder use into the route-intensity value; keep them as separate safety text.

## 2. Route fidelity modes

- **精确轨迹/严格遵循轨迹（默认）**: treat the approved route PNG as the highest-priority geometry reference. Preserve the complete visible polyline, topology, direction, start/finish relationship, segment boundaries, inset position, and checkpoint anchors. Artistic treatment may change line color, width, texture, and surrounding layout, but not geometry.
- **结构相似（仅用户明确要求时）**: preserve overall silhouette, major turns, start/finish relationship, travel direction, and checkpoint order; allow local simplification.
- **氛围自由（仅用户明确要求时）**: preserve only route type and broad direction.

Never infer a downgrade from phrases such as `手绘旅行地图`, `更有设计感`, or `直接生成完整效果图`. If the user did not explicitly approve a lower mode, keep exact fidelity.

Fit the route into the requested canvas without non-uniform stretching. Add padding when source and target aspect ratios differ. Do not mirror or rotate unless approved.

### Clean route-map composition default

Use a clean no-connector composition unless the user explicitly approves connector lines. Place landmark cards near the matching route region and repeat the same checkpoint number and name on the route anchor and landmark card. This reduces visual clutter and avoids connector-driven anchor duplication or mismatch.

Treat any confirmed location background as P1 atmosphere. Describe the confirmed viewpoint and broad landscape only, render it with low contrast and atmospheric perspective, and keep the route, endpoints, checkpoint anchors, text, and landmark identities dominant. Do not invent precise buildings, labels, construction state, lighting events, or city conditions that the user did not confirm.

## 3. Describe route structure generically

Convert track geometry into a small ordered set of major screen-space anchors. Describe the current route using those anchors, for example:

```text
start at <relative position>;
continue toward <direction> through anchor A;
turn toward <direction> through anchor B;
reach the finish at <relative position>;
```

For loops, state how the final section reconnects to the start. For out-and-back routes, identify the overlapping return. For point-to-point routes, keep start and finish distinct.

Bind each checkpoint to both track progress and the anchor interval containing it. Never rely only on a textual `1→2→...→N` list.

## 4. Preserve numbering across multiple images

Use one global checkpoint list. Overview and detail images must keep the same numbers. A detail image containing checkpoints 4, 5, and 6 must display 4, 5, and 6.

For every image, count the checkpoints that should appear and require the rendered anchor count to match. A landmark card or label does not count as a checkpoint unless its route anchor is also present. Bind each route anchor, number, name, and landmark identity one-to-one. Do not draw connector lines by default; use matching numbers, names, and nearby card placement. Connector lines are allowed only after explicit user approval.

If a detail image includes a route inset:

- show the full route in a muted color;
- highlight the current segment;
- indicate its position in the full journey.

## 5. Handle reference materials by role

Final route-image generation accepts at most two uploaded images:

- `route_geometry`: the route PNG, always first;
- `landmark_reference_board`: one optional deterministic board built from approved simplified landmarks, always second.

Original photos, individual simplified landmarks, SVG, and layout JSON are never final route-image uploads. Keep them under `素材事实来源（不上传）` or `校验资产（不上传）`.

For route screenshots, use only the polyline silhouette, major turns, travel direction, and layout. Ignore satellite backgrounds, map labels, pins, phone UI, and controls.

For a generated route skeleton, attach only its rasterized PNG preview as the geometry reference. Keep the SVG and compact normalized path signature for validation and textual structure guidance. Do not paste hundreds of original track points into the prompt.

### Real photo mode

When the user wants the existing photo itself:

- reserve a frame in the generated base image;
- keep the original photo out of the generative redraw path;
- create a deterministic composition instruction with crop focus, frame shape, size, position, and privacy treatment;
- do not claim the model will preserve original photo pixels merely because it received a reference image.

### AI-derived scene mode

Extract only confirmed features:

- primary scene;
- distinctive objects;
- environment and colors;
- foreground, middle-ground, and background relationships;
- must-preserve features;
- allowed simplifications;
- avoid items.

Do not reproduce identifiable people unless the user explicitly requests and authorizes it.

### Landmark simplification mode

Before building a landmark reference board, create one locked prompt per landmark with:

```text
[LANDMARK_SIMPLIFICATION_LOCK_BEGIN]
点位编号：<全局编号；不得由模型写入图片>
点位名称：<已确认名称>
画面风格骨架：<提前确认的轮廓、主色、材质方向和笔触方向；终稿模型负责统一完成度>
必须保留：<1—3 个已确认辨识特征>
原图文字处理：<真实存在且已确认的牌匾、石刻和地标名称允许参考保留；看不清时保留文字区域或题刻特征，不强行补写；不得新增原图不存在的文字>
必须删除：人物、广告、杂乱背景、无关建筑、点位编号、凭空新增的招牌或随机文字
输出：请求provider已确认的较小方形尺寸和low/fast/draft档；工具不暴露尺寸或质量控制时使用默认输出并记录实际尺寸；主体居中、浅色纯净背景、小型精简地标插画；需要时另行确定性生成512×512拼板标准稿，标准稿不得冒充模型原始输出
事实边界：原始照片和核对单定义事实；不得发明照片中不存在的主体结构
[LANDMARK_SIMPLIFICATION_LOCK_END]
```

Upload exactly one confirmed original photo for each call. Do not automatically accept or retry the output. Preserve individual outputs, build numbered review boards deterministically, and wait for `地标简化稿确认无误` before any simplified landmark can enter a final reference board.

The prepaint output locks landmark identity, silhouette, primary colors, orientation, confirmed original inscriptions, and 1–3 confirmed features. Existing plaques, stone inscriptions, and landmark names may remain when supported by the source photo; do not invent missing text. The final route-image executor may improve lighting, materials, brushwork, and scene integration, but may not replace or mutate those confirmed identity features. Never build an original-photo collage and ask a model to simplify the collage.

## 6. Keep prompt priorities clear

Use this priority order unless the user changes it:

1. P0: route PNG geometry, topology, direction, start/finish, segment boundaries, inset, complete checkpoint anchors, numbering, and one-to-one checkpoint identity;
2. P1: checkpoint names and function icons;
3. P1: landmark scenes or real-photo frames;
4. P1: typography, information cards, low-contrast confirmed location background, decoration, and atmosphere.

When content conflicts with route readability, shrink or move secondary illustrations instead of changing route structure. Do not introduce connector lines as a layout remedy unless the user explicitly approved them.

## 7. Recommended prompt structure

```text
use case and asset type |
image scope and layout |
shared style |
actual uploaded references |
landmark-board number mapping |
non-uploaded fact sources |
non-uploaded validation assets |
single-image compatibility branch |
route fidelity and geometry |
segment display |
global checkpoints and topology |
checkpoint scenes and real-photo frames |
text and route data |
safety, supply, and seasonal information |
background and decoration |
visual constraints |
negative constraints
```

The delivered prompt must include every item above that applies to the image, plus the complete geometry lock, complete text lock, actual upload paths, board mapping, non-uploaded sources/assets, and an explicit acceptance checklist. Shared execution plans may help internal consistency but never replace content inside an individual final prompt.

For reliable preflight validation, every route-map prompt must include these explicit labels with complete content:

```text
实际上传参考图：<第1张 route_geometry 轨迹PNG；第2张可选 landmark_reference_board>
地标参考板编号映射：<参考板编号 → 全局点位编号、名称、必须保留特征；没有则写“无”>
素材事实来源（不上传）：<原始照片、用户确认特征和单张简化稿路径；没有则写“无”>
校验资产（不上传）：<路线SVG、布局JSON和参考板sidecar>
单图兼容分支：<provider仅支持1张图时只上传轨迹PNG，地标改用哪些已确认文字特征>
负面约束：<列出本图禁止出现的错误>
验收清单：<逐项列出轨迹、点位、文字、地标、构图和清晰度验收条件>
```

## 8. Negative constraints

Include only relevant constraints, such as:

`wrong route type, route shape unrelated to reference, mirrored route, unauthorized rotation, non-uniformly stretched route, missing checkpoint, duplicated checkpoint, extra checkpoint, skipped number, wrong checkpoint order, reversed checkpoint numbering, checkpoint renumbered in detail map, checkpoint anchor replaced by a landmark card, number/name/landmark mismatch, unapproved connector line, wrong or misleading connector line, checkpoints rearranged for visual balance, disconnected markers, marker on wrong segment, route hidden behind illustrations, oversized landmark cards, unapproved full-photo scene inserted instead of the confirmed simplified landmark, satellite map UI, photo pins, phone controls, garbled Chinese characters, cropped route`

## 9. Multi-image execution

Create one prompt per image task plus a shared execution plan. Keep shared style, global numbers, segment colors, names, and landmark invariants consistent.

For overview-first cadence, generate and review the overview before compiling targeted revisions for detail images. For generate-all cadence, execute each image as a separate task; do not use multiple variants of one prompt as a substitute for distinct image prompts.

## 10. Capability and authorization

- If the user selected prompt-only mode, stop after delivering prompts.
- If generation is authorized, check whether an image-generation tool is actually available in the current session.
- If available, generate or edit using the current tool's supported path.
- If unavailable, provide prompts and composition instructions; never claim that an image was generated.
- Never silently switch to an external credentialed API or CLI fallback.

## 11. Preflight and post-generation acceptance

- Before every generation call, build a generation manifest with `build_generation_manifest.py` and validate it with `validate_generation_manifest.py`.
- Do not build the final manifest or call an image tool until the user has approved the exact complete prompt with `生图提示词确认无误`.
- The exact prompt file used to build the manifest is the prompt sent to the image tool. Do not manually rewrite it in the tool call.
- The prompt must contain the complete `[TEXT_LOCK_BEGIN]` block for that image, including an explicit no-text or post-production decision when applicable.
- The route PNG must be the first actual upload and labeled `route_geometry`. The only allowed second upload is one `landmark_reference_board`; never upload SVG, layout JSON, original photos, or individual simplified landmarks in the final route-image call.
- A successful model response is not acceptance. Compare the output against the approved geometry assets.
- Reject outputs with a materially different silhouette, wrong direction, moved start/finish, changed segment boundary, missing/duplicated/extra/reordered checkpoint, checkpoint count mismatch, number/name/landmark mismatch, an unapproved connector line, or route hidden by P1 content.
- Do not call a rejected output final. One targeted retry is allowed, retaining the same geometry lock and changing only the conflicting P1 composition instructions.
- Prompt-only strictness reduces drift but does not guarantee pixel-level identity. State this limitation when exactness matters.
# 多日徒步补充规则

多日路线的每条独立提示词必须包含：`第几天`、`当天起点`、`当天终点/跨夜点`、`当天突出颜色`、`全局点位范围` 和 `其余路线的 inset 表现`。跨夜点必须在相邻两天重复出现，但编号和名称保持不变。
