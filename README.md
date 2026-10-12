# Zeigarnik Episode 01 — 蔡格尼克效应

Vibe 知识大赏短片 Ep.1《为什么你总忘不掉那个没在一起的人？》
成片规格：1920×1080 / 156s / Remotion 流水线出片

## 这个仓库里有什么

本仓库备份的是这集的**配音与后期工具文件**（视频成片文件太大，不进 GitHub，另行保存）：

- `make_voice.py` + `lines.txt` — 云希（Edge TTS zh-CN-YunxiNeural）逐句配音脚本与 28 句校对台词
- `一键配音.bat` / `一键配音-Mac.command` — Windows / Mac 一键配音入口
- `说明.txt` / `Mac使用说明.txt` — 配音包使用说明
- `align_build.py` / `align_build2.py` / `align_build3.py` — AI 重配音与原字幕网格的对齐脚本（v3 为最终版）

## 备注

- Remotion 剧集源码（`src/episodes/zeigarnik/`：script.ts + visuals.tsx）在 Cursor 工程里，待从本机工程推送补充
- 流水线命令：`npm run voice -- <id>` 生成配音 → `npm run render -- <id>` 出片 + 封面
