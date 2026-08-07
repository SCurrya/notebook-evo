@echo off
chcp 65001 >nul
title Open Notebook - 一键启动
color 0A

echo.
echo ================================================================
echo   Open Notebook 一键启动脚本
echo   启动顺序：SurrealDB → API → Caddy → Cloudflare Tunnel
echo ================================================================
echo.

:: ============================================================
:: 0. 检查端口占用，避免重复启动
:: ============================================================
echo [检查] 端口占用情况...
set /a ALREADY_RUNNING=0

netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo   [!] SurrealDB (8000) 已在运行，跳过
    set /a ALREADY_RUNNING+=1
) else (
    echo   [OK] 端口 8000 空闲
)

netstat -ano | findstr ":5055 " | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo   [!] API (5055) 已在运行，跳过
    set /a ALREADY_RUNNING+=1
) else (
    echo   [OK] 端口 5055 空闲
)

netstat -ano | findstr ":8889 " | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo   [!] Caddy (8889) 已在运行，跳过
    set /a ALREADY_RUNNING+=1
) else (
    echo   [OK] 端口 8889 空闲
)

if %ALREADY_RUNNING% equ 3 (
    echo.
    echo ================================================================
    echo   所有服务已在运行！无需重复启动。
    echo   访问地址：
    echo     本机：     http://localhost:8889
    echo     局域网：   http://192.168.5.22:8889
    echo     Tailscale: http://100.108.217.19:8889
    echo   Cloudflare 域名请查看：
    echo     E:\notebook\cloudflared-web.log.err
    echo ================================================================
    echo.
    pause
    exit /b 0
)

echo.

:: ============================================================
:: 1. 启动 SurrealDB (端口 8000)
:: ============================================================
netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul 2>&1
if %errorlevel% neq 0 (
    echo [1/4] 启动 SurrealDB...
    start "SurrealDB" /B "C:\Tools\surreal\surreal.exe" start --user root --pass root --bind 0.0.0.0:8000 rocksdb:E:\notebook\open-notebook\surreal_data\db
    echo   等待 SurrealDB 就绪...
    timeout /t 3 /nobreak >nul
    echo   [OK] SurrealDB 已启动 (0.0.0.0:8000)
) else (
    echo [1/4] SurrealDB 已在运行，跳过
)
echo.

:: ============================================================
:: 2. 启动 Open Notebook API (端口 5055)
:: ============================================================
netstat -ano | findstr ":5055 " | findstr "LISTENING" >nul 2>&1
if %errorlevel% neq 0 (
    echo [2/4] 启动 Open Notebook API...
    set DATA_FOLDER=E:\notebook\open-notebook\data
    set PYTHONPATH=E:\notebook\open-notebook
    set API_HOST=0.0.0.0
    set API_PORT=5055
    set API_RELOAD=false
    start "OpenNotebook-API" /B "E:\notebook\open-notebook\.venv\Scripts\python.exe" run_api.py
    echo   等待 API 就绪（约 15-20 秒）...
    timeout /t 18 /nobreak >nul
    echo   [OK] API 已启动 (0.0.0.0:5055)
) else (
    echo [2/4] API 已在运行，跳过
)
echo.

:: ============================================================
:: 3. 启动 Caddy (端口 8888 API + 8889 前端)
:: ============================================================
netstat -ano | findstr ":8889 " | findstr "LISTENING" >nul 2>&1
if %errorlevel% neq 0 (
    echo [3/4] 启动 Caddy...
    start "Caddy" /B "E:\notebook\downloads\caddy\caddy.exe" run --config "E:\notebook\downloads\caddy\Caddyfile" --adapter caddyfile
    timeout /t 3 /nobreak >nul
    echo   [OK] Caddy 已启动 (8888 API + 8889 前端)
) else (
    echo [3/4] Caddy 已在运行，跳过
)
echo.

:: ============================================================
:: 4. 启动 Cloudflare Tunnel（临时隧道，域名每次重启会变）
:: ============================================================
echo [4/4] 启动 Cloudflare Tunnel...

:: 清理旧日志
del /Q "E:\notebook\cloudflared-api.log.err" 2>nul
del /Q "E:\notebook\cloudflared-web.log.err" 2>nul

:: 启动 Web 隧道（8889 Caddy 统一入口，手机只需一个 URL）
start "CF-Web" /B "E:\notebook\downloads\cloudflared.exe" tunnel --url http://localhost:8889 --no-autoupdate --protocol http2

:: 启动 API 隧道（5055，供 APK 直连）
start "CF-API" /B "E:\notebook\downloads\cloudflared.exe" tunnel --url http://localhost:5055 --no-autoupdate --protocol http2

echo   等待隧道建立连接（15 秒）...
timeout /t 15 /nobreak >nul
echo   [OK] Cloudflare 隧道已启动
echo.

:: ============================================================
:: 5. 显示所有访问地址
:: ============================================================
echo ================================================================
echo   全部服务已启动！
echo ================================================================
echo.
echo --- 访问地址（按稳定性排序）---
echo.
echo   [局域网]  http://192.168.5.22:8889
echo             ^| 同 WiFi 最快，地址永远不变
echo.
echo   [Tailscale] http://100.108.217.19:8889
echo             ^| 需手机 Tailscale VPN 已连接
echo.
echo   [Cloudflare Web] （见下方域名）
echo             ^| 无需 VPN，任何网络可用，但重启会变
echo.

echo --- Cloudflare 临时域名 ---
echo.
echo   Web 域名（手机浏览器用这个）：
findstr /C:"trycloudflare.com" "E:\notebook\cloudflared-web.log.err" 2>nul
echo.
echo   API 域名（APK 直连用）：
findstr /C:"trycloudflare.com" "E:\notebook\cloudflared-api.log.err" 2>nul
echo.

echo --- 登录密码 ---
echo   密码见 .env 文件中的 OPEN_NOTEBOOK_PASSWORD
echo   路径：E:\notebook\open-notebook\.env
echo.

echo --- 服务管理 ---
echo   查看运行状态：  E:\notebook\scripts\health-check.ps1
echo   停止所有服务：  E:\notebook\scripts\stop-all.bat
echo   配置开机自启：  E:\notebook\scripts\register-services.ps1 (管理员)
echo ================================================================
echo.
echo 提示：此窗口可以关闭，服务在后台运行。
echo.
pause
