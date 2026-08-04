@echo off
chcp 65001 >nul 2>&1
REM ============================================================
REM Open Notebook - Windows Native One-Click Startup Script
REM No Docker, no WSL. Just SurrealDB + FastAPI + Worker + Next.js
REM ============================================================

setlocal EnableDelayedExpansion

REM ---- Paths (edit these if you installed elsewhere) ----
set "ROOT=E:\notebook\open-notebook"
set "DATA_ROOT=E:\notebook\open-notebook-data"
set "SURREAL_BIN=C:\Tools\surreal\surreal.exe"

REM ---- Derived env (consumed by config.py / surreal-commands-worker) ----
set "DATA_FOLDER=%DATA_ROOT%"
set "PYTHONPATH=%ROOT%"

echo ============================================================
echo   Open Notebook - Native Windows One-Click Startup
echo   ROOT     = %ROOT%
echo   DATA     = %DATA_ROOT%
echo ============================================================
echo.

REM ---- Pre-flight: Check prerequisites ----
echo [Check] Verifying prerequisites...

if not exist "%ROOT%\.venv\Scripts\python.exe" (
    echo [ERROR] Python venv not found at %ROOT%\.venv
    echo         Run: cd /d %ROOT% ^&^& uv sync
    pause
    exit /b 1
)
if not exist "%SURREAL_BIN%" (
    echo [ERROR] SurrealDB not found at %SURREAL_BIN%
    echo         Download v2.3.7 from: https://github.com/surrealdb/surrealdb/releases
    pause
    exit /b 1
)
if not exist "%ROOT%\frontend\node_modules" (
    echo [ERROR] Frontend deps not installed.
    echo         Run: cd /d %ROOT%\frontend ^&^& npm install
    pause
    exit /b 1
)
echo [Check] Prerequisites OK.
echo.

REM ---- Pre-flight: Fix Windows native binding stubs ----
REM These packages repeatedly ship as stubs or get corrupted on Windows.
REM We check every time because rebooting can corrupt them.
echo [Check] Verifying Windows native bindings...

set "SWC_BIN=%ROOT%\frontend\node_modules\@next\swc-win32-x64-msvc\next-swc.win32-x64-msvc.node"
set "OXIDE_BIN=%ROOT%\frontend\node_modules\@tailwindcss\oxide-win32-x64-msvc\tailwindcss-oxide.win32-x64-msvc.node"
set "RHF_ESM=%ROOT%\frontend\node_modules\react-hook-form\dist\index.esm.mjs"
set "HOOKFORM_DIST=%ROOT%\frontend\node_modules\@hookform\resolvers\dist\resolvers.mjs"

set "NEED_FIX=0"
if not exist "%SWC_BIN%"      set "NEED_FIX=1"
if not exist "%OXIDE_BIN%"    set "NEED_FIX=1"
if not exist "%RHF_ESM%"      set "NEED_FIX=1"
if not exist "%HOOKFORM_DIST%" set "NEED_FIX=1"

if "%NEED_FIX%"=="1" (
    echo [Fix] Detected missing/corrupted Windows native bindings.
    echo [Fix] Reinstalling: SWC, Tailwind oxide, react-hook-form, hookform/resolvers...
    pushd "%ROOT%\frontend"
    call npm install @tailwindcss\oxide-win32-x64-msvc@latest --save-optional
    call npm install react-hook-form@7.60.0 @hookform/resolvers@5.1.1
    call npm install @next\swc-win32-x64-msvc@16.2.6 --save-optional
    popd
    echo [Fix] Native bindings reinstalled.
) else (
    echo [Check] Native bindings OK.
)
echo.

REM ---- Kill any leftover processes from previous run ----
echo [Cleanup] Stopping any leftover services...
taskkill /F /IM surreal.exe 2>nul
REM Don't kill all python.exe - might kill other apps. Only kill if on our ports.
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5055 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a 2>nul
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a 2>nul
)
echo [Cleanup] Done.
echo.

