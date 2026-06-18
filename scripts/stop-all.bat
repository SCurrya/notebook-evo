@echo off
chcp 65001 >nul
title Open Notebook - 停止所有服务
color 0C

echo.
echo ================================================================
echo   停止所有 Open Notebook 服务
echo ================================================================
echo.

echo [1/4] 停止 Cloudflare Tunnel...
taskkill /F /IM cloudflared.exe >nul 2>&1
taskkill /F /IM cloudflared-windows-amd64.exe >nul 2>&1
echo   [OK] Cloudflare 已停止

echo [2/4] 停止 Caddy...
taskkill /F /IM caddy.exe >nul 2>&1
echo   [OK] Caddy 已停止

echo [3/4] 停止 Open Notebook API...
:: 找到 run_api.py 的 python 进程并停止
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV /NH 2^>nul ^| findstr "python"') do (
    wmic process where "ProcessId=%%~i" get CommandLine 2>nul | findstr "run_api" >nul
    if !errorlevel! equ 0 (
        taskkill /F /PID %%~i >nul 2>&1
    )
)
:: 备用：按端口找
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5055 " ^| findstr "LISTENING" 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo   [OK] API 已停止

echo [4/4] 停止 SurrealDB...
taskkill /F /IM surreal.exe >nul 2>&1
echo   [OK] SurrealDB 已停止

echo.
echo ================================================================
echo   所有服务已停止
echo ================================================================
echo.
pause
