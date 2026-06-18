@echo off
:: ================================================================
:: 启动 Cloudflare 临时隧道（http2 协议，兼容代理环境）
:: 暴露 Open Notebook API (5055) 和前端 (8889 Caddy 统一入口) 到公网
:: 完全绕开 Tailscale / Nekobox，无需 VPN
:: ================================================================
:: 关键改进：
::   1. --protocol http2：使用 TCP 443，绕开 Mihomo/代理对 QUIC/UDP 的拦截
::   2. Web 隧道指向 8889（Caddy 静态文件端口），手机一个 URL 即可访问
::      前端 + API（Caddy 内部 /api/* 反代到 5055），无需双隧道
:: ================================================================

chcp 65001 >nul
title Cloudflare Quick Tunnel - Open Notebook

echo.
echo ============================================================
echo  Cloudflare Tunnel 启动器（http2 协议）
echo  暴露端口：API 5055 + Web 8889（Caddy 统一入口）
echo ============================================================
echo.

:: 清理旧日志
del /Q "E:\notebook\cloudflared-api.log"  2>nul
del /Q "E:\notebook\cloudflared-api.log.err"  2>nul
del /Q "E:\notebook\cloudflared-web.log"  2>nul
del /Q "E:\notebook\cloudflared-web.log.err"  2>nul

:: 启动 API 隧道（5055，http2 协议）
start "Cloudflare-API" /B "E:\notebook\downloads\cloudflared.exe" tunnel --url http://localhost:5055 --no-autoupdate --protocol http2
echo [OK] API 隧道已启动（PID 即将打印到 cloudflared-api.log.err）

:: 启动前端隧道（8889 Caddy 统一入口，http2 协议）
start "Cloudflare-Web" /B "E:\notebook\downloads\cloudflared.exe" tunnel --url http://localhost:8889 --no-autoupdate --protocol http2
echo [OK] Web 隧道已启动（PID 即将打印到 cloudflared-web.log.err）

echo.
echo ============================================================
echo  等待 15 秒让两个隧道建立连接...
echo ============================================================
timeout /t 15 /nobreak >nul

echo.
echo ===== API 临时域名 =====
findstr /C:"trycloudflare.com" "E:\notebook\cloudflared-api.log.err"

echo.
echo ===== Web 临时域名（手机用这一个即可） =====
findstr /C:"trycloudflare.com" "E:\notebook\cloudflared-web.log.err"

echo.
echo ============================================================
echo  两个 Cloudflare 隧道已在后台运行（http2 协议）
echo  临时域名查看：
echo    E:\notebook\cloudflared-api.log.err
echo    E:\notebook\cloudflared-web.log.err
echo.
echo  手机访问：使用 Web 临时域名（Caddy 8889 内部反代 API）
echo.
echo  关闭命令（管理员 PowerShell）：
echo    Get-Process cloudflared | Stop-Process -Force
echo ============================================================
echo.
pause
