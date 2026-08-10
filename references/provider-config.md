# 图像执行器能力发现与配置

每台电脑和每个 Agent 会话可用的生图工具可能不同。先检查本轮实际附带的工具 schema，再读取本地 provider 配置。能力发现只读执行，不得为了探测能力自动发起收费请求或上传照片。

## 两个独立角色

- `landmark_prepaint`：逐张上传一张已确认原图，优先请求 Provider 已确认的较小方形尺寸和 low/fast/draft 档。原始输出尺寸如实记录；需要时另行生成默认512×512的拼板标准稿。要求至少一张参考图并确认支持图片编辑/参考图重绘。
- `route_final`：生成正式路线图。精确轨迹至少需要一张 `route_geometry`；两图模式需要再接收一张 `landmark_reference_board`。

两个角色分别选择、分别确认。选型小样、批量地标预绘和最终路线图是三个独立上传授权范围。

## 当前会话能力发现

检查当前 Agent 实际暴露的图像生成/编辑工具及参数：是否支持参考图、图片编辑、模型选择、尺寸、质量和参考图数量。无法从工具 schema 确认的字段写 `unknown`。模型被平台隐藏时写 `tool-managed/unknown`。

使用脚本保存能力证据，例如；`--executor` 必须与 manifest 中的 provider profile 名一致：

```bash
python3 scripts/build_image_capability_report.py \
  --executor builtin \
  --executor-type current_session \
  --model tool-managed/unknown \
  --source runtime_tool_schema \
  --can-generate true \
  --can-use-reference-image true \
  --can-edit-image true \
  --selectable-model false \
  --selectable-size false \
  --selectable-quality false \
  --evidence "attached tool accepts an image edit reference but exposes no model/size/quality selector" \
  --output route-work/current-session-image-capabilities.json
```

能力值只使用 `true`、`false` 或 `unknown`。能够执行不代表便宜或高质量；价格和质量没有证据时保持 `unknown`。

## 本地 Provider 配置

复制 `assets/provider-config.example.json` 到私有路径，例如：

```text
~/.config/trail-image-generation/providers.json
```

配置 schema v2 使用：

- `defaults.landmark_prepaint_provider`
- `defaults.route_final_provider`
- `allowed_purposes`：`landmark_prepaint`、`route_final`
- `model`：工具隐藏模型时使用 `tool-managed/unknown`
- `supports_reference_images`：`true`、`false` 或 `unknown`
- `max_reference_images`：`0..16` 或 `unknown`
- `supports_image_editing`：`true`、`false` 或 `unknown`
- `supported_output_sizes`
- `supported_quality_levels`
- `preferred_output_size`
- `preferred_quality`
- `cost_class`：`budget`、`standard`、`premium`、`unknown`
- `quality_class`：`draft`、`final`、`user_approved_for_drafts`、`user_approved_for_final`、`unknown`
- `capability_source`：`runtime_tool_schema`、`provider_config`、`provider_documentation`、`user_approved_sample`、`unknown`
- `base_url`
- `api_format`：`openai-responses`、`openai-images` 或 `custom`
- `api_key_env`
- `supports_streaming`
- `result_format`：`url`、`base64` 或 `binary`
- `timeout_seconds`
- `max_retries`

旧配置只有 `default_provider` 时仍可读取；没有 `allowed_purposes` 时暂按两个角色均可选择，没有 `max_reference_images` 时 `supports_reference_images: true/false` 分别按 1/0。但旧配置缺少价格、质量和尺寸证据时，这些字段仍为 `unknown`。

验证和按用途选择：

```bash
python3 scripts/provider_config.py validate ~/.config/trail-image-generation/providers.json
python3 scripts/provider_config.py select ~/.config/trail-image-generation/providers.json --purpose landmark_prepaint --provider builtin --capability-report route-work/builtin-prepaint-capabilities.json
python3 scripts/provider_config.py select ~/.config/trail-image-generation/providers.json --purpose route_final
```

当前会话 Provider 默认能力为未知，选择时必须附带本轮能力报告。由官方文档配置且字段完整的 relay 可以直接选择；最终 manifest 仍必须附带对应能力报告并做语义一致性校验。

## 地标预绘尺寸规则

1. Provider 明确列出尺寸和质量：选择已确认的较小方形尺寸和 low/fast/draft 档，不把模型名当作价格证据。
2. Provider 不暴露尺寸或质量参数：使用 `provider-default`，并在返回后记录真实格式和像素尺寸。
3. 原始稿不是适合拼板的较小方图：运行 `python3 scripts/normalize_landmark_draft.py input.png --output normalized.png --size 512` 生成独立标准稿。
4. 标准稿只用于审核板和最终参考板，不得覆盖或冒充模型原始输出。
5. 不得把多张原始照片先拼板再交给模型重绘。

便宜执行器只负责地标身份、轮廓、主色、方向和 1—3 个辨识特征；最终执行器负责统一光影、材质、笔触和场景融合，但不得改变地标事实。

## 能力不明确时的选型小样

当存在多个候选工具但价格或效果未知时，可在 `地标简化规格确认无误` 后：

1. 选择一张已确认的代表照片。
2. 展示每个候选执行器、模型或未知状态、目标地址、提示词和上传路径。
3. 获得仅限这张照片和这些候选执行器的授权。
4. 每个候选只生成一张小样，不自动重试。
5. 用户按结果指定 `landmark_prepaint` 执行器。

小样结果只能支持 `user_approved_for_drafts`，不能证明价格便宜，也不能自动成为批量授权或最终路线图授权。

## 外部调用前确认

每次授权范围都要展示：

```text
执行角色：<landmark_prepaint / route_final>
图像提供方：<name>
目标地址：<origin and base path / current-session-tool>
模型：<model / tool-managed/unknown>
接口格式：<api_format>
尺寸与质量：<明确值 / unknown>
价格与质量等级：<明确值 / unknown>
上传内容：<一张已确认原图；或最终 prompt / route PNG / optional landmark board>
返回格式：<url / base64 / binary / tool-result>
```

不得打印 Token、静默切换 Provider、把未知能力写成已支持，或把一次授权扩展到其他照片和阶段。Custom 格式必须使用已审查的 adapter，不能只凭配置猜请求格式。
