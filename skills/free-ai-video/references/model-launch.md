# Model launch: make the model's value the story

Use for releases of models, model variants and substantial upgrades. The viewer should understand what changed, whether it matters for their work, what it costs and what tradeoff they would accept. A research release without a commercial offering can explain its scientific contribution and explicitly state that pricing is inapplicable; do not force a shopping comparison onto unrelated stories.

## Research before picking the hook

Build a compact source sheet, then choose an angle. Look for:

- **Capability and change:** concrete tasks, improvement over the predecessor, useful outputs and meaningful limits. A large context window or parameter count is not automatically an improvement or a unique advantage. Translate a feature into a task only when the source supports that connection.
- **Access and price:** official provider, model/version, region, currency, per-token unit, input/output/cache classes, service tier, context thresholds and the date checked. Distinguish web membership, coding subscriptions and API usage; distinguish free trial access, open weights and free inference. If pricing is unavailable, state exactly what was searched and what remains unknown.
- **Competition:** choose alternatives the audience might actually use. Include a relevant capability rival and consider a same-price or lower-price alternative, rather than selecting only an expensive flagship. Compare the same task and metric; don't average unrelated leaderboards. An untested alternative can be listed on price without inventing its task performance.
- **Evidence strength:** direct observation, independent evaluation, vendor evaluation, vendor demo, or unverified discussion. Preserve harness, reasoning effort, tool access, pass@k, date and version. A vendor's compilation of results from different harnesses is a published comparison, not a controlled head-to-head test. A 0.7 percentage-point gap is not 0.7% overall inferiority.

Compare prices under explicitly matched assumptions. Standard uncached input cannot be compared with a competitor's cache hit, batch or promotional rate. Specify cache/time-of-day and long-context modifiers where relevant. Per-token price ratios are not task-cost ratios: retries, reasoning output, cache reuse and successful completion can change the bill. Currency conversion is a separate dated assumption, not a silent substitution for a domestic rate card.

## Audience region and native prices

For this installation's Chinese customers, begin with official domestic sites, Chinese announcements, domestic access instructions and RMB rate cards for Chinese providers. Use the actual domestic SKU/plan; a translated international page is not automatically a domestic offer. If the primary Chinese page is missing or redirects to English, retain the accessible official source and record that fallback rather than inventing a Chinese page.

Foreign providers such as Claude retain the currency and region of their official offer, commonly USD. It is acceptable to show Kimi's RMB and Claude's USD prices in the same report, provided each row/scene identifies its currency, model, tier, unit and check date. They need not be forcibly converted. Do not infer “same price”, “half the price” or an affordability ranking from their raw numbers. For a necessary cross-currency comparison, cite the conversion date/source and mark the result as an estimate, while keeping the native price visible. Do not add exchange-rate research when the story does not require conversion.

When revising a price locale, update the entire dependency chain: sources, spoken prices, comparisons, labels, title, cover, publishing copy and research conclusions. Replacing a USD screenshot with an RMB screenshot while retaining a USD-based ratio is incorrect. Compare a domestic model against its previous domestic version when that provides a clearer supported price-change hook. Record actual input/output changes separately; do not claim total task savings from unit-rate reductions.

## Choose one central question

Useful angles include capability gained for a lower unit price, a workflow that now becomes feasible, a speed/cost tradeoff, a strong result paired with an important weakness, or a decision between two versions. Select the strongest verified angle for this audience; do not cram every dimension into the title.

Use [attention and payoff](attention-and-payoff.md) to compare different angles before polishing wording. A stronger but relevant comparison is welcome when separately verified, rather than repeatedly rephrasing a weak lead. Keep the price baseline and the task/performance baseline explicit; a unit-price advantage plus one vendor benchmark cannot become an overall replacement claim. Plan where the opening is proved and what further understanding the body adds.

Write several candidate hooks internally and select one by its relevance, evidence, specificity and ability to be paid off within the video. Consider event-led news, a verified surprising change, a useful result or a viewer decision; do not force every video into “值得换吗”. The hook should identify the model/event and quickly establish a stake. A confirmed time/event anchor can be effective: “10月24日程序员节，X发布了Y；模型升级，国内API单价还降了三成多” is usable only when each claim is verified. Show the actual announcement/date and matching pricing evidence. A bare announcement without the meaningful change or unsupported amazement provides little payoff.

