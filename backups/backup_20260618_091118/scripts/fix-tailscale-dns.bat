@echo off
chcp 65001 >nul
title Tailscale DNS 修复（需管理员）
color 0E

echo.
echo ================================================================
echo   Tailscale DNS 权限修复
echo   解决 "Access is denied" 和 "can't reach DNS" 错误
echo ================================================================
echo.

:: 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 需要管理员权限！
    echo   右键此文件 → 以管理员身份运行
    echo   或在管理员 PowerShell 中执行：
    echo     tailscale up --accept-dns=false
    pause
    exit /b 1
)

echo [1/2] 重启 Tailscale 服务...
net stop Tailscale >nul 2>&1
timeout /t 2 /nobreak >nul
net start Tailscale >nul 2>&1
echo   [OK] Tailscale 服务已重启

echo.
echo [2/2] 配置 Tailscale（禁用 MagicDNS，用 IP 访问）...
"C:\Program Files\Tailscale\tailscale.exe" up --accept-dns=false --reset
echo   [OK] 配置完成

echo.
echo ================================================================
echo   修复完成！
echo ================================================================
echo.
echo   说明：
echo   - --accept-dns=false 禁用 Tailscale 的 DNS 配置
echo   - 不影响 IP 访问（TAILSCALE_IP_PLACEHOLDER:8889 仍可用）
echo   - 只是 MagicDNS 域名（laptop-xxx.ts.net）不可用
echo   - 这样就不会再报 "Access is denied" 错误
echo.
echo   验证：
echo     tailscale status
echo.
pause
