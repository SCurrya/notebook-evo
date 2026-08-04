@echo off
setlocal

:: 1. 环境检查
echo [1/4] 检查环境...
if not exist "C:\Tools\android-sdk" goto :error_sdk
if not exist "E:\C\Java\jdk-18.0.1.1" goto :error_jdk

set ANDROID_HOME=C:\Tools\android-sdk
set JAVA_HOME=E:\C\Java\jdk-18.0.1.1
set PATH=%JAVA_HOME%\bin;%ANDROID_HOME%\platform-tools;%ANDROID_HOME%\cmdline-tools\latest\bin;%PATH%

:: 2. 构建 Next.js 静态导出
echo [2/4] 构建 Next.js 静态导出...
cd /d E:\notebook\open-notebook\frontend
if exist .next rmdir /s /q .next
if exist out rmdir /s /q out

:: 注入移动端 API 发现域名（构建时烘焙到 APK）
set NEXT_PUBLIC_TAILSCALE_DOMAIN=100.108.217.19
:: Cloudflare 域名每次重启会变，这里设为当前域名，硬编码 IP 是更可靠的 fallback
for /f "tokens=*" %%i in ('findstr /C:"trycloudflare.com" "E:\notebook\cloudflared-web.log.err" 2^>nul ^| findstr /R "https://.*trycloudflare.com"') do (
    set NEXT_PUBLIC_CLOUDFLARE_DOMAIN=%%i
)
:: 如果没找到域名，用占位符（硬编码 IP 仍会工作）
if not defined NEXT_PUBLIC_CLOUDFLARE_DOMAIN set NEXT_PUBLIC_CLOUDFLARE_DOMAIN=shower-tubes-reasonably-incredible.trycloudflare.com

echo   NEXT_PUBLIC_TAILSCALE_DOMAIN=%NEXT_PUBLIC_TAILSCALE_DOMAIN%
echo   NEXT_PUBLIC_CLOUDFLARE_DOMAIN=%NEXT_PUBLIC_CLOUDFLARE_DOMAIN%

call npm run build:mobile
if errorlevel 1 goto :error_build

:: 3. 同步到 Android
echo [3/4] 同步到 Android 项目...
cd /d E:\notebook\mobile-app
call npx cap sync android
if errorlevel 1 goto :error_sync

:: 4. 构建 APK
echo [4/4] 构建 APK...
cd /d E:\notebook\mobile-app\android
call gradlew.bat assembleDebug
if errorlevel 1 goto :error_gradle

echo.
echo ======================================
echo 构建成功！
echo APK 位置: E:\notebook\mobile-app\android\app\build\outputs\apk\debug\app-debug.apk
echo 安装命令: adb install -r "E:\notebook\mobile-app\android\app\build\outputs\apk\debug\app-debug.apk"
echo ======================================
pause
exit /b 0

:error_sdk
echo [错误] Android SDK 未安装在 C:\Tools\android-sdk
pause
exit /b 1

:error_jdk
echo [错误] JDK 未安装在 E:\C\Java\jdk-18.0.1.1
pause
exit /b 1

:error_build
echo [错误] Next.js 移动端构建失败
pause
exit /b 1

:error_sync
echo [错误] Capacitor 同步失败
pause
exit /b 1

:error_gradle
echo [错误] Gradle 构建失败
pause
exit /b 1