REM ---- 1. SurrealDB (port 8000) ----
echo [1/4] Starting SurrealDB on 127.0.0.1:8000 ...
start "OpenNotebook-DB" cmd /k ^
    "%SURREAL_BIN% start --user root --pass root --bind 127.0.0.1:8000 rocksdb:%DATA_ROOT%\surrealdb\mydatabase.db"

echo       Waiting for SurrealDB to be ready...
set "DB_READY=0"
for /l %%i in (1,1,10) do (
    timeout /t 2 /nobreak >nul
    powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop; exit 0 } catch { exit 1 }" 2>nul
    if !errorlevel! equ 0 (
        set "DB_READY=1"
        echo       SurrealDB is ready!
        goto :db_done
    )
    echo       Still waiting... %%i/10
)
:db_done
if "!DB_READY!"=="0" (
    echo [WARN] SurrealDB health check failed, but continuing anyway...
)
echo.

REM ---- 2. FastAPI (port 5055) ----
echo [2/4] Starting API on 0.0.0.0:5055 ...
start "OpenNotebook-API" cmd /k ^
    "cd /d %ROOT% && set DATA_FOLDER=%DATA_ROOT%&& set PYTHONPATH=%ROOT%&& uv run --env-file .env uvicorn api.main:app --host 0.0.0.0 --port 5055"

echo       Waiting for API to be ready...
set "API_READY=0"
for /l %%i in (1,1,30) do (
    timeout /t 3 /nobreak >nul
    powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:5055/health' -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop; exit 0 } catch { exit 1 }" 2>nul
    if !errorlevel! equ 0 (
        set "API_READY=1"
        echo       API is ready!
        goto :api_done
    )
    echo       Still waiting... %%i/30
)
:api_done
if "!API_READY!"=="0" (
    echo [WARN] API health check failed, but continuing anyway...
)
echo.

REM ---- 3. Surreal Commands Worker ----
echo [3/4] Starting Worker ...
start "OpenNotebook-Worker" cmd /k ^
    "cd /d %ROOT% && set DATA_FOLDER=%DATA_ROOT%&& set PYTHONPATH=%ROOT%&& uv run --env-file .env python -m surreal_commands.cli.worker --import-modules commands"

timeout /t 3 /nobreak >nul
echo       Worker started.
echo.

REM ---- 4. Next.js Frontend (port 3000) ----
echo [4/4] Starting Frontend on 0.0.0.0:3000 ...
start "OpenNotebook-Frontend" cmd /k ^
    "cd /d %ROOT%\frontend && set API_URL=http://localhost:5055&& set NEXT_PUBLIC_API_URL=http://localhost:5055&& set INTERNAL_API_URL=http://localhost:5055&& node node_modules\next\dist\bin\next dev -H 0.0.0.0 -p 3000"

echo       Waiting for Frontend port to be listening...
set "FE_READY=0"
for /l %%i in (1,1,30) do (
    timeout /t 2 /nobreak >nul
    netstat -aon | findstr ":3000 " | findstr "LISTENING" >nul 2>&1
    if !errorlevel! equ 0 (
        set "FE_READY=1"
        echo       Frontend port is listening!
        goto :fe_done
    )
    echo       Still starting... %%i/30
)
:fe_done
if "!FE_READY!"=="0" (
    echo [WARN] Frontend port not yet listening.
    echo        Check the Frontend window for errors.
) else (
    echo [NOTE] Port is open but first page load triggers Next.js dev compilation.
    echo        On slow drives this can take 1-5 minutes. Just wait and refresh.)
echo.

echo ============================================================
echo   All services started!
echo.
echo   - Frontend:  http://127.0.0.1:3000
echo   - API docs:  http://127.0.0.1:5055/docs
echo   - SurrealDB: ws://127.0.0.1:8000
echo.
echo   Each service runs in its own window.
echo   Close the corresponding window to stop a service.
echo.
echo   To stop everything:
echo     taskkill /F /IM surreal.exe
echo     (then close API/Worker/Frontend windows)
echo ============================================================
echo.
echo Tip: First page load may take 1-5 minutes on slow drives (Next.js dev compilation).
echo      Subsequent loads are fast. Just wait and refresh.
echo.
pause
endlocal
