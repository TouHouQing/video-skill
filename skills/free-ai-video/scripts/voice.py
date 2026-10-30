"""Free online TTS with a real offline Chinese fallback; exact scene audio lengths."""
from __future__ import annotations
import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import wave
from runtime import ROOT, emit, ffmpeg, run, save_json

RATE = 24000


def duration(path):
    with wave.open(str(path), 'rb') as f:
        return f.getnframes() / f.getframerate()


async def edge(text, path, voice, rate):
    import edge_tts
    async def execute():
        communicator = edge_tts.Communicate(text, voice=voice, rate=rate, connect_timeout=8, receive_timeout=12)
        await communicator.save(str(path))
    await asyncio.wait_for(execute(), timeout=28)


def one(text, output, provider, voice, speech_rate):
    path = Path(output)
    fingerprint = hashlib.sha256(json.dumps([text, provider, voice, speech_rate], ensure_ascii=False).encode()).hexdigest()
    metadata = path.with_suffix('.meta.json')
    if path.exists() and metadata.exists():
        previous = json.loads(metadata.read_text('utf-8'))
        if previous.get('fingerprint') == fingerprint and duration(path) > 0.1:
            return previous
    path.parent.mkdir(parents=True, exist_ok=True)
    if provider == 'edge':
        raw = path.with_suffix('.mp3')
        asyncio.run(edge(text, raw, voice, speech_rate))
        voice_name = voice
    else:
        if os.name != 'nt':
            raise RuntimeError('Local fallback needs an installed Chinese Windows voice; use Edge TTS on this platform or supply a local voice adapter.')
        text_path = path.with_suffix('.txt')
        text_path.write_text(text, 'utf-8')
        raw = path.with_suffix('.raw.wav')
        result = run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                      '-File', ROOT / 'scripts/sapi.ps1', '-TextFile', text_path.resolve(), '-OutputFile', raw.resolve()], timeout=60)
        voice_name = result.stdout.strip()
    run([ffmpeg(), '-y', '-hide_banner', '-loglevel', 'error', '-i', raw,
         '-ar', str(RATE), '-ac', '1', '-c:a', 'pcm_s16le', path], timeout=60)
    meta = {'fingerprint': fingerprint, 'provider': provider, 'voice': voice_name,
            'seconds': round(duration(path), 4), 'path': str(path), 'paid_api_cost': 0}
    save_json(metadata, meta)
    return meta


def chunks(text, maximum=25):
    # Phrase-level timing, explicitly not forced word alignment.
    parts = re.findall(r'[^，。！？；,!?;]+[，。！？；,!?;]?', text)
    out = []
    for part in parts:
        part = part.strip()
        while len(part) > maximum:
            split = part.rfind(' ', 8, maximum)
            split = split if split > 8 else maximum
            out.append(part[:split].strip())
            part = part[split:].strip()
        if part:
            out.append(part)
    # Keep short connectors with the clause they introduce instead of flashing
    # isolated captions such as “不过，” or “所以，” for half a second.
    grouped = []
    for part in out:
        if grouped and len(grouped[-1]) < 8 and len(grouped[-1]) + len(part) <= maximum:
            grouped[-1] += part
        else:
            grouped.append(part)
    if len(grouped) > 1 and len(grouped[-1]) < 8 and len(grouped[-2]) + len(grouped[-1]) <= maximum:
        grouped[-2:] = [grouped[-2] + grouped[-1]]
    return grouped or [text]


def timestamp(seconds, ass=False):
    ms = max(0, round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'


def prepare(project, folder):
    folder = Path(folder)
    preference_path = ROOT / '.runtime/voice-default.json'
    preference = json.loads(preference_path.read_text('utf-8')) if preference_path.exists() else {}
    mode = project.get('voice_mode', preference.get('voice_mode', 'auto'))
    provider = 'local' if mode == 'local' else 'edge'
    voice_name = project.get('voice', 'zh-CN-XiaoxiaoNeural')
    speech_rate = project.get('speech_rate', '+8%')
    fallback = None
    if mode == 'ming':
        from ming import prepare_records
        records = prepare_records(project, folder)
        provider = 'ming-local'
    while mode != 'ming':
        records = []
        try:
            for i, scene in enumerate(project['scenes']):
                emit('narration', scene=i+1, total=len(project['scenes']), provider=provider)
                records.append(one(scene['narration'], folder / f'voice-{i:02}.wav', provider, voice_name, speech_rate))
            break
        except Exception as error:
            if provider == 'edge' and mode == 'auto':
                fallback = str(error)[:500]
                emit('voice_fallback', provider='local', reason=fallback)
                provider = 'local'
                continue
            raise
    timeline, subtitles = [], []
    pcm = bytearray()
    cursor = 0.0
    padding = 0.30
    audio_rate = records[0].get('output_sample_rate', RATE)
    for i, (scene, record) in enumerate(zip(project['scenes'], records)):
        with wave.open(record['path'], 'rb') as audio:
            if (audio.getframerate(), audio.getnchannels(), audio.getsampwidth()) != (audio_rate, 1, 2):
                raise RuntimeError('Narration scenes must share a sample rate and use mono PCM16.')
            samples = audio.readframes(audio.getnframes())
        pcm.extend(samples)
        pcm.extend(b'\0\0' * round(padding * audio_rate))
        speech_seconds = record['seconds']
        length = speech_seconds + padding
        timeline.append({'index': i, 'start': cursor, 'duration': length, 'speech_seconds': speech_seconds})
        phrases = chunks(scene['narration'])
        weights = [max(1, len(re.sub(r'\s+', '', phrase))) for phrase in phrases]
        total = sum(weights)
        accumulated = 0
        for phrase, weight in zip(phrases, weights):
            start = cursor + speech_seconds * accumulated / total
            accumulated += weight
            end = cursor + speech_seconds * accumulated / total
            display = phrase
            for spoken, written in project.get('caption_replacements', {}).items():
                display = display.replace(spoken, written)
            subtitles.append({'start': start, 'end': end, 'text': display})
        cursor += length
    narration = folder / 'narration.wav'
    with wave.open(str(narration), 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(audio_rate)
        f.writeframes(pcm)
    return {'provider': provider, 'voice': records[0]['voice'], 'fallback_reason': fallback,
            'duration': cursor, 'timeline': timeline, 'subtitles': subtitles,
            'narration': str(narration), 'timing_method': 'phrase-duration-proportional', 'records': records}
