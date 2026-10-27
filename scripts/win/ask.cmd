@echo off
rem 用法：ask.cmd "今年适合跳槽吗"
rem 输出：可粘贴给任意 AI 的提示包
setlocal
cd /d "%~dp0..\.."
set "Q=%~1"
if "%Q%"=="" (
  set "Q=整体态势"
)
set "ENGINE=%ZIWEI_ENGINE_ROOT%"
if "%ENGINE%"=="" set "ENGINE=F:\github\ziwei-doushu"
if not exist "%ENGINE%\lib\ziwei\algorithm.ts" (
  echo [提示] 未找到排盘引擎：%ENGINE%
  echo        仅用演示盘生成提示包；自排盘请设置 ZIWEI_ENGINE_ROOT。
  python packages\hypergraph\chart2hypergraph.py fixtures\sample-chart.json --matter "%Q%"
  goto :eof
)
python packages\hypergraph\chart2hypergraph.py fixtures\sample-chart.json --matter "%Q%"