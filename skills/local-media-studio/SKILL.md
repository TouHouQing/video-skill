---
name: local-media-studio
description: 用本地 FFmpeg、Pillow 和可选 Whisper 处理视频、音频、图片、字幕；适用于自动剪辑、素材混剪、横转竖、双语字幕、混音和长视频切片，不需要 Easel 工作台或付费 API。
---

# 本地媒体工具箱

14 个随技能安装的本地工具直接处理媒体文件。按具体任务选工具：`list` 查用途，`run <工具> <子命令> --help` 查真实参数；不要把所有工具串成固定流程。完整视频先用 `free-ai-video` 的时间轴能力；只有额外处理确有价值时才预处理，减少重复编码。

```text
python scripts/studio.py doctor
python scripts/studio.py list
python scripts/studio.py run video cut -i <原片> -o <片段> --start 12 --duration 8 --reencode
```

读取 [媒体工作流](references/media-workflows.md) 选择字幕、ASR、混音、节拍、画幅等操作，并按 [处理记录与复用](references/processing-reuse.md) 追踪需要复用的派生素材。

```text
python scripts/studio.py run --input <原片> --output <片段> --reuse video cut -i <原片> -o <片段> --start 12 --duration 8 --reencode
```

跟踪参数放在工具名之前。它生成 `<输出文件名>.processing.json`，核对输入、参数、工具代码和输出哈希后才复用。主输入放在第一个 `--input`；字幕、音乐等辅助输入也逐个声明。输出不能覆盖输入。处理记录不是新的录屏证明，图片/波形/生成内容不能借它冒充实际操作。

先看原片、读字幕、确定语义，再定切点。能量峰值和节拍只生成候选；新闻以完整观点、动作与结果为准。横转竖要保住被讲解的表格/代码/结果。保留原件、来源和使用依据，检查时长、音画、字幕、画幅及转场。

启动器自动使用本技能 `.runtime/runtime.json` 指定的环境；基础需 FFmpeg/ffprobe 和 Pillow，其他依赖按需使用。缺库才运行 `scripts/bootstrap.py`。ASR 库和模型权重分开，未实际识别时不声称转写通过。此处无云生成、云 TTS 或账号发布接口。

Easel 代码的 Apache-2.0 许可证、来源与修改记录在 `third_party/Easel/`；本地包装层和记录协议独立维护，不修改上游文件来增加编排逻辑。
