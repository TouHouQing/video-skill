"""Install only free local dependencies into this skill's private directory."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
target = ROOT / '.runtime' / 'packages'
target.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(target))
packages = {'PIL': 'Pillow>=10,<13', 'edge_tts': 'edge-tts>=7.2,<8',
            'playwright': 'playwright>=1.50,<2',
            'numpy': 'numpy>=1.26,<3'}
missing = [requirement for module, requirement in packages.items() if importlib.util.find_spec(module) is None]
if missing:
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check', '--target', str(target), *missing], check=True)
from runtime import run, save_json, ffmpeg, emit
try:
    ffmpeg()
except ImportError:
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check', '--target', str(target), 'imageio-ffmpeg>=0.6,<0.7'], check=True)
save_json(ROOT / '.runtime' / 'runtime.json', {'python': sys.executable, 'packages': str(target), 'ffmpeg': ffmpeg()})
from playwright.sync_api import sync_playwright
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        browser.close()
except Exception:
    environment = dict(__import__('os').environ)
    environment['PYTHONPATH'] = str(target)
    subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium', '--only-shell'], env=environment, check=True)
emit('bootstrap', status='ready', python=sys.executable, paid_api_cost=0)
