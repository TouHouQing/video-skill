# Local Ming narration

The user selected C / 二次元细声 on 2026-10-25. The original generated sample is packaged at `assets/voices/ming-anime-c.wav`; its exact transcript, SHA-256, voice-design description and seed are in `ming-anime-c.json`. It is an original synthesized adult female voice. Its direction is fine, light, soft, mildly breathy and anime-like. Preserve this selected timbre with task `TTS`, the waveform and its exact transcript. A repeated style prompt alone can change the speaker.

## Runtime and project fields

The adapter uses `inclusionAI/Ming-3.0-tts-0.5B`. The reference installation used WSL Ubuntu-22.04 with CUDA. Each machine must install its own runtime; the source repository does not include model weights, Python environments or `.runtime/ming.json`. `.runtime/voice-default.json` stores local preferences rather than a requirement for every other machine. The 0.5B name describes the backbone; do not claim the whole checkpoint is 0.5B or assume the tiny model is smaller.

The current runner requires the following layout inside the Linux user's home directory; `--runtime-root` validates this location rather than relocating it:

```text
~/.local/share/free-ai-video/ming3/
  src/                    Ming source, importable as ming_tts
  model/                  Complete model and tokenizer files, including model.safetensors
  venv/                   Isolated Python with CUDA PyTorch and Ming dependencies
  source-provenance.json  Actual downloaded source revision, including a commit field
```

Follow the [Ming model's installation instructions](https://huggingface.co/inclusionAI/Ming-3.0-tts-0.5B) for dependencies and weights. Record the actual downloaded source commit in `source-provenance.json`; do not invent a revision or claim an environment has been verified before inference. Create `free-ai-video/.runtime/ming.json` locally, replacing the Linux user, WSL distribution and hash with actual installed values:

```json
{
  "distribution": "Ubuntu-22.04",
  "python": "/home/<linux-user>/.local/share/free-ai-video/ming3/venv/bin/python",
  "root": "/home/<linux-user>/.local/share/free-ai-video/ming3",
  "model": "inclusionAI/Ming-3.0-tts-0.5B",
  "model_sha256": "<actual SHA-256 of model/model.safetensors>",
  "default_profile": "anime-c",
  "tempo": 1.0
}
```

On Linux, use the same home-relative layout with its local Python; `distribution` is only used by the Windows WSL launcher. The runner currently requires a CUDA GPU. Bootstrap and the general doctor do not install or certify Ming. Validate actual inference before promising narration on a new machine.

```json
{"voice_mode":"ming","voice_profile":"anime-c","voice_seed":330,"voice_tempo":1.0}
```

`scripts/voice.py` routes these projects through `scripts/ming.py`, which batches missing scenes in one model process. `ming_runner.py` uses local weights, HF offline flags and a Python outbound socket guard. It retains inference logs, raw 44.1kHz WAV files, per-scene seeds, reference/model hashes, generation time and the actual provider `ming-local`. It never labels Ming output as Edge. The selected reference is hash-checked and participates in cache invalidation. The audio assembly/mix preserves Ming's 44.1kHz sample rate.

Ming failure stops the job with the failed stage. It does not silently switch to SAPI, Edge or VoxCPM2. Explicit `auto`, `edge` and `local` modes retain their previous behavior. Installing or trying VoxCPM2 should follow the user's request.

## Delivery tuning and checks

Write spoken Chinese with short clauses, sentence stress and purposeful pauses. Expand dates, numbers and difficult foreign names into forms the narrator can speak; this runner skips the optional pynini normalizer. Avoid adding fillers to every sentence. Build a fixed voice identity from the selected reference rather than a long new role description for every scene.

The local BASIC slow/high experiment did not reliably obey pacing: a requested slow take was shorter than its anchor. Do not claim a control worked because it was requested. If needed, split sentences and add measured pauses; `voice_tempo` from 0.8–1.2 uses FFmpeg's pitch-preserving `atempo` and is recorded in audio metadata. Default 1.0 preserves the chosen sample's processing direction. Don't promise that any prompt removes all synthetic sound.

Check actual output, non-silence, full decode and missed words. An optional offline transcript checker such as `iic/SenseVoiceSmall-onnx` must be installed separately; no ASR weights are bundled. Automatic recognition can itself err and does not assess naturalness. Keep automatic checks and human listening judgments distinct. Subtitles remain proportional phrase timing unless a real alignment step is implemented.

The code/model downloads need network access during setup; installed Ming inference has no paid API calls. Computer/electricity and existing Codex usage are outside that statement. Reference and inference model licensing/provenance remain available in the original project and the installed Ming source.
