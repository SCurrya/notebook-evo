# 项目整治最终记录（中文）

日期：2026-06-24

## 本轮目标

1. 修复 EXE 冷启动链路，确保桌面版可稳定拉起。
2. 继续用已验证可用的 OpenRouter 接入，把模型同步和默认分配收口。
3. 让 OpenRouter 的 STT/TTS/Embedding 发现和默认分配回到正确状态。
4. 更新桌面快捷方式到最新 EXE。
5. 做实机冷启动验证，并记录真实结果。

## 已完成

### 1) EXE 冷启动修复

- 已将桌面入口的 API 子进程改为显式环境快照传递，避免继承到脏环境。
- 已把冷启动就绪判断从“端口已被占用”收紧为“`/health` 可正常返回”。
- 已把桌面 API 的 `health` 路由恢复到正确位置，避免被前端 SPA fallback 误吞。
- 重新打包后的 EXE 已通过冷启动实测。

### 2) OpenRouter 模型同步修复

- 已修复 OpenRouter 模型分类逻辑。
- 现在会正确识别：
  - `speech_to_text`
  - `text_to_speech`
  - `embedding`
  - `language`
- 已确认 OpenRouter 发现接口中存在 STT / TTS / Embedding 模型。
- 已执行 OpenRouter 同步，数据库内 OpenRouter 模型总数为 `432`。

### 3) 默认分配收口

- 已执行自动默认分配。
- 当前默认模型状态：
  - `default_chat_model` 已有
  - `default_transformation_model` 已有
  - `large_context_model` 已有
  - `default_embedding_model` 已有
  - `default_text_to_speech_model` 已有
  - `default_speech_to_text_model` 已有
  - `default_tools_model` 已有

### 4) 桌面快捷方式

- 已将桌面上的 Open Notebook 快捷方式更新到最新 EXE：
  - `E:\notebook\open-notebook\dist\OpenNotebook\OpenNotebook.exe`

### 5) 验证结果

- 后端定向测试此前已通过：`27 passed`
- 前端 build 此前已通过
- 本轮实机验证再次确认：
  - `GET /health` 返回 `200`
  - `GET /api/config` 返回正常
  - `GET /api/models/defaults` 返回正常
  - `GET /api/models/count/openrouter` 返回：
    - `language: 365`
    - `embedding: 26`
    - `speech_to_text: 30`
    - `text_to_speech: 11`

## 当前真实结论

- EXE 已重新打包并可正常冷启动。
- 本地 API 服务器可正常访问。
- OpenRouter 的模型同步和默认分配已经收口完成。
- `default_speech_to_text_model` 已补齐，不再为空。

## 当前 EXE 位置

- `E:\notebook\open-notebook\dist\OpenNotebook\OpenNotebook.exe`

## 备注

- 这轮不再依赖“免费万能 key”的猜测，实际是基于当前已验证可用的 OpenRouter 接入链路完成同步与分配。
- 如果后续还要继续扩展语音能力，建议单独引入支持面更完整的 provider，再做二次收口。
