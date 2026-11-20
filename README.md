# 中文 AI 短视频 Skill

把 AI 资讯搜索、选题、口播脚本、真实页面素材、录屏、中文配音、字幕、剪辑、封面和发布文案连成一条工作流，由 Codex 调度本地工具完成，不需要 Easel 工作台。

这是供 Codex 使用的技能集合，不是无人值守的视频生成服务。热点核查、文案编辑、素材选择和最终审片由 Codex 完成；Python、Playwright、FFmpeg 和本地 TTS 负责执行。新闻真假、操作结果和成片质量仍需实际核验，不承诺爆款。

## 包含什么

| 技能 | 用途 |
| --- | --- |
| [free-ai-video](skills/free-ai-video/SKILL.md) | 总入口：新闻搜索核查、脚本、真实录屏/截图、混剪、配音、字幕、竖屏合成、封面和发布文案 |
| [ai-content-ops](skills/ai-content-ops/SKILL.md) | 选题与口播策划、账号偏好、内容台账、排期和真实数据复盘 |
| [local-media-studio](skills/local-media-studio/SKILL.md) | 本地视频/音频/图片处理、字幕转换、ASR、横转竖、节拍混剪等按需工具 |

三个目录需要保持同级。主技能通过相对路径复用配套技能，共用研究、项目和配音时间轴，不需要启动额外网页服务。

这一版保留了实际迭代中的制作要求：中文口语表达、文案与素材逐段匹配、连贯镜头、教程优先真实中文操作页面；国内模型优先国内官网及人民币价格，海外模型保留官方原币种。每次成片交付附抖音标题、描述和恰好五个相关话题标签。画面不额外叠加来源标牌，素材来源和处理记录保存在项目内；使用素材仍须满足适用授权条件。

## 本次更新（2026-11-17）

同步后续视频制作中积累的写作、镜头和教程要求，并加入可按需读取的完整视频案例分析：

- **整段口播与收尾**：沿着同一个用途解释，保留已经认可的段落；项目介绍优先讲清身份和作用，再展示例子、教学，最后回到项目作用。公开视频不默认承诺另发配套资料。
- **真实素材与节奏**：固定截图默认保持取景不动；必要操作后停在结果上，切镜跟随解释。录屏检查实际清晰度和灰边，优先 1080p 以上原素材；界面变化时同步检查个人信息遮挡位置。
- **完整案例参考**：[指定抖音账号的首轮 5 条观察](skills/free-ai-video/references/douyin-wanan-cases.md)、[新增 20 条高互动样本](skills/free-ai-video/references/douyin-high20.md)、[硬件与桌宠同类案例](skills/free-ai-video/references/gadget-spoken-cases.md)。保留观察日期、覆盖范围及原片链接，区分互动快照、自动转写和实际画面观察。

本次更新以技能指令与编辑参考为主。三个技能继续共用原有项目和执行工具，Ming 环境按下文配置。

## 安装

需要 Git、Python（建议 3.11）、FFmpeg/ffprobe、中文字体，以及能联网检索和执行本地命令的 Codex。浏览器素材使用 Playwright Chromium；Windows 窗口录屏使用 Windows 本地捕获能力。

在 Windows PowerShell 中，将三个技能复制到 Codex 的技能目录。已有同名技能时先备份，再按需要更新；自定义了 CODEX_HOME 的环境应使用对应的 skills 目录。

```powershell
git clone https://github.com/TouHouQing/video-skill.git
cd video-skill
$videoSkillsRoot = Join-Path $env:USERPROFILE '.codex/skills'
New-Item -ItemType Directory -Path $videoSkillsRoot -Force | Out-Null
Copy-Item -Path './skills/*' -Destination $videoSkillsRoot -Recurse
```

打开新会话让 Codex 识别技能。以下命令从已安装的 `free-ai-video` 目录运行；始终使用同一个 Python 环境：

```powershell
python scripts/bootstrap.py
python scripts/factory.py doctor
python scripts/factory.py ops -- --help
python scripts/factory.py media doctor
```

`bootstrap.py` 安装缺少的基础 Python 库和浏览器，在技能的 `.runtime/` 中保存本机配置；它不安装 Ming、Whisper 模型，也不保证完整的 FFmpeg 工具链已就绪。媒体工具还需要 `ffprobe`，应安装包含 `ffmpeg` 和 `ffprobe` 的完整 FFmpeg 发行版并加入 PATH。可按当前网络情况通过 `PIP_INDEX_URL` 临时选择镜像源。

## 本地配音

已附带 Ming C「二次元细声」的原创合成参考音频及其文本、哈希和来源记录。保留选定音色时必须使用实际参考音频，不能只重写声线提示词。

**Ming 的模型权重和推理环境不在仓库里，需要单独配置。** 跨平台适配器使用 `inclusionAI/Ming-3.0-tts-0.5B`，Windows 经 WSL 调用 Linux CUDA 环境；Apple Silicon 优先使用已经验证的 `mlx-community/Ming-3.0-tts-0.5B-8bit` 与 `mlx-audio` 本地路径。安装所需目录、版本下限、参考音频校验和限制见 [本地配音说明](skills/free-ai-video/references/local-tts.md)。基础 doctor 通过不代表 Ming 已可用；实际配音还需单独验证。

Ming 失败会停止，不会悄悄更换声线。VoxCPM2 只是后备方向，未打包成自动可用后端。其他已有模式（Edge 在线语音、Windows 本地 SAPI）必须显式选择；Edge 需要网络，不是本地模型。

流程不接入付费生成 API 或云渲染；现有 Codex 使用额度、设备、电力和下载流量不包含在“零额外 API 费用”中。

## 使用

在 Codex 中调用：

```text
用 $free-ai-video 搜索最近 72 小时值得做的 AI 新闻，核查官方信息，
选一个适合中文用户的题材。先给自然口语脚本、素材计划和分镜草稿，
等我同意再生成视频。
```

```text
用 $free-ai-video 直接制作一条中文竖屏 AI 教程。
优先真实中文操作页面截图或录屏，素材要跟口播对应。
交付视频、封面、字幕、抖音标题、描述和五个相关标签。
```

正常项目链为 `research.json → project.json → 素材/录屏 → 配音与剪辑时间轴 → MP4/封面/SRT/发布文案`。账号偏好和台账保存在工作区，渲染结果标记为待审片；生成文案不等于授权登录或发布。字段及 CLI 参数见技能参考文件和 `python scripts/factory.py --help`。

## 仓库范围与第三方来源

仓库只包含技能指令、源码、参考文档和必要的原创声线样本。不包含账号档案、历史视频、用户截图、Cookie、密钥、模型权重、Python 安装包或本机运行配置。这些内容也由 `.gitignore` 排除。

部分媒体工具和 RSS 工具迁自 [ZJU-REAL/Easel](https://github.com/ZJU-REAL/Easel)，已保留 Apache-2.0 许可证、NOTICE，以及适用的迁移和修改记录：

- [free-ai-video 第三方记录](skills/free-ai-video/third_party/Easel/NOTICE)
- [ai-content-ops 第三方记录](skills/ai-content-ops/third_party/Easel/NOTICE)
- [local-media-studio 第三方记录](skills/local-media-studio/third_party/Easel/NOTICE)

第三方代码、模型、字体和素材遵循各自许可证；第三方许可证不自动扩展为本仓库全部原创内容的统一授权。
