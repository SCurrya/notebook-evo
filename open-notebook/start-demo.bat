@echo off
REM ============================================================
REM  Notebook-Evo 一键演示模式
REM  启动 SurrealDB -> 初始化演示数据 -> 启动 API -> 打开浏览器
REM ============================================================
setlocal
cd /d "%~dp0"

echo ============================================================
echo   Notebook-Evo 一键演示启动
echo ============================================================

REM 1. 检查虚拟环境
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] 未找到虚拟环境，请先运行: uv sync
    pause
    exit /b 1
)

REM 2. 检查 SurrealDB
if not exist "surreal.exe" (
    echo [ERROR] 未找到 surreal.exe
    pause
    exit /b 1
)

REM 3. 启动 SurrealDB（若未运行）
echo [1/4] 启动 SurrealDB...
tasklist /fi "imagename eq surreal.exe" 2>nul | find /i "surreal.exe" >nul
if errorlevel 1 (
    start "SurrealDB" surreal.exe start --log info --user root --pass root --bind 127.0.0.1:8000 rocksdb:./surreal_data/db
    echo       等待 SurrealDB 就绪...
    timeout /t 8 /nobreak >nul
) else (
    echo        SurrealDB 已在运行
)

REM 4. 初始化演示数据
echo [2/4] 初始化演示数据...
".venv\Scripts\python.exe" scripts\seed_demo_data.py
if errorlevel 1 (
    echo [WARN] 演示数据初始化出现异常，继续启动
)

REM 5. 启动 API
echo [3/4] 启动 API 服务...
set API_RELOAD=false
start "Notebook-Evo API" cmd /c ".venv\Scripts\python.exe run_api.py"

REM 6. 等待 API 就绪并打开浏览器
echo [4/4] 等待 API 就绪...
timeout /t 15 /nobreak >nul
start http://127.0.0.1:8502

echo.
echo ============================================================
echo   演示模式已启动!
echo   Web UI : http://127.0.0.1:8502
echo   API    : http://127.0.0.1:5055
echo   关闭 API 窗口即可停止服务
echo ============================================================
endlocal
