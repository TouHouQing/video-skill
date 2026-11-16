# Recording and automatic editing

## Source-led news

The user prefers source material to occupy most of the video. Start by collecting enough relevant source states for each paragraph: official model pages, the actual benchmark figure and notes, API pricing pages with the correct plan selected, and short demonstrations that show the model's advertised workflows. Then write the edit; do not finish a largely graphical edit and add one small recording as decoration.

For this installation's `visual_style: source_led` preset, aim for at least 90% of the actual timeline showing source screenshots/recordings/demo footage and at least 65% showing real recordings. The editor enforces these preset values and exports `visual-mix.json`. `requirements.source_material_min_ratio`, `recording_min_ratio` and `max_consecutive_motion_seconds` override those defaults; `min_distinct_source_assets` is optional only when explicitly useful. Do not add sources, insert demos or cut away mid-idea to satisfy a source-count goal. These are this user's production defaults, not a universal formula for every video.

Use `media.role: source_page` for authentic source screenshots, `source_recording` for browsing an actual public source, and `vendor_demo` for attributed native playback excerpts. Keep original URLs and hashes; recordings require the normal completed capture manifest. Set `source_asset_id` to the original URL/figure/demo identifier when several crops or recordings come from that same original. The diversity check groups those views; changing filenames or recording the same unchanged page again is not more source variety. Source pages otherwise group by URL. Generated visuals, custom result viewers and unrelated stock do not satisfy this coverage target.

Record useful operations: switch the real API/plan tab, scroll to the relevant model, reveal a pricing row, inspect a chart/footnote, or play the published example. Skip loading, setup and dead scrolling in the edit. Browsing documentation is source review, not a demonstration that the model itself completed the advertised task. Preserve that distinction in the labels.

Keep the source readable on a phone. Capture a suitable viewport, reframe to the relevant part, and retain enough page context to identify its origin. Browser zoom, source-image enlargement and postproduction crops may change presentation but must not change source text, values or controls; log presentation adjustments. A large original figure can be opened at its own original URL and enlarged for a recorded inspection. Do not replace inaccessible pages with a lookalike vendor page.

For this channel, hold screenshots and reading states still by default: use identical `camera.start` and `camera.end` rectangles. The user explicitly rejected continuously scrolling, drifting or zooming evidence that cannot be read. Show a necessary scroll or click until the next useful state appears, then hold it; cut when the spoken point changes. Preserve real motion in a model demonstration when that motion is the evidence.

Prefer 1080p or higher original tutorial footage, and inspect the recorded pixels as well as the container dimensions. A nominally large recording may contain a downscaled page and padding. Set the browser viewport and capture size deliberately, check the first recording before collecting the rest, and re-record when key text is too small. Upscaling or sharpening a low-resolution source does not restore its missing detail.

For Chinese viewers, prefer an actual Chinese/domestic source when available, especially domestic model pricing and usage instructions. Keep foreign models' official native-currency evidence. Changing the target price locale also changes any dependent spoken comparison; see [native prices](model-launch.md#audience-region-and-native-prices). Capture an actual publication date for a date-led opening; an article's “updated” date alone does not prove its model launch date.

Use captions, pointer motion, region highlights, short callouts and occasional transitions over the actual material. Keep callouts to one or two lines and a small part of the screen, normally under one fifth, leaving the underlying evidence dominant. Avoid repeated large tables over different backgrounds, fake typing, or prolonged source stills with a token animation that merely recreate slides. Mix meaningful actions, source states and close results; a cut should advance the information rather than reset the same picture.

Before delivery, inspect recorded clips and the encoded edit rather than trusting screenshots alone. Report source-material seconds, recording seconds, distinct originals and any graphical-only duration. Also judge relevance, legibility and whether consecutive shots are visibly different; numerical coverage alone does not establish good editing.

Use [editorial continuity](editorial-continuity.md) to choose when a new source is actually needed. Stay on a useful page/result while the viewer understands a complete comparison. A purposeful reveal or inspection can carry a paragraph; repeated tiny up/down scrolls add no information. A dissolve cannot repair an unrelated change of subject.

