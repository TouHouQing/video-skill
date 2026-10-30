"""Animate original editorial scenes and genuine evidence locally into H.264 MP4."""
from __future__ import annotations
from functools import lru_cache
import math
import os
from pathlib import Path
import subprocess
import time
import wave
from PIL import Image, ImageDraw, ImageFont, ImageOps
from runtime import emit, ffmpeg, font_path, run

W, H = 720, 1280
INK = '#142D2A'
PAPER = '#F5F3EC'
MINT = '#D5FA73'


@lru_cache(maxsize=70)
def font(size, bold=False):
    return ImageFont.truetype(font_path(bold), size)


def wrap(text, width, face):
    lines = []
    for paragraph in str(text).split('\n'):
        current = ''
        for char in paragraph:
            if current and face.getlength(current + char) > width:
                lines.append(current.rstrip())
                current = char
            else:
                current += char
        lines.append(current.rstrip())
    return lines


def block(draw, xy, text, size, fill, width=624, bold=False, spacing=12, limit=None):
    face = font(size, bold)
    lines = wrap(text, width, face)
    if limit and len(lines) > limit:
        raise ValueError(f'Text overflows the {limit}-line layout: {text!r}')
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=face, fill=fill, stroke_width=0)
        y += size + spacing
    return y


def round_box(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius, fill, outline, width)


