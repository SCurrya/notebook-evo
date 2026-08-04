# 项目整改记录（中文）

## 本轮目标

1. 修复 OpenRouter 模型分类，把 `whisper / transcribe / asr` 归到 STT。
2. 让现有错分的 OpenRouter 模型在重同步时自动回正。
3. 统一 provider 能力声明，让前端能看到 openrouter 的语音能力。
4. 跑后端定向测试、前端 build，并重新打包 EXE。
5. 记录当前真实状态，避免把“能发现”和“已分配”混为一谈。

## 已完成

### 1) OpenRouter 分类修复

- 已修复 `open_notebook/ai/model_discovery.py` 中 OpenRouter 的类型识别顺序。
- 现在会优先把下列关键词识别为 `speech_to_text`：
  - `whisper`
  - `transcribe`
  - `transcription`
  - `asr`
- 只有真正的 TTS 模型才会进入 `text_to_speech`。

### 2) 旧数据自动纠正

- `sync_provider_models()` 现在会按模型名查找历史记录。
- 如果同名模型的类型变了，会原地更新旧记录，而不是再插一条新记录。
- 这样可以把之前错分到 TTS 的 OpenRouter STT 模型，在重同步时直接回正。

### 3) Provider 能力声明

- `api/credentials_service.py` 已把 `openrouter` 的默认能力扩展为：
  - `language`
  - `embedding`
  - `speech_to_text`
  - `text_to_speech`
- 前端 `api-keys` 页面也已同步这个能力集合，避免 UI 仍显示成“只有语言和 embedding”。

### 4) 后端测试

- 已用仓库自带 Python 环境跑通定向测试：
  - `tests/test_credentials_api.py`
  - `tests/test_models_api.py`
- 结果：`27 passed`

### 5) 前端构建

- `frontend` 已成功完成生产构建。
- 路由和静态页生成正常。

## 当前真实状态

### 已确认

- 本地 API 服务器在线。
- `GET /api/config` 返回正常。
- `GET /api/models/defaults` 当前状态是：
  - `default_chat_model` 已有
  - `default_transformation_model` 已有
  - `large_context_model` 已有
  - `default_embedding_model` 已有
  - `default_text_to_speech_model` 已有
  - `default_speech_to_text_model` 仍为空

### OpenRouter 现状

- 通过当前运行中的旧进程查看，OpenRouter 发现结果仍显示：
  - `language: 365`
  - `embedding: 26`
  - `text_to_speech: 41`
  - `speech_to_text: 0`
- 这说明：
  - 代码已经修了
  - 但当前跑着的还是旧后端进程
  - 需要重新打包并冷启动，让新分类逻辑真正生效

### 关于“免费 key”

- `openrouter free` 页面不能一次补齐 `embedding / TTS / STT`。
- 所以本轮不再继续找“免费万能 key”，而是优先用已验证可用的 OpenRouter 接入路径，把现有能力补正。
- 如果后续还要补额外的语音源，再单独接 SenseNova 这类支持面更完整的 provider。

## 下一步

1. 等 EXE 重新打包完成。
2. 冷启动新 EXE，确认 OpenRouter 发现结果里出现 `speech_to_text`。
3. 再跑一次 `POST /api/models/auto-assign`，确认 `default_speech_to_text_model` 被补上。
4. 最后再把这份中文记录更新成最终完成版。
