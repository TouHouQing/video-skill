# 派生素材、缓存和真实录屏衔接

仅当素材确实需要独立加工或跨次修改复用时启用跟踪；主剪辑器可以用 source_in/out、speed、camera 完成的任务优先在时间轴处理，省掉中间编码。

## 跟踪一次加工

```text
python scripts/studio.py run --input C:/job/raw.mp4 --output C:/job/trim.mp4 --reuse video cut -i C:/job/raw.mp4 -o C:/job/trim.mp4 --start 3 --duration 8 --reencode
```

`--input`、`--output`、`--reuse` 是启动器参数，放在 `video` 等工具名之前。工具自己的参数保持原样。辅助文件也必须声明，例如字幕烧录加第二个 `--input C:/job/captions.srt`。输入和输出路径都须出现在实际工具参数中；仅支持跟踪一个输出，多文件/目录输出先按工具原命令执行并逐项登记。

成功后生成 `trim.mp4.processing.json`：命令、工具及包装层代码哈希、输入哈希、输出哈希和完成时间。保留媒体扩展名，避免同名视频/音频/字幕覆盖彼此的记录。输入、参数或代码变更会重新加工；输出丢失、被改动或前次失败也不会命中缓存。复用时不重写证明文件，保持下游引用稳定。原片必须保留，不能覆盖输入。

新工具参数中凡影响结果的外部文件都要列入输入。自动识别模型名、外部模型版本和硬件非确定性不由文件缓存自动证明；ASR 模型/配置更换后使用新输出路径或不加 reuse。缓存不校验观点是否仍然适用于当前新闻，价格和发布信息仍需重新核查。

## 接回视频主流程

未经处理的录屏继续用现有 `.recording.json`。需要外部裁切/转画幅后，在项目媒体记录中保留原录屏证明，同时增加派生记录：

```json
{
  "id": "operation-closeup",
  "type": "video",
  "path": "trim.mp4",
  "recording_manifest": "raw.recording.json",
  "processing_manifest": "trim.mp4.processing.json",
  "role": "target_app",
  "rights": {"kind": "original_capture"}
}
```

多步加工时，下步主输入的同名 `.processing.json` 会自动成为父记录。生产预检递归检查输入、输出及父记录，追溯到原录屏 SHA；任一环不匹配就停止，不能改标 owned 来绕过真实性。所有路径在处理记录里保存为绝对路径；跨机器移动需要重新解析素材路径/重新生成记录。

目前仅将保留原画面的 `video cut/speed/aspect/compress`、`reframe reframe`、`subtitles burn` 识别为可追溯录屏派生。主输入必须是第一个声明的输入；其他种类有处理记录也不自动算作真实操作。拼接多个来源、波形可视化、片头片尾、图像转视频等不能靠一条父录屏链获得 original_capture 身份；按实际素材和使用权分别登记。

源文件、许可证和实际录屏是否真实仍由 Codex 查看并核实。哈希链证明文件衔接，不证明内容含义、权利或新闻结论。处理同一录屏产生的多个版本按同一个原素材计算，不用裁切增加来源数量。
