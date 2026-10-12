#!/bin/bash
# 蔡格尼克 ep.1 —— Yunxi 配音一键包 (Mac 版启动器)
# 双击运行:在本文件夹里建一个独立的小环境(.venv),装好 edge-tts,
# 然后逐句生成配音到 out/ 文件夹。已生成的句子会自动跳过,可断点续跑。
cd "$(dirname "$0")" || exit 1

echo "============================================"
echo "  蔡格尼克 ep.1 Yunxi 配音一键包 (Mac)"
echo "============================================"
echo

# 1) 找 python3
if ! command -v python3 >/dev/null 2>&1; then
  echo "[X] 这台 Mac 还没有可用的 Python3。"
  echo "    去 https://www.python.org/downloads/macos/ 装最新版,"
  echo "    装完再双击本文件即可。"
  echo
  read -r -p "按回车关闭窗口..." _
  exit 1
fi

# 2) 准备独立环境 .venv(第一次才建,之后直接复用)
VENV_PY=".venv/bin/python"
if [ ! -x "$VENV_PY" ]; then
  echo "[准备] 第一次运行:正在创建独立环境(约十几秒)..."
  if ! python3 -m venv .venv; then
    echo "[X] 环境创建失败。如果刚才弹出了苹果的『命令行工具』安装窗,"
    echo "    先把那个装完,再双击本文件一次即可。"
    echo "    还不行就去 python.org 装官方版 Python,再重试。"
    echo
    read -r -p "按回车关闭窗口..." _
    exit 1
  fi
fi

# 3) 装/更新 edge-tts
echo "[1/2] 检查/安装 edge-tts(只需第一次,约几十秒)..."
if ! "$VENV_PY" -m pip install --quiet --upgrade edge-tts; then
  echo "[X] edge-tts 安装失败,多半是网络问题,换个网络再双击一次。"
  echo
  read -r -p "按回车关闭窗口..." _
  exit 1
fi

# 4) 生成配音(make_voice.py 结尾会自己等回车,窗口不会闪退)
echo "[2/2] 开始逐句生成 Yunxi 配音..."
"$VENV_PY" make_voice.py
