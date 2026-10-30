"""Provision the media skill's own optional libraries without an Easel environment."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index-url', help='Per-run pip mirror; does not change pip configuration.')
    parser.add_argument('--basic-only', action='store_true')
    args = parser.parse_args()
    folder = ROOT/'.runtime/venv'
    python = folder/('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.exists():
        venv.EnvBuilder(with_pip=True, system_site_packages=True).create(folder)
    requirements = {'PIL': 'Pillow>=10,<14'}
    if not args.basic_only:
        requirements.update({'numpy': 'numpy>=1.26,<3', 'cv2': 'opencv-python>=4.9,<5',
                             'librosa': 'librosa>=0.11,<1', 'faster_whisper': 'faster-whisper>=1.2,<2'})
    probe = 'import importlib.util,json;print(json.dumps({k:importlib.util.find_spec(k)is not None for k in '+repr(list(requirements))+'}))'
    checked = subprocess.run([str(python), '-c', probe], capture_output=True, text=True, check=True)
    installed = json.loads(checked.stdout)
    missing = [requirement for module, requirement in requirements.items() if not installed[module]]
    if missing:
        command = [str(python), '-m', 'pip', 'install', '--disable-pip-version-check']
        if args.index_url:
            command.extend(['--index-url', args.index_url])
        subprocess.run([*command, *missing], check=True)
    config = {'python': str(python.resolve()), 'managed_by': 'local-media-studio',
              'paid_apis_enabled': False, 'asr_weights_downloaded_by_bootstrap': False}
    (ROOT/'.runtime/runtime.json').write_text(json.dumps(config, ensure_ascii=False, indent=2), 'utf-8')
    print(json.dumps(config, ensure_ascii=False))


if __name__ == '__main__':
    main()