def screenshot_layer(path):
    original = Image.open(path).convert('RGB')
    # Fit the genuine source; never stretch text or fabricate a browser UI.
    fitted = ImageOps.contain(original, (590, 350), Image.Resampling.LANCZOS)
    card = Image.new('RGBA', (624, 406), '#FFFFFF')
    d = ImageDraw.Draw(card)
    d.rectangle((0, 0, 624, 38), fill='#E6EAE6')
    for i in range(3):
        d.ellipse((16+i*17, 14, 23+i*17, 21), fill='#A9B7AE')
    d.text((86, 7), '原始资料 · 截图 / 原文摘录', font=font(17), fill='#4C6156')
    card.paste(fitted, ((624-fitted.width)//2, 44 + (350-fitted.height)//2))
    return card


def prepare_scene(project, scene, index, asset=None):
    dark = scene.get('dark', scene.get('kind') in ('hook', 'close'))
    bg_color, text_color = (INK, PAPER) if dark else (PAPER, INK)
    muted = '#B8CCC0' if dark else '#5C6E63'
    accent = scene.get('accent', MINT)
    background = Image.new('RGB', (W, H), bg_color)
    d = ImageDraw.Draw(background)
    d.line((48, 112, 672, 112), fill='#4D6355' if dark else '#CFD7CB', width=1)
    d.text((48, 63), project.get('brand', 'AI 工具观察'), font=font(23, True), fill=text_color)
    d.text((586, 65), f'{index+1:02}/{len(project["scenes"]):02}', font=font(21), fill=muted)
    chapter = {'hook': '先看结果', 'evidence': '事实核验', 'steps': '实际做法', 'comparison': '成本拆解', 'close': '带走这张图'}[scene['kind']]
    d.text((48, 144), chapter, font=font(22), fill=accent if dark else '#526D19')
    headline = Image.new('RGBA', (W, 230), (0, 0, 0, 0))
    hd = ImageDraw.Draw(headline)
    block(hd, (48, 0), scene['headline'], 60, text_color, bold=True, spacing=14, limit=3)
    visual = None
    if asset:
        visual = screenshot_layer(asset)
    notes = []
    for i, line in enumerate(scene.get('body', [])[:3]):
        layer = Image.new('RGBA', (W, 66), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.ellipse((49, 18, 57, 26), fill=accent if dark else '#66842A')
        block(ld, (76, 1), line, 26, text_color, width=590, spacing=4, limit=2)
        notes.append(layer)
    # Keep safe space for platform controls and caption area.
    source_label = scene.get('asset_label') or ('原始来源见随附清单' if scene.get('source_ids') else '流程示意 · 本地制作')
    d.text((48, 1194), source_label[:34], font=font(18), fill=muted)
    return {'background': background, 'headline': headline, 'visual': visual, 'notes': notes,
            'dark': dark, 'accent': accent, 'ink': text_color, 'muted': muted}


def diagram(frame, scene, state, progress):
    d = ImageDraw.Draw(frame)
    steps = scene.get('steps') or scene.get('body') or ['公开资讯', '中文脚本', '本地成片']
    steps = steps[:5]
    top = 440
    gap = min(86, 360 // len(steps))
    active = min(len(steps)-1, int(progress * len(steps)))
    for i, label in enumerate(steps):
        y = top + i * gap
        fill = state['accent'] if i == active else ('#274239' if state['dark'] else '#E5EADB')
        color = INK if i == active else state['ink']
        round_box(d, (48, y, 672, y + gap - 12), 14, fill)
        d.text((68, y+12), f'{i+1:02}', font=font(22, True), fill=color)
        d.text((122, y+8), label, font=font(27, True), fill=color)
        if i < len(steps)-1:
            d.line((359, y+gap-10, 359, y+gap-3), fill=state['muted'], width=2)


def subtitle_layer(text):
    layer = Image.new('RGBA', (W, 142), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    lines = wrap(text, 580, font(31, True))
    if len(lines) > 2:
        raise ValueError(f'Caption is too long for safe layout: {text}')
    height = len(lines) * 45 + 26
    round_box(d, (42, 0, 678, height), 14, (11, 24, 20, 238))
    for i, line in enumerate(lines):
        width = font(31, True).getlength(line)
        d.text(((W-width)/2, 9+i*45), line, font=font(31, True), fill='#FFFFFF')
    return layer


def mix_audio(narration, output, seconds, music=True):
    with wave.open(str(narration), 'rb') as audio:
        rate = audio.getframerate()
    if not music:
        run([ffmpeg(), '-y', '-loglevel', 'error', '-i', narration,
             '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11', '-ar', str(rate), '-ac', '1', output])
        return
    import numpy as np
    t = np.arange(round(seconds * rate), dtype=np.float64) / rate
    frequencies = [130.8128, 103.8262, 174.6141, 116.5409]
    root = np.array(frequencies)[(t // 4).astype(int) % 4]
    envelope = np.minimum(1, t/1.5) * np.minimum(1, np.maximum(0, seconds-t)/2)
    # Original procedural ambience: quiet enough to sit below narration.
    sound = 0.009 * envelope * (np.sin(2*np.pi*root*t) + .35*np.sin(2*np.pi*root*1.5*t))
    samples = np.clip(sound * 32767, -32768, 32767).astype('<i2')
    bed = Path(output).with_name('original-music.wav')
    with wave.open(str(bed), 'wb') as f:
        f.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        f.writeframes(samples.tobytes())
    run([ffmpeg(), '-y', '-loglevel', 'error', '-i', narration, '-i', bed,
         '-filter_complex', '[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[v];[v][1:a]amix=inputs=2:normalize=0[a]',
         '-map', '[a]', '-ar', str(rate), '-ac', '1', output])


def render(project, voice, assets, output):
    out = Path(output)
    states = [prepare_scene(project, s, i, assets.get(i)) for i, s in enumerate(project['scenes'])]
    subtitles = [(s, subtitle_layer(s['text'])) for s in voice['subtitles']]
    fps = project.get('fps', 24)
    width, height = project.get('width', 1080), project.get('height', 1920)
    soundtrack = out / 'assets' / 'soundtrack.wav'
    mix_audio(voice['narration'], soundtrack, voice['duration'], project.get('music', True))
    video = out / 'final.mp4'
    log = out / 'assets' / 'render.log'
    command = [ffmpeg(), '-y', '-hide_banner', '-loglevel', 'warning', '-f', 'rawvideo', '-vcodec', 'rawvideo',
               '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps), '-i', 'pipe:0', '-i', str(soundtrack),
               '-vf', f'scale={width}:{height}:flags=lanczos', '-c:v', 'libx264', '-preset', 'veryfast',
               '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart',
               '-shortest', '-threads', str(min(6, os.cpu_count() or 2)), str(video)]
    options = {'stdin': subprocess.PIPE, 'stdout': subprocess.DEVNULL}
    if os.name == 'nt':
        options['creationflags'] = subprocess.CREATE_NO_WINDOW
    frame_total = math.ceil(voice['duration'] * fps)
    previous = None
    scene_index = 0
    subtitle_index = 0
    sample_frames = []
    started = time.monotonic()
    with log.open('wb') as errors:
        process = subprocess.Popen(command, stderr=errors, **options)
        try:
            for number in range(frame_total):
                timestamp = number / fps
                while scene_index+1 < len(states) and timestamp >= voice['timeline'][scene_index+1]['start']:
                    scene_index += 1
                scene = project['scenes'][scene_index]
                state = states[scene_index]
                clock = voice['timeline'][scene_index]
                elapsed = timestamp - clock['start']
                fraction = min(1, elapsed/clock['duration'])
                frame = state['background'].copy()
                ease = 1-(1-min(1, elapsed/.45))**3
                frame.paste(state['headline'], (0, 192+round(22*(1-ease))), state['headline'])
                if state['visual']:
                    visual = state['visual']
                    # Small camera movement plus a moving reading guide over actual source evidence.
                    y = 444 + round(12*(1-ease)) - round(5*fraction)
                    frame.paste(visual, (48, y), visual)
                    d = ImageDraw.Draw(frame)
                    d.rounded_rectangle((48, y, 672, y+406), 12, outline='#94AE85', width=2)
                    guide_x = 62 + round(590*fraction)
                    d.line((guide_x, y+399, guide_x+18, y+399), fill='#648B22', width=4)
                else:
                    diagram(frame, scene, state, fraction)
                for i, note in enumerate(state['notes']):
                    if elapsed >= .55 + .45*i:
                        frame.paste(note, (0, 876+i*53), note)
                while subtitle_index+1 < len(subtitles) and timestamp >= subtitles[subtitle_index][0]['end']:
                    subtitle_index += 1
                current_subtitle, layer = subtitles[subtitle_index]
                if current_subtitle['start'] <= timestamp < current_subtitle['end']:
                    frame.paste(layer, (0, 1064), layer)
                draw = ImageDraw.Draw(frame)
                draw.rectangle((48, 1232, 672, 1235), fill='#617363' if state['dark'] else '#CAD3C0')
                draw.rectangle((48, 1232, 48+round(624*timestamp/voice['duration']), 1235), fill=state['accent'] if state['dark'] else '#648B22')
                if elapsed < .17 and previous is not None:
                    frame = Image.blend(previous, frame, min(1, elapsed/.17))
                if abs(elapsed-min(2, clock['duration']/2)) < 1/fps and len(sample_frames) <= scene_index:
                    frame_path = out / 'assets' / f'frame-{scene_index:02}.jpg'
                    frame.save(frame_path, quality=93)
                    sample_frames.append(frame_path)
                process.stdin.write(frame.tobytes())
                if (number+1) % (fps*5) == 0:
                    emit('render', percent=round(100*(number+1)/frame_total), elapsed_seconds=round(time.monotonic()-started))
                if elapsed >= clock['duration'] - 2/fps:
                    previous = frame.copy()
            process.stdin.close()
            status = process.wait(timeout=180)
            if status:
                raise RuntimeError(log.read_text('utf-8', errors='replace')[-2400:])
        except Exception:
            if process.poll() is None:
                process.kill()
            process.wait()
            raise
    # Review frames are decoded from the encoded deliverable, not only the input canvas.
    sample_frames = []
    for i, clock in enumerate(voice['timeline']):
        frame_path = out / 'assets' / f'frame-{i:02}.jpg'
        at = clock['start'] + min(2, clock['duration']/2)
        run([ffmpeg(), '-y', '-hide_banner', '-loglevel', 'error', '-ss', f'{at:.3f}',
             '-i', video, '-frames:v', '1', '-q:v', '2', frame_path], timeout=60)
        sample_frames.append(frame_path)
    # Export a clean cover with the hook and its visual.
    cover_state = states[0]
    cover = cover_state['background'].copy()
    cover.paste(cover_state['headline'], (0, 204), cover_state['headline'])
    if cover_state['visual']:
        cover.paste(cover_state['visual'], (48, 450), cover_state['visual'])
    else:
        diagram(cover, project['scenes'][0], cover_state, 0.4)
    cd = ImageDraw.Draw(cover)
    round_box(cd, (48, 966, 672, 1050), 15, MINT)
    block(cd, (84, 984), project.get('cover_tagline', 'AI工具拆解 · 真实来源 · 实用场景'), 29, INK, width=552, bold=True, limit=1)
    cover.resize((width, height), Image.Resampling.LANCZOS).save(out / 'cover.png')
    contact = Image.new('RGB', (360*3, 640*math.ceil(len(sample_frames)/3)), '#DCE3D5')
    for i, sample in enumerate(sample_frames):
        contact.paste(Image.open(sample).resize((360, 640), Image.Resampling.LANCZOS), ((i%3)*360, (i//3)*640))
    contact.save(out / 'contact-sheet.jpg', quality=94)
    return video, sample_frames