Verify announcement time separately from an article update, service rollout or future open-weight release. Use absolute dates for an earlier event; say “今天/刚刚/就在今天” only when publication timing supports it. Use “程序员节” or another seasonal anchor only for a genuine connection, not as a mandatory recurring hook. Avoid unsupported “吊打 / 最强 / 全面替代 / 全球最低价 / 任务成本减半”. A question mark does not excuse a misleading premise.

Research those dimensions, then choose what this particular story needs. Do not automatically turn capability, price, benchmarks and limits into separate spoken chapters or a repeated question-and-answer tour. A price change may lead into its task implications; a useful demonstration may lead into its relevant comparison. Keep benchmark detail selective and put the full matrix in the research/publishing material.

Use [spoken news writing](spoken-news-writing.md) to write a continuous draft, review specific weak passages and check facts again before TTS. Natural clause-length variation matters more than making every sentence short. A selected anime timbre does not determine the narrator's vocabulary or require playful particles.

Apply [editorial continuity](editorial-continuity.md): lead with a consequential audience question, let visible source numbers carry detail, and explain what changes the viewer's choice. Read the narration aloud or use an available audio review; remove report-style noun chains, repeated caveats and generic engagement bait. Retain the qualification that changes the meaning at the relevant claim. Put the full configuration/currency matrix in source notes rather than reciting it repeatedly.

## Make footage perform a specific job

Apply this user's source-led preference from [recording-and-editing.md](recording-and-editing.md#source-led-news). The main performance/price evidence should usually be the actual source chart or selected pricing page, inspected through recordings and close excerpts. The data-animation layouts below remain available as brief supporting explanations or when the user requests a graphics-led treatment; do not let them take over a source-led news edit.

| Editorial job | Good material | Review criterion |
| --- | --- | --- |
| Show capability | Short actual task execution or attributed official workflow/result | Subject is visible; task, result and origin are clear; no imaginary self-test |
| Compare capability | Original animated bars/table plus close source excerpt | Full versions and units, consistent axis, configuration differences visible |
| Explain price | Input/output comparison with region, currency, tier and unit | Rate class matches; important conditions remain on screen |
| Explain workflow | Original process animation or a real sequence of actions | A diagram is labelled as an explanation, not a vendor UI or recorded result |
| Explain limits | Relevant failed/weak benchmark or an access/cost constraint | The weakness changes a viewer decision, rather than adding empty hedging |

Build original data graphics from verified values. Bar charts start at zero unless a justified alternative is clearly marked; avoid visually magnifying tiny gaps with truncated axes. Keep labels readable in portrait playback. Use actual source receipts briefly and crop to the relevant evidence instead of asking the viewer to read an entire English announcement. An impressive 3D/game example can illustrate coding capability; it should not dominate an API value comparison simply because it is easy to record.

For source demos, review whether downloaded/premade assets, external tools or multiple attempts were part of the workflow when the source discloses that information. Describe the resulting workflow accurately. General B-roll supplies context only; it cannot substantiate model performance or price.

## Editorial brief and final review

Add `editorial_brief` to research.json: audience, central question, thesis, selected hook, supporting claims, capability evidence, pricing assumptions/check date, competitors and why selected, meaningful limitation, takeaway and scene-to-claim/media map. This is reusable reasoning, not a numeric viral-score form. Keep full data rows with source URLs outside the spoken script.

Before production, read the script without the footage. Does it still identify a useful model story and answer the hook? Then review the footage without audio: are the right comparisons/results actually legible? Revise either side if the claim and picture diverge. Check that the title/cover express the same claim as the narration and that a narrow benchmark or unit-price advantage has not become a universal promise.

Close with a relevant real task or decision. For growth and lead generation, build a repeatable series around a clearly defined audience and its jobs; use actual retention/follow/inquiry feedback when available. Do not invent platform results or promise viral traffic.
