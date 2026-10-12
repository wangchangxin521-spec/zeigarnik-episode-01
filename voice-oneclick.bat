@echo off
chcp 65001 >nul
cd /d %~dp0
echo ============================================
echo   蔡格尼克 ep.1 Yunxi 配音一键包
echo ============================================
echo.

where py >nul 2>nul && set PY=py || set PY=python
%PY% --version >nul 2>nul
if errorlevel 1 (
  echo [X] 这台电脑还没装 Python。
  echo     去 https://www.python.org/downloads/ 装最新版,
  echo     安装第一屏记得勾选 "Add python.exe to PATH",
  echo     装完再双击本文件即可。
  pause
  exit /b 1
)

echo [1/2] 检查/安装 edge-tts(只需第一次,约几十秒)...
%PY% -m pip install --quiet --upgrade edge-tts
if errorlevel 1 (
  echo [X] edge-tts 安装失败,多半是网络问题,换个网络再双击一次。
  pause
  exit /b 1
)

echo [2/2] 开始逐句生成 Yunxi 配音...
%PY% make_voice.py
