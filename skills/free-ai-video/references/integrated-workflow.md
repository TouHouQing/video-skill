# 按任务复用内容策划和媒体能力

`free-ai-video` 是总入口，`ai-content-ops` 提供编辑方法和账号状态，`local-media-studio` 提供确定性的额外媒体处理。保持一份研究、一个项目、一条配音时间轴；不要为用了 Easel 而再建一条出片链。

## 复用决策

| 当前任务 | 优先路径 | 何时用迁入能力 |
|---|---|---|
| 找 AI 新闻 | 主技能 collect + 当前网页搜索 + 官方核查 | 内容运营的选题/差异角度方法；热榜为可选观察 |
| 选开头、写稿 | 用 [观看理由与兑现](attention-and-payoff.md) 筛角度，再按 [中文新闻口播](spoken-news-writing.md) 成文、编辑、拆分镜 | topic-and-script 负责运营侧选题；共用角度、兑现与语言规范，不另套 Hook 模板 |
| 日常剪切、变速、近景、字幕 | 主编辑器 shots 与实测配音时长 | 不额外先剪一遍；中间文件只有确实要复用时才做 |
| 一份素材需独立交付/多次使用 | 媒体工具进行必要加工 | tracked run 保存输入/参数/输出，精确命中才复用 |
| 外语采访或长演示理解/选段 | 实际看片与文字转录 | ASR 用于找段和漏字检查；字幕工具供逐行翻译和双语合并 |
| 音轨响度、降噪、BGM 闪避 | 默认配音与主编辑器的混音 | 只有提供原声/音乐或提出专门音频需求时才用音频工具 |
| 音乐混剪、绿幕、波形 | 用户确实要该效果 | 再调用 beats/chroma/visualizer，不插进普通新闻默认链 |
| 账号定位、内容矩阵、排期 | 既有档案与当前产能 | 用户要持续规划时展开运营参考；单条视频不生成整套策略 |
| 复盘与下一轮 | 用户提供/授权获取的真实数据 | ops analyze 分平台/窗口比较，有依据的观察写入 learning |

源视频原声目前由主编辑器丢弃，叠加的是旁白和其支持的音乐。不要因为媒体工具能混音就宣称主时间轴已经支持原声采访混合；此类具体需求需单独安排音轨衔接并实际验证。

## 每阶段传什么

1. **发现**：`ops brief --stage discover` 读取档案和少量学习；候选包括发生时间、受众问题、实际热度信号、原始来源和可用证据。collect 的来源软上限避免 HN 分数挤掉国内媒体，source_coverage 显示覆盖限制。无日期线索单列，不用无关内容补位。
2. **写稿**：按已选 topic_id 读取 brief draft；确定中心判断，按 [中文新闻口播](spoken-news-writing.md) 写连续正文并完成文本复核，再拆进同一份 project.json。稿件与短评审留在任务目录；research.json 保留事实及取舍，用 evidence_map 指明终稿每个场景的来源、素材、观看重点与证据限制。
3. **制作**：project 声明 channel_dir/topic_id；项目字段优先，未填设置从账号档案读取。preflight produce 检查文件和衔接；主编辑器按实际配音分配时长。特殊加工才走媒体工具，原片与处理记录都保留。
4. **审片与反馈**：成功编码自动回写路径和 produced_pending_review，Codex 再检查转场、文案、声音和画面。发布后才登记真实发布时间/平台数据，不能用编码成功替代内容审核或发布成功。

## 成片交付同时给抖音文案

本账号要求每次交付成片时，一并提供可直接粘贴的抖音标题、描述，以及恰好5个话题标签。最终回复里直接给出这些文字，不能只给成片链接或把文案藏在附件中；同份内容保存为输出目录的`抖音发布文案.md`。用户只补要已有视频文案时，更新文案文件和交付偏好即可，无需重做视频。

标题先说本片最具体的收益、变化或操作目标，保留自然口语；描述接上标题，说明观众能学到什么，保留会改变结论的资格、金额或使用限制。沿用用户已认可的措辞，不把描述写成脚本结构表，不加入素材引用说明，不承诺爆款或保证所有人可领取。

5个标签从当前题材的产品名、用途和抖音常用相关话题里选择；用户举的`#codex`、`#gpt`是可选例子，不必每条强塞同一套。不要为了蹭标签把视频没讲的产品或用途写进去。要求热门标签时查看当前平台公开搜索/话题线索；没有实际榜单或统计数据，不声称“今日热榜前五”，不编造播放量和热度。标题、描述、标签三者应指向同一条视频的真实内容。生成文案不等于执行发布，发布状态仍按实际动作记录。

## 命令

相对路径以主技能目录为基准；项目与素材参数使用绝对路径。Python 选择见 .runtime/runtime.json。

```text
python scripts/factory.py ops brief --workspace <工作区>/work/ai-channel --stage discover
python scripts/factory.py ops brief --workspace <工作区>/work/ai-channel --stage draft --topic-id <id>
python scripts/factory.py preflight --project <job>/project.json --stage draft --output <job>/preflight-draft.json
python scripts/factory.py preflight --project <job>/project.json --stage produce --output <job>/preflight.json
python scripts/factory.py produce --project <job>/project.json --output <交付目录>
```

需要读取策划规则时从 [内容运营](../../ai-content-ops/SKILL.md) 进入；额外处理从 [媒体工具](../../local-media-studio/SKILL.md) 进入。按任务读取其参考，不默认加载所有资料。普通生产不需要全量 context。

## 采集与缓存

`collect --feeds <JSON>` 替换 RSS 列表（name/url 对象），仍采集公开 GitHub/HN；`rss fetch --feeds <文本文件>` 是每行一个 URL 的自定义订阅摘要。二者按需选用，避免重复抓相同订阅。collect 的 hours 为小时，rss 的 since 为天。

可选 hotlists 为 weibo/douyin/zhihu/bilibili。第三方端点失败要保留错误并做当前网页搜索；抓取时间不是新闻发布日，平台搜索链接只是导航，不是原始事实证据。材料和研究的缓存不能替代对当前价格/版本/日期的重新核查。

主编辑器缓存 Ming 分场景配音；未改旁白/声线无需重合成。新增处理缓存按输入、参数、代码和输出哈希复用；详见 [派生素材记录](../../local-media-studio/references/processing-reuse.md)。更新新闻研究会改变显式 source capture 的缓存键。新模式不自动抓取根本没进入时间轴的全套截图。

## 维护边界

Easel vendor 文件只做必要兼容修复，包装层负责路由、缓存和状态衔接；许可证与本地哈希保存在 third_party/Easel。升级时对照固定版本，不直接覆盖本地修复。付费生成/配音、Workbench、账号发布适配器及当前任务无关模板不接入默认链。迁移清单是追踪记录，不作为每次制作都要加载的操作手册。
