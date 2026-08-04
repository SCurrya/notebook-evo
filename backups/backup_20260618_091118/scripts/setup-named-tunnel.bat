@echo off
chcp 65001 >nul
title Cloudflare 命名隧道配置（固定域名）
color 0B

echo.
echo ================================================================
echo   Cloudflare 命名隧道配置向导
echo   一次性配置，域名永久不变！
echo ================================================================
echo.
echo 前提条件：
echo   1. 拥有一个 Cloudflare 托管的域名（免费注册即可）
echo      例如：yourdomain.com（在 Cloudflare DNS 管理）
echo   2. cloudflared 已安装（E:\notebook\downloads\cloudflared.exe）
echo.
echo 配置完成后：
echo   - 域名永久不变（如 notebook.yourdomain.com）
echo   - APK 和手机不用再更新域名
echo   - PC 重启后自动恢复（配合 start-all.bat）
echo.
echo ================================================================
echo.

set /p DOMAIN="请输入你的域名（如 notebook.yourdomain.com）: "
if "%DOMAIN%"=="" (
    echo [错误] 域名不能为空
    pause
    exit /b 1
)

echo.
echo [1/4] 登录 Cloudflare（浏览器会打开授权页面）...
echo ================================================================
"E:\notebook\downloads\cloudflared.exe" tunnel login
if %errorlevel% neq 0 (
    echo [错误] 登录失败
    pause
    exit /b 1
)
echo [OK] 登录成功
echo.

echo [2/4] 创建命名隧道...
echo ================================================================
"E:\notebook\downloads\cloudflared.exe" tunnel create open-notebook
if %errorlevel% neq 0 (
    echo [提示] 隧道可能已存在，尝试继续...
)
echo [OK] 隧道创建完成
echo.

echo [3/4] 配置 DNS 路由（%DOMAIN% -> 隧道）...
echo ================================================================
"E:\notebook\downloads\cloudflared.exe" tunnel route dns open-notebook %DOMAIN%
if %errorlevel% neq 0 (
    echo [错误] DNS 路由配置失败
    pause
    exit /b 1
)
echo [OK] DNS 路由已配置
echo.

echo [4/4] 生成隧道配置文件...
echo ================================================================

:: 获取隧道 ID
for /f "tokens=2" %%i in ('"E:\notebook\downloads\cloudflared.exe" tunnel list 2^>nul ^| findstr "open-notebook"') do (
    set TUNNEL_ID=%%i
)

:: 写入配置文件
set CONFIG_FILE=E:\notebook\downloads\cloudflared-named.yml
(
    echo tunnel: %TUNNEL_ID%
    echo credentials-file: C:\Users\ZS\.cloudflared\%TUNNEL_ID%.json
    echo.
    echo ingress:
    echo   # Web 前端 + API（Caddy 统一入口）
    echo   - hostname: %DOMAIN%
    echo     service: http://localhost:8889
    echo   # 兜底
    echo   - service: http_status:404
) > "%CONFIG_FILE%"

echo [OK] 配置文件已生成: %CONFIG_FILE%
echo.

echo ================================================================
echo   配置完成！
echo ================================================================
echo.
echo   固定域名: https://%DOMAIN%
echo   配置文件: %CONFIG_FILE%
echo.
echo   启动命名隧道（替代临时隧道）:
echo     "E:\notebook\downloads\cloudflared.exe" tunnel --config "%CONFIG_FILE%" run open-notebook
echo.
echo   或者用一键启动脚本（已自动支持命名隧道）
echo.
echo   下一步：
echo   1. 更新 .env 中的 CLOUDFLARE_DOMAIN=https://%DOMAIN%
echo   2. 更新 APK 中的 Cloudflare 域名
echo   3. 用 start-all.bat 启动服务
echo ================================================================
echo.
pause
