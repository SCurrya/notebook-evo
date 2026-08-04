# 新 IDE 接手清单（最短路径版）

日期：2026-06-26

## 当前确认过的事实

- EXE 产物在：`E:\notebook\open-notebook\dist\OpenNotebook\OpenNotebook.exe`
- 桌面快捷方式已指向这个 EXE
- `GET /health`、`GET /api/config`、`GET /api/models/defaults` 在本地曾经能通
- OpenRouter 同步和默认分配曾经跑过一次，`default_speech_to_text_model` 也曾补上
- 但用户最终仍反馈“还是用不了”，所以当前不能把项目视为真正完成

## 最短入口

1. 先开这个 EXE：
   - `E:\notebook\open-notebook\dist\OpenNotebook\OpenNotebook.exe`
2. 先看这几个接口：
   - `http://127.0.0.1:8502/health`
   - `http://127.0.0.1:8502/api/config`
   - `http://127.0.0.1:8502/api/models/defaults`
   - `http://127.0.0.1:8502/api/models/count/openrouter`
3. 再看主路径：
   - 笔记本列表
   - 打开单个笔记本
   - 来源列表
   - API Key / 模型页

## 先查什么

1. 是否有旧进程残留
2. 是否有旧快捷方式或旧入口
3. 前端页面拿到的 API 地址是否正确
4. 笔记本、来源、模型页是否能联动刷新
5. Studio / Transformations 是否和主界面风格一致但功能仍正常

## 已知风险

- 代码库是 dirty worktree，历史并行改动很多
- 之前的“已修复”有一部分只算局部验证，不等于端到端可用
- UI、API Key、来源、笔记本、Studio、Transformations 仍需要实机串起来看

## 不要先做

- 不要先相信某个单接口 200 就算修好
- 不要先看 build 结果就当功能没问题
- 不要先假设旧进程已经退出
- 不要先假设模型同步完成就代表页面也正常

## 当前真正需要的结果

- 打开 EXE 后能顺滑进入首页
- 笔记本、来源、API Key、模型页都能正常工作
- 模型同步后默认分配能稳定落地
- `studio`、`transformations` 这几页风格统一，且没有功能回归

