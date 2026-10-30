# 素材处理与自动剪辑

下列命令由 `scripts/studio.py run <工具>` 转发。先运行对应子命令 `--help`，不要凭其他工具的同名参数猜用法。路径均使用绝对路径，并为含空格路径加引号。

## 录屏和混剪

录屏由 `free-ai-video/scripts/factory.py record` 或 `record-native` 完成；这个工具箱负责后期。

1. 用 `video info -i <文件>` 检查原片参数。根据实际画面与旁白选择区间，写入项目 shots/media 和素材来源记录。
2. `video cut -i <原片> -o <片段> --start <秒> --duration <秒> --reencode` 做精确裁切。默认 stream-copy 的切点受关键帧影响，不能用作字幕精确对齐。
3. 画幅不同先 `reframe reframe --help`；包含代码/价格表时优先局部构图或模糊填充，检查文字是否被裁掉。
4. `video concat --help` 的 filter 模式可统一分辨率、帧率后拼接；demuxer 模式适用于编码参数相同的片段。项目复杂时交回 `free-ai-video` 的 measured narration timeline 自动编辑。
5. `highlights energy` 只提供能量候选；中文演示更应结合实际动作和 ASR 文本选段。保存采用/舍弃区间，避免“高音量=高价值”。

## 字幕与语音校对

`subtitles parse` 将已有 SRT/VTT/ASS 解析成 cues；`extract` 提取行；由 Codex 逐行翻译，保持行序，再 `merge` 合成双语字幕。禁止翻译调用收费接口。`convert` 转格式，`burn` 烧录。

Windows 的驱动器冒号与反斜杠不能原样拼进 FFmpeg filtergraph。本地版本统一把字幕路径转换为正斜杠并转义驱动器冒号；不要把这次适配覆盖成上游旧文件。

`asr transcribe -i <音视频> -o <字幕.srt> --language zh --model <本地模型目录或small> --device cpu --compute-type int8` 使用 faster-whisper。首次指定模型名可能下载权重；CPU 较慢。识别结果用于检查漏字/数字/重复，不是逐字强制对齐或音色自然度认证。原脚本对过长识别段的二次分句仍按字符比例分配时间，关键切点需查看原音频。

## 混音与特殊画面

`mix mix --help` 可压低音乐以突出旁白；`audio normalize` 调整响度。不要对已经清晰的合成配音反复降噪。神经降噪模式的外部模型不随本技能安装，先确认缺的是什么。

音乐必须具有可用授权，不能从短视频平台任意搬运。资讯解说的节奏优先服务理解；`beats build` 只用于确实需要音乐节拍的片段。`visualizer`、`branding` 和绿幕不算模型能力证据，也不增加真实操作占比。

## 环境

基础：Python、FFmpeg/ffprobe、Pillow。按功能增加 `opencv-python`、`numpy`、`librosa`、`faster-whisper`。先运行 doctor，再装缺项。当前主机默认 pip 清华源；若其 HTTP 403，用户已允许临时使用阿里云国内备用源，保持全局清华配置不变。使用 `--index-url https://mirrors.aliyun.com/pypi/simple`，不要重复全量安装。
