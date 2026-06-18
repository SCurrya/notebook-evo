@echo off
:: 启动 Next.js dev server（3000 端口）
:: 警告：dev server 外部访问 HMR 会失败，建议用 8889 静态版
cd /d E:\notebook\open-notebook\frontend
echo 启动 Next.js dev server...
start "Next.js Dev" /B npm run dev -- -H 0.0.0.0
echo [OK] dev server 启动中（编译需要 20-30 秒）
echo 访问: http://localhost:3000
echo [WARN] 外部访问请用 8889 静态版：http://100.108.217.19:8889
pause