## Tutorials for this Chinese-language channel

The user rejected the Pro-credits tutorial on2026-10-30 because almost all footage was English documentation. For this channel, tutorial steps must show actual product-interface screenshots or recordings: where to enter, which control to select, what confirmation appears, and where the result is checked. Document pages are research evidence and at most brief supporting material. Do not make another predominantly English-document walkthrough, even if its recording ratio passes or Chinese subtitles are added.

Prefer original captures of the real interface, with the Chinese locale when available. If access is unavailable, the user permits using authentic screenshots from other public tutorials. Inspect the original article and images, cross-check the depicted flow against current official instructions, and retain source URLs, creators and unmodified originals in project records. Use selected relevant interface excerpts for original Chinese explanation; do not copy another creator's complete video or script. Redact exposed personal account details and record crops/redactions. Keep balances, button labels, account tier and success state accurate.

For this channel, the user explicitly asked on2026-10-30 to remove all added citation explanations from the video and cover, then also requested removing visible creator watermarks from the screenshots. Do not add badges such as “引用实页截图”, publisher names, “非本次实领”, or source/author footers. Keep provenance in the media/project records instead of turning it into viewer-facing narration or publishing copy. In full-bleed shots set `label` to an empty string; check other callouts and cover text as well. Process visible creator watermarks on a working copy as requested, recording the actual edited regions and keeping the original. Account display names are identifiers rather than watermarks; obscure them when needed for a clean presentation, without inventing an account name. Retain product controls, actual amounts and the service's own interface branding. Removing labels does not authorize claiming that another person's account or result is our own; the tutorial can simply explain the visible steps without a personal-success claim.

Review account names, email addresses, machine identifiers and other exposed personal details in every used interface state. Track redactions across modal changes and cuts so a mask does not cover a button or status message after the interface moves. Preserve originals and processing records outside the public delivery.

Choose Chinese interface examples first. If an essential actual product screen is only available in English, Chinese action labels and arrows can explain the visible controls while retaining their true text and location; that is different from filling the video with English paragraphs. Show the page/control legibly on a phone, keep annotations tied to the spoken action and give viewers time to find it. Do not invent a Chinese vendor UI by reconstructing or translating its pixels.

Check material sufficiency before rendering: every core action must have its corresponding real interface state. If screenshots are the honest available material, use them and record their type accurately; panning a still or recording a third-party article does not turn it into an original live operation. The user's acceptance of screenshots overrides the old65% recording target for such a tutorial; set the project target accordingly instead of padding it with documentation recordings. If core interface states remain unavailable after reasonable searching, report the specific gap and deliver the acquired material/storyboard; do not render the rejected document-based substitute.

## Actual browser operations

Use an isolated local browser on a public page or a user-owned local demo. Inspect the current DOM first so selectors match actual controls. Do not build a fake UI and present it as the target product. A local viewer of genuinely generated output must be labelled as such, distinct from an application's native UI.

`recording.json` example:

```json
{
  "url":"http://127.0.0.1:8000",
  "label":"自有测试工具的真实操作",
  "viewport":{"width":1080,"height":1400},
  "lead_in":0.8,
  "tail":1,
  "steps":[
    {"action":"type","selector":"#input","text":"示例内容","delay_ms":70,"pause":0.4},
    {"action":"click","selector":"#run","pause":0.5},
    {"action":"assert_text","selector":"#result","text":"实际期望结果","pause":1}
  ]
}
```

Supported actions: `click`, `fill`, `type`, `press`, `hover`, `scroll`, `wait`, `assert_text`, `assert_visible`, `goto`. Use `selector` for target controls; `press` takes `key`; `scroll` takes `x`/`y`; `wait` takes seconds (0–30). Each action can set a short post-action `pause`. Do not put account passwords/API secrets in a recording plan. Recording is not authorization to publish, message, purchase or delete anything.

```text
python scripts/factory.py record --plan <recording.json> --output <clip.mp4>
python scripts/factory.py autocut --manifest <clip.recording.json> --output <rough-cut.json>
```

