"""Local media inventory, declared usage rights and public asset ingestion."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from runtime import ffmpeg, run, save_json


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def probe(path):
    sibling = Path(ffmpeg()).with_name('ffprobe.exe' if Path(ffmpeg()).suffix == '.exe' else 'ffprobe')
    executable = str(sibling) if sibling.exists() else shutil.which('ffprobe')
    if not executable:
        raise RuntimeError('Timeline editing requires ffprobe alongside FFmpeg or on PATH.')
    data = json.loads(run([executable, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', path]).stdout)
    video = next((s for s in data['streams'] if s['codec_type'] == 'video'), None)
    if not video:
        raise ValueError(f'No video stream: {path}')
    return {'width': int(video['width']), 'height': int(video['height']),
            'duration': float(data.get('format', {}).get('duration', video.get('duration', 0)))}


def validate_rights(rights):
    if rights.get('kind') not in ('owned', 'original_capture', 'licensed', 'public_domain', 'source_excerpt'):
        raise ValueError('Media needs rights.kind: owned, original_capture, licensed, public_domain or source_excerpt.')
    if rights['kind'] in ('licensed', 'public_domain'):
        if not rights.get('license') or not rights.get('license_url') or not rights.get('source_url'):
            raise ValueError('Third-party footage needs source_url, license and license_url; public access is not a license.')
    if rights['kind'] == 'source_excerpt' and not rights.get('source_url'):
        raise ValueError('A source excerpt needs its original URL.')


def resolve_media(project, base):
    from PIL import Image
    inventory = {}
    for item in project.get('media', []):
        validate_rights(item.get('rights', {}))
        path = Path(item['path'])
        if not path.is_absolute():
            path = Path(base) / path
        path = path.resolve()
        if not path.is_file():
            raise ValueError(f'Media file missing: {item["id"]}: {path}')
        data = {**item, 'path': str(path), 'sha256': sha256(path)}
        if item['type'] == 'video':
            data.update(probe(path))
            if data['duration'] <= 0:
                raise ValueError('Video duration must be positive.')
        else:
            with Image.open(path) as picture:
                data.update(width=picture.width, height=picture.height)
        if item['rights']['kind'] == 'original_capture':
            manifest = Path(item.get('recording_manifest') or path.with_suffix('.recording.json'))
            if not manifest.is_absolute():
                manifest = Path(base) / manifest
            evidence = json.loads(manifest.read_text('utf-8-sig'))
            if evidence.get('status') != 'completed':
                raise ValueError(f'Recording evidence is incomplete or mismatched: {item["id"]}')
            if evidence.get('sha256') != data['sha256']:
                processing = item.get('processing_manifest')
                if not processing:
                    raise ValueError(f'Recording evidence is incomplete or mismatched: {item["id"]}')
                processing = Path(processing)
                if not processing.is_absolute():
                    processing = Path(base)/processing
                import importlib.util
                module_path = Path(__file__).resolve().parents[2]/'local-media-studio/scripts/receipts.py'
                spec = importlib.util.spec_from_file_location('local_media_receipts', module_path)
                receipts = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(receipts)
                data['processing_lineage'] = receipts.validate_capture_lineage(path, data['sha256'], evidence, processing)
                data['processing_manifest'] = str(processing.resolve())
            default_original = (item['rights'].get('source_url') if item.get('role') in ('source_page', 'source_recording') else None)
            data.setdefault('source_asset_id', default_original or 'capture:'+evidence['sha256'])
            data['recording_manifest'] = str(manifest.resolve())
        inventory[item['id']] = data
    return inventory


def fetch_media(url, output, rights):
    """Fetch an explicitly selected licensed public asset; never scrape accounts."""
    validate_rights(rights)
    if rights['kind'] not in ('licensed', 'public_domain'):
        raise ValueError('Public downloads must carry an explicit third-party license declaration.')
    from factory import BLOCKED_HOSTS
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.hostname in BLOCKED_HOSTS:
        raise ValueError('Expected a public HTTPS asset URL, without credentials or paid endpoints.')
    path = Path(output).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.partial')
    try:
        with urlopen(Request(url, headers={'User-Agent': 'Free-AI-Video/2.0'}), timeout=30) as response:
            redirected = urlparse(response.geturl())
            if redirected.scheme != 'https' or redirected.hostname in BLOCKED_HOSTS or redirected.username:
                raise ValueError('Download redirected outside the public HTTPS media boundary.')
            total = 0
            with temporary.open('wb') as stream:
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > 100 * 1024 * 1024:
                        raise ValueError('Selected asset exceeds 100 MiB; choose a shorter segment/source.')
                    stream.write(chunk)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    record = {'url': url, 'path': str(path), 'sha256': sha256(path), 'rights': rights,
              'rights_verification': 'Declared by the editor; the agent must read the license page.'}
    save_json(path.with_suffix('.media.json'), record)
    return record
