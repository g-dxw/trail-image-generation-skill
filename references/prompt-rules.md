# 生图提示词规则

Only read and apply this file together with `geometry-contract.md` after the user has replied `生图画面规格确认无误`. Generate prompts first. After delivering the prompts, ask the user to choose the current-session image tool, a configured relay, or prompt-only mode. Authorized generation produces the complete image directly; this skill does not use deterministic SVG post-overlay as a route-correction step. The default requested model is `gpt-image-2`. Do not call or upload to an external provider before explicit confirmation.

Every final prompt must be shown to the user in full and approved with `生图提示词确认无误` before provider selection or generation authorization. If the user requests any revision, regenerate and show the complete revised prompt again. A previous approval does not apply to modified prompt text.

Do not compile prompts unless the stage-4 decisions `画面风格`, `生图数量`, `图中文字`, and `轨迹精度` have been confirmed. Default image count is one. Default route fidelity is `精确轨迹/严格遵循轨迹`. Create exactly the confirmed number of independent prompts.

## 执行能力与点位优先

- 先检测当前 Agent 是否具备可调用的生图模型/工具，不根据 Agent 名称猜测能力。
- 没有生图能力，或用户明确要使用其他生图模型时，只输出独立可用的提示词、参考图清单、构图要求和负面约束，不声称已生成图片。
- 点位优先模式：先生成小尺寸打卡点图供用户判断；用户确认后跳过总览图，直接生成路线详图。

## 强制几何层

- 每条路线图提示词都必须列出路线 SVG、PNG 预览和布局 JSON。向生图模型提交视觉参考时优先使用 PNG，不假设模型能解析 SVG。
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

Copy confirmed wording exactly. Do not paraphrase, shorten, merge, translate, or reuse text assigned to another image. If the decision is `全部后期添加`, instruct the model to reserve the confirmed regions without rendering placeholder characters. If it is `无文字`, explicitly prohibit all decorative lettering and fake map labels.

The text lock must incorporate the image-specific wording selected during step 4.5 route-copy research. Include confirmed short text for applicable items such as suitable season/time, suitable or unsuitable participants, equipment, weather/road risks, supply, access restrictions, and safety reminders. Do not automatically place source URLs, source IDs, confidence labels, or long research explanations in the image; keep those in the review document unless the user explicitly requests citations on the artwork. Never add a researched item to an image that the stage-4.5 table marked `否`.

When route intensity is shown, use the confirmed `route_intensity.score` and `route_intensity.level`. Do not convert cave, wet surface, cliff exposure, construction status, or ladder use into the route-intensity value; keep them as separate safety text.

## 2. Route fidelity modes

- **精确轨迹/严格遵循轨迹（默认）**: treat the approved route PNG as the highest-priority geometry reference. Preserve the complete visible polyline, topology, direction, start/finish relationship, segment boundaries, inset position, and checkpoint anchors. Artistic treatment may change line color, width, texture, and surrounding layout, but not geometry.
- **结构相似（仅用户明确要求时）**: preserve overall silhouette, major turns, start/finish relationship, travel direction, and checkpoint order; allow local simplification.
- **氛围自由（仅用户明确要求时）**: preserve only route type and broad direction.

Never infer a downgrade from phrases such as `手绘旅行地图`, `更有设计感`, or `直接生成完整效果图`. If the user did not explicitly approve a lower mode, keep exact fidelity.

Fit the route into the requested canvas without non-uniform stretching. Add padding when source and target aspect ratios differ. Do not mirror or rotate unless approved.

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

If a detail image includes a route inset:

- show the full route in a muted color;
- highlight the current segment;
- indicate its position in the full journey.

## 5. Handle reference materials by role

Label every input image as one of:

- route geometry reference;
- real photo to insert;
- AI scene reference;
- style reference.

For route screenshots, use only the polyline silhouette, major turns, travel direction, and layout. Ignore satellite backgrounds, map labels, pins, phone UI, and controls.

For a generated route skeleton, prefer attaching the SVG or a rasterized preview as the geometry reference. Also include the compact normalized path signature from the generated prompt fragment. Do not paste hundreds of original track points into the prompt.

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

## 6. Keep prompt priorities clear

Use this priority order unless the user changes it:

1. P0: route PNG geometry, topology, direction, start/finish, segment boundaries, inset, checkpoint anchors and numbering;
2. P1: checkpoint names and function icons;
3. P1: landmark scenes or real-photo frames;
4. P1: typography, information cards, decoration, background, and atmosphere.

When content conflicts with route readability, shrink or move secondary illustrations instead of changing route structure.

## 7. Recommended prompt structure

```text
use case and asset type |
image scope and layout |
shared style |
reference-image roles |
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

The delivered prompt must include every item above that applies to the image, plus the complete geometry lock, complete text lock, reference-image paths and roles, and an explicit acceptance checklist. Shared execution plans may help internal consistency but never replace content inside an individual final prompt.

For reliable preflight validation, every route-map prompt must include these explicit labels with complete content:

```text
参考图角色：<逐项列出绝对路径和 route_geometry/real_photo/ai_scene/style_reference>
负面约束：<列出本图禁止出现的错误>
验收清单：<逐项列出轨迹、点位、文字、地标、构图和清晰度验收条件>
```

## 8. Negative constraints

Include only relevant constraints, such as:

`wrong route type, route shape unrelated to reference, mirrored route, unauthorized rotation, non-uniformly stretched route, wrong checkpoint order, reversed checkpoint numbering, checkpoint renumbered in detail map, checkpoints rearranged for visual balance, disconnected markers, marker on wrong segment, route hidden behind illustrations, oversized landmark cards, real photo redrawn by AI, satellite map UI, photo pins, phone controls, garbled Chinese characters, cropped route`

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
- The route PNG must be present in the actual image references and labeled `route_geometry`.
- A successful model response is not acceptance. Compare the output against the approved geometry assets.
- Reject outputs with a materially different silhouette, wrong direction, moved start/finish, changed segment boundary, missing/reordered checkpoint, or route hidden by P1 content.
- Do not call a rejected output final. One targeted retry is allowed, retaining the same geometry lock and changing only the conflicting P1 composition instructions.
- Prompt-only strictness reduces drift but does not guarantee pixel-level identity. State this limitation when exactness matters.
# 多日徒步补充规则

多日路线的每条独立提示词必须包含：`第几天`、`当天起点`、`当天终点/跨夜点`、`当天突出颜色`、`全局点位范围` 和 `其余路线的 inset 表现`。跨夜点必须在相邻两天重复出现，但编号和名称保持不变。
