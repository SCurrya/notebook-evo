@echo off
:: 停止 Next.js dev server（3000 端口）
:: 因为静态文件版（8889）已经能用，dev server 不需要一直跑
echo 停止 Next.js dev server...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000') do (
  echo 杀掉 PID %%a
  taskkill /F /PID %%a 2>nul
)
echo [OK] dev server 已停止
echo.
echo 接下来用 8889 静态版:
echo   http://localhost:8889
echo   http://100.108.217.19:8889
pause
