# Open Notebook 凭据记录（请妥善保管，建议存到密码管理器）

> **警告**：本文件包含明文凭据，仅用于本地记录。请保存到 1Password / Bitwarden / KeePass 等密码管理器后立即删除本文件。

## PC 后端访问

- API 端点: http://localhost:5055
- API 文档: http://localhost:5055/docs
- API 密码 (Bearer token / Authorization header): `XOZ/cGdE1boChyPfPKy9H9cKW+xvhx16WM4QQXxgMJM=`

## Tailscale

- 账号: scurry413a@
- 节点: laptop-62burom0
- 域名: laptop-62burom0.taile2bacf.ts.net
- Tailscale IP: 100.108.217.19

## 数据库 (SurrealDB)

- URL: ws://127.0.0.1:8000/rpc
- 用户: root
- 密码: root（默认值，建议改成强随机密码）

## 加密密钥

- OPEN_NOTEBOOK_ENCRYPTION_KEY: `HHuk2IRyhYSyZpoZqaogI4lNJaJ0hsl4B8ghKeoH/LEHoSqZJqZjDBgW5/3oJnE/`
- 用途: 加密数据库中存储的 AI provider 凭据（OpenAI、Anthropic 等 API key）
- 注意: 更换此密钥会导致已加密的所有凭据无法解密

## CORS 辅助 token

- ycbaFxD+cNn9KLl5mqaPjw==

---

生成时间: 2026-06-17
生成工具: .NET System.Security.Cryptography.RandomNumberGenerator (CSPRNG)
