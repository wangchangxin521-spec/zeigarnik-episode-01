# -*- coding: utf-8 -*-
"""
蔡格尼克效应 ep.1 —— Edge TTS (zh-CN-YunxiNeural) 逐句配音生成器
用法: 双击「一键配音.bat」,或在本目录运行  python make_voice.py
读取同目录 lines.txt(一行一句,顺序与原工程 script.ts 一致),
逐句生成到 out/ 文件夹: 001.mp3, 002.mp3, ...
失败的句子会自动重试 3 次;全部完成后打印汇总。
"""
import subprocess
import sys
import time
from pathlib import Path

VOICE = "zh-CN-YunxiNeural"
RATE = "+0%"   # 语速调整,如 "-5%" 放慢、"+5%" 加快
PITCH = "+0Hz"

BASE = Path(__file__).resolve().parent
LINES_FILE = BASE / "lines.txt"
OUT_DIR = BASE / "out"


def read_lines():
    if not LINES_FILE.exists():
        print("找不到 lines.txt,请确认它和本脚本在同一个文件夹里。")
        sys.exit(1)
    lines = []
    for raw in LINES_FILE.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    return lines


def synth_one(text, dest):
    cmd = [
        sys.executable, "-m", "edge_tts",
        "--voice", VOICE,
        "--rate", RATE,
        "--pitch", PITCH,
        "--text", text,
        "--write-media", str(dest),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0 and dest.exists() and dest.stat().st_size > 0


def main():
    lines = read_lines()
    OUT_DIR.mkdir(exist_ok=True)
    print(f"共 {len(lines)} 句,声音: {VOICE}")
    failed = []
    for i, text in enumerate(lines, 1):
        dest = OUT_DIR / f"{i:03d}.mp3"
        if dest.exists() and dest.stat().st_size > 0:
            print(f"[{i}/{len(lines)}] 已存在,跳过: {text[:20]}...")
            continue
        ok = False
        for attempt in range(1, 4):
            print(f"[{i}/{len(lines)}] 生成中(第{attempt}次): {text[:20]}...")
            if synth_one(text, dest):
                ok = True
                break
            time.sleep(2)
        if not ok:
            failed.append(i)
            print(f"[{i}/{len(lines)}] !! 失败,先跳过,最后会汇总")
    print("=" * 40)
    if failed:
        print(f"完成,但有 {len(failed)} 句失败: {failed}")
        print("重新双击一次即可,只会补失败/缺失的句子(已生成的不重做)。")
    else:
        print(f"全部完成!{len(lines)} 个 mp3 在 out 文件夹里。")
        print("把整个 out 文件夹发回给小噜噜就行。")
    input("按回车关闭窗口...")


if __name__ == "__main__":
    main()
