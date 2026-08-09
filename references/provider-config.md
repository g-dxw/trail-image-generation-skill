# 图像提供方配置

Use provider configuration only after prompts are complete and the user chooses `使用已配置中转站`. Never silently fall back to a relay.

## Local configuration

Copy `assets/provider-config.example.json` to a private local path such as:

```text
~/.config/trail-image-generation/providers.json
```

The default requested model is `gpt-image-2`. A provider may override it when its relay uses another executable model identifier.

Store only the environment-variable name in JSON. Never store the secret value.

## Required confirmation

Before any external request, show:

```text
图像提供方：<name>
目标地址：<origin and base path>
模型：<model>
接口格式：<api_format>
上传内容：<prompt / route PNG / confirmed photos>
返回格式：<url / base64 / binary>
```

Wait for explicit confirmation. Do not print the token, silently switch providers, or upload unconfirmed photos.

## Supported configuration fields

- `base_url`
- `api_format`: `openai-responses`, `openai-images`, or `custom`
- `model`
- `api_key_env`
- `supports_reference_images`
- `supports_image_editing`
- `supports_streaming`
- `result_format`: `url`, `base64`, or `binary`
- `timeout_seconds`
- `max_retries`

Custom formats require a separately reviewed adapter. Configuration alone does not authorize inventing a request schema.
