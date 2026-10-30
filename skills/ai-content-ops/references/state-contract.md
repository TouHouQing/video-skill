# 本地状态格式

```text
python scripts/content_ops.py init --workspace <workspace>/work/ai-channel
python scripts/content_ops.py context --workspace <workspace>/work/ai-channel
python scripts/content_ops.py brief --workspace <workspace>/work/ai-channel --stage draft --topic-id <id>
python scripts/content_ops.py record --workspace <workspace>/work/ai-channel --kind topics --input <rows.json>
python scripts/content_ops.py analyze --workspace <workspace>/work/ai-channel --output <review.json>
```

`record` 接受一条对象或对象数组，按 `id` 更新；历史旧版本写入 `history.jsonl`。整批先校验再写入，原子替换文件。不同 Codex 会话不应同时写同一个台账。

日常先用 `brief`：按 discover/draft/produce/review 只返回相关台账项、选中题材和有限学习，默认最多 8 条；全量数据继续用 context/analyze。brief 不会把历史播放数据都塞进写稿上下文，也不会重新定义账号偏好。

`attach --workspace <目录> --topic-id <id> --project <json> --report <report.json>` 记录实际成功编码的本地作品；正常由生产入口自动调用。仅接受 completed、verification.passed 且视频存在的报告，追加 artifacts 并标为 produced_pending_review；已有 published/cancelled 状态保留。它既不宣布审片通过，也不写入计划的播放数或执行发布。

| kind / 文件 | 每行必需 | 常用附加字段 |
|---|---|---|
| `topics` / topics.json | id, title, audience_problem, sources | occurred_at, heat_signals, angle, evidence_gaps, footage_plan, project_path, status |
| `calendar` / calendar.json | id, topic_id, planned_at, status | platform, project_path, deliverable_path, dependencies |
| `performance` / performance.json | id, post_id, platform, observed_at, window_hours | published_at, url, views, impressions, completions, follows, qualified_leads, likes, saves, shares |
| `learning` / learning.json | id, observation, evidence, recorded_at | hypothesis, conditions, next_test |

时间戳带时区。window_hours 表示同生命周期观察窗口（例如 24、72）；不是把 10 小时与 24 小时快照混比。`sources` 和 `evidence` 是非空列表。未知数值省略或 null；提供时必须为非负有限数，计数为整数。completions 不可大于 views。精确粉丝归因不明时留空。

`profile.json` 保存 identity、audience、platforms、goals、preferences、content_pillars，直接在本地编辑；初始化不会读平台账号、API 密钥或 Easel 配置。profile 只保存已知事实和标注为 assumption 的假设。默认偏好反映本会话已选设置，可以由用户调整。

`analyze` 的 rates 是分母已知记录的分子之和 / 对应分母之和，返回计入数和缺失数；中位数按内容计算。不同平台与 window_hours 分组，不把重复快照累加。数据量很少时报告描述统计，不给显著性或爆款概率。
