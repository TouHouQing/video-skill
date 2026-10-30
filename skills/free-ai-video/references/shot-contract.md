# Shots and media

Use `visual_mode: screencast | motion | montage | hybrid`. Each scene retains its original narration/source fields and adds `shots`. Durations are positive editorial weights, scaled within that scene to its measured narration duration. `planned_duration` is used only by static draft previews. The renderer leaves the narration timeline intact across visual transitions.

Optional project `caption_replacements` maps spoken spelling to written spelling, for example `{"K三点一Pro":"K3.1 Pro","五点五":"5.5"}`. Replacements affect subtitle display after timing is calculated, not TTS input or audio caching. Use nonempty literal string keys and string values. Phrase timings remain approximate rather than forced alignment.

## Media inventory

```json
{
  "media": [
    {"id":"operation", "type":"video", "path":"recordings/demo.mp4",
     "recording_manifest":"recordings/demo.recording.json", "rights":{"kind":"original_capture"}},
    {"id":"owned-result", "type":"image", "path":"result.png", "rights":{"kind":"owned"}},
    {"id":"licensed-clip", "type":"video", "path":"licensed.mp4",
     "rights":{"kind":"licensed", "source_url":"https://publisher.example/clip",
               "license":"CC BY 4.0", "license_url":"https://creativecommons.org/licenses/by/4.0/"}}
  ]
}
```

Paths resolve relative to project.json. IDs are unique. Types are `video` or `image`. The first two items represent real local files you must create; the third illustrates license metadata, not a downloadable sample. Do not use an example URL as actual evidence.

Externally processed recordings can add `processing_manifest` while retaining the original `recording_manifest`. The media resolver verifies the hash chain through permitted picture-preserving transforms, rather than demanding that a trimmed file equal the raw recording hash. See [processing reuse](../../local-media-studio/references/processing-reuse.md). Keep the raw files and receipts; tampering/missing lineage fails production. Derived views of one recording default to one source_asset_id.

Rights kinds: `owned` (user/original creation), `original_capture` (completed recording manifest with matching SHA-256), `licensed` and `public_domain` (license, license URL and original source URL required), or `source_excerpt` (image only, a short authentic excerpt with source URL). Publicly viewable footage is not automatically reusable. The agent verifies permission and attribution; scripts preserve declarations, not legal conclusions.

## Shot examples

```json
{
  "shots": [
    {"id":"result-closeup", "type":"video", "media_id":"operation", "duration":3,
     "source_in":2.4, "source_out":7.2, "speed":"auto", "fit":"contain",
     "camera":{"start":[0,0,1,1], "end":[0.15,0.12,0.65,0.75]},
     "highlights":[{"rect":[0.2,0.4,0.5,0.15], "start":0.3, "end":0.85,"label":"真实结果"}],
     "transition":"cut", "label":"实际操作"},
    {"id":"explain-flow", "type":"motion", "duration":2,
     "motion":{"layout":"flow", "nodes":["输入文件","本地转换","检查结果"]},
     "transition":"dissolve"},
    {"id":"result-detail", "type":"image", "media_id":"owned-result", "duration":2,
     "camera":{"start":[0,0,1,1], "end":[0.04,0.04,0.92,0.92]}, "transition":"wipe"}
  ]
}
```

- IDs use 1–80 ASCII letters, digits, underscores or hyphens and are unique across scenes.
- `source_in` / `source_out` are seconds in the original clip. Omitted source_out selects the clip's end. `speed: auto` fits the selected range to its allocated narration time; a numeric speed keeps that rate and cuts surplus source footage. Rates outside 0.25–4x and footage shorter than its allocation are errors. The editor never silently loops or freezes a supposedly genuine operation.
- Frame-rate conversion may repeat at most one output frame at a clip boundary to round narration time to whole frames; this limit is recorded in edit-plan.json. It is not a fallback for missing footage.
- Camera start/end and highlight rect are normalized `[x,y,width,height]` in the original media. They must stay within its bounds. Camera motion interpolates smoothly. `fit: contain` retains the selected region; `cover` crops its edges to fill the shot area. Prefer contain when cropping could hide evidence.
- Highlights start/end are fractions of shot progress, not seconds. Labels should be short.
- Transitions are `cut`, `dissolve` or `wipe`; effects fit inside the incoming shot without shifting audio time. Video source audio is discarded; narration and optional original music form the soundtrack. This version does not mix quoted source audio.
- `presentation: full_bleed` fills the frame with footage or its blurred background, and uses small corner labels plus overlaid captions. It removes the large fixed scene-title/footer bands. Set `fit: cover` for contextual stock and `contain` when the full application frame needs to stay visible.
- Motion layouts: `kinetic` sequences large words/phrases, `flow` continuously moves signals between up to four nodes, `compare` moves a dividing line between two short labels. Use `words` or `nodes`; each entry must be nonempty. These are programmatic graphics, not photorealistic generated footage.
- For numerical comparisons use `bars` or `table` so values remain side by side after their entrance. Both need `title`, `unit`, optional short `note`, and 2–4 `rows` with full model `label`s. `bars` rows have finite nonnegative `value`, optional formatted `display`/`color`, and a positive `max_value` covering every value; the baseline is zero. `table` has 1–3 `columns` and each row has equally many nonempty string `cells`. Keep source/configuration conditions in the label/unit/note and verify them editorially; the numeric layout validates shape, not factual truth. Example: `{"layout":"bars","title":"任务成功率","unit":"% · 同一测试定义","max_value":100,"rows":[{"label":"模型 A","value":65.7,"display":"65.7%"},{"label":"模型 B","value":66.4,"display":"66.4%"}]}`. These example values are not research evidence.
- `headline` and `label` can override a shot's top overlay. Keep UI/action out of the top title and bottom caption bands.
- A full-bleed source shot may add a short `callout` string (one or two lines). Optional `callout_y` is its normalized top position, .08–.65, default .12. The callout annotates source material rather than replacing it; keep evidence unobstructed.
- `visual_style: source_led` uses the duration-based coverage preset documented in [source-led editing](recording-and-editing.md#source-led-news). `source_asset_id` on a media item groups different views of one original page, figure or demo. The renderer writes `visual-mix.json` for review.
- `motion` mode can omit shots; each scene derives a kinetic sequence from its headline/body. Other modes require explicit shots. Screencast needs video, montage needs two media shots, and hybrid needs two visual types.

`draft` uses existing media to export static shot frames, a contact sheet and a planned edit timeline. It does not record an operation, synthesize speech or encode a new video. When required footage does not yet exist, provide the shot list and labelled visual sketches; do not claim it is a recorded preview.