The recording saves actual browser video plus action screenshots, before/after HTML, a Playwright trace, successful assertions and SHA-256 in `clip.recording.json`. Failures leave a failed manifest; they do not produce a fake successful demonstration. The rough-cut plan selects actual action/result windows, removes idle gaps and suggests highlights/camera focus from actual control positions. Its wallclock offsets are approximate. Review cuts around long/asynchronous operations; keep the real resulting state, even if that requires a later result shot.

For native Windows apps, `record-window --title <exact-window-title> --seconds 15 --output <clip.mp4>` captures the named window and cursor through local FFmpeg/GDI. It records the window; it does not drive the desktop application. Use available host UI automation for actual interactions, or use browser/CLI demonstrations when they better expose a genuine result. Whole-desktop capture is not the default. Verify named-window recording on the actual target app before relying on it.

`record-native --title <exact-window-title> --seconds 15 --output <clip.mp4>` uses Windows PrintWindow and records the observed native application, including occluded content when the application supports it. This optional path needs pywin32. It records only one uniquely matched window. It does not grant permission to interact with accounts or unrelated documents. Keep action/provenance evidence when driving the application through an available supported interface. Tag actual target-app footage as `media.role: target_app`, an executed CLI as `terminal_execution`, supporting viewers as `result_viewer`, and licensed contextual footage as `b_roll`.

## Learn from source editing without inventing capabilities

For the specified Douyin account and frame-timed examples, read [AI科技推送 cases](douyin-wanan-cases.md). Plan the visible action/evidence, where the viewer should look, and why a highlight or layer starts and stops in the existing editing record. A still is useful when its evidence remains readable; source playback and screenshots are different material types. Keep a continuous action until its result and use simultaneous views when a comparison needs both results present. Exact layer entrances, callout lines or two-video layouts may need a separately composed clip: current shot fields do not acquire those features merely because a reference describes them. Use documented fields, retain the source/processing lineage and inspect the encoded timing.

## Automatic assembly

Codex turns the rough cuts and verified result frames into a narrated storyboard, then writes shots in project.json. The renderer fits those shots to actual narration, trims/retimes media, smoothly reframes the selected region, adds highlights and transitions, and composites captions and optional original music. Source video audio is muted. Editing is deterministic once the storyboard is written; it does not call a separate model API for semantic editing.

Use a tool demo mainly for visible action/result, a motion segment only where it explains something, and licensed montage only where it adds context. Avoid long footage of installation terminals, decorative scrolling and screenshots too small to read. Editorial pace depends on the task: preserve enough time to understand an important click/result.

```text
python scripts/factory.py draft --project <project.json> --output <static-preview-dir>
python scripts/factory.py produce --project <project.json> --output <finished-video-dir>
```

The first command needs existing local media and produces only images/JSON. The second synthesizes narration and video and refuses pending-approval projects. Keep a requested draft gate intact. For a planned recording, provide an honest shot sketch rather than generating a topical video before approval.

## Montage assets

Use user-owned footage, original recordings/graphics, public-domain material or a license verified on the original source. Record attribution/license in `media[].rights`. No paid stock or generator is needed. `fetch-media --url <explicit-public-asset-url> --rights <rights.json> --output <local-file>` downloads a selected asset up to 100 MiB and records its hash/declaration. It does not discover licenses or grant rights. If no suitable footage is reusable, use original recordings and graphics and disclose that choice in the storyboard.

## Verification

Run `python -m unittest discover -s scripts -p "test_*.py"` for contract checks. `python scripts/smoke_edit.py --workdir <temporary-work-dir>` performs a real browser operation on a clearly labelled local test app, rough-cuts it, encodes all four visual modes, checks motion/decoding, verifies static-only previews and tests the full factory with local Chinese speech. Its clips are technical fixtures, not a product demonstration or a user-approved topical video. Named-window capture is a separate host/app check.

Implementation references: [Playwright video lifecycle](https://playwright.dev/python/docs/videos), [page actions](https://playwright.dev/python/docs/api/class-page). Playwright finalizes its video when the browser context closes; the recorder closes it before transcoding.
