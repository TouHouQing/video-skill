"""Local dependency and process helpers; no model credentials or paid endpoints."""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / '.runtime' / 'packages'
if PACKAGES.exists():
    sys.path.insert(0, str(PACKAGES))


def emit(stage, **data):
    print(json.dumps({'stage': stage, **data}, ensure_ascii=False), flush=True)


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def ffmpeg():
    installed = shutil.which('ffmpeg')
    if installed:
        return installed
    cached = sorted((Path.home() / '.cache/codex-studio-toolchains/ffmpeg').glob('*/bin/ffmpeg.exe'))
    if cached:
        return str(cached[-1])
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def run(args, *, timeout=300, check=True, **kwargs):
    options = dict(capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
    if os.name == 'nt':
        options['creationflags'] = subprocess.CREATE_NO_WINDOW
    options.update(kwargs)
    result = subprocess.run([str(a) for a in args], **options)
    if check and result.returncode:
        raise RuntimeError(f'Command failed ({result.returncode}): {(result.stderr or result.stdout)[-2200:]}')
    return result


def font_path(bold=False):
    candidates = [
        Path('C:/Windows/Fonts/msyhbd.ttc' if bold else 'C:/Windows/Fonts/msyh.ttc'),
        Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc' if bold else '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'),
        Path('/System/Library/Fonts/PingFang.ttc'),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    raise RuntimeError('No CJK font found. Install Microsoft YaHei, PingFang or Noto Sans CJK before rendering Chinese.')
