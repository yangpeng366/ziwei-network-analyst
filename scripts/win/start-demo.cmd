@echo off
rem 双击启动本地演示页：http://127.0.0.1:8765/
setlocal
cd /d "%~dp0..\.."
where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 未找到 python，请先安装 Python 3.9+ 并加入 PATH。
  pause
  exit /b 1
)
echo 正在启动紫微四因子演示页...
start "" http://127.0.0.1:8765/
python web\server.py
pause