# 项目当前状态与待办

日期：2026-06-23

## 结论

- EXE 已重新打包并验证可启动。
- 桌面快捷方式已经更新到最新 EXE。
- 当前桌面 EXE 已能拉起后端、访问本地界面，并且 `/api/config` 兼容问题已修复。
- APK 仍暂停在缺少 JDK 21 的现实限制上。

## 已完成

- 已把桌面入口切到轻量版 `api.desktop_main`。
- 已把桌面快捷方式更新到 [E:/notebook/open-notebook/dist/OpenNotebook/OpenNotebook.exe](/E:/notebook/open-notebook/dist/OpenNotebook/OpenNotebook.exe)。
- 已补上桌面版配置兼容，前端不再只依赖单一路径。
- 已把 `PROJECT_REMEDIATION.md` 改成中文状态记录。
- 已统一 `studio` 与 `transformations` 的视觉风格，方向接近 NotebookLM 的浅色研究工作台。
- 已跑过一轮后端定向测试，当前记录为通过。
- 已跑过一轮前端构建，当前记录为通过。
- 已完成一次新 EXE 冷启动验证，`/api/config` 与 `/config` 都返回 200。

## 这次继续处理的内容

- 继续把 `studio`、`transformations`、以及相邻页面统一到同一套浅色风格。
- 继续观察 EXE 的启动稳定性和桌面入口反馈。

## 目前的真实限制

- 机器上暂时没有可用的 JDK 21，所以 APK 还不能按理想状态重新打包。
- 如果后续找到 JDK 21，再继续补 APK。

## 下一步顺序

1. 继续做 UI 细抠。
2. 如有反馈，再针对 EXE 启动日志做补丁。
3. 等 JDK 21 到位后再恢复 APK 打包。
