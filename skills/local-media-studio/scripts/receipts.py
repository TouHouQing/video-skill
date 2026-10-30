"""Hashed processing receipts and conservative lineage for edited recordings."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def sidecar(path):
    # Keep the media extension: clip.mp4 and clip.wav must not share a receipt.
    path = Path(path)
    return path.with_name(path.name+'.processing.json')


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name+'.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load(path):
    return json.loads(Path(path).read_text('utf-8-sig'))


def file_record(path, include_parent=False):
    path = Path(path).resolve()
    data = {'path': str(path), 'sha256': sha256(path)}
    parent = sidecar(path)
    if include_parent and parent.is_file():
        receipt = load(parent)
        if receipt.get('status') != 'completed' or data not in receipt.get('outputs', []):
            raise ValueError('Input processing receipt does not match its file: '+str(path))
        data.update(processing_manifest=str(parent), processing_sha256=sha256(parent))
    return data


def tracked_run(tool, script, args, inputs, output, env, reuse=False):
    """The declared inputs include every auxiliary file that affects processing."""
    output = Path(output).resolve()
    paths = [Path(path).resolve() for path in inputs]
    if not paths or output in paths:
        raise ValueError('Tracked processing needs inputs and a separate output path.')
    # Do not certify a file unrelated to the command being executed.
    argument_paths = set()
    for value in args:
        if not value.startswith('-'):
            try:
                argument_paths.add(Path(value).resolve())
            except (ValueError, OSError):
                pass
    if output not in argument_paths or any(path not in argument_paths for path in paths):
        raise ValueError('Every declared input/output must appear in the tool arguments.')
    records = [file_record(path, include_parent=True) for path in paths]
    bundle = hashlib.sha256()
    for file in sorted(Path(script).parent.glob('*.py')):
        bundle.update(file.name.encode())
        bundle.update(file.read_bytes())
    signature = {'schema_version': 1, 'tool': tool, 'script_sha256': sha256(script),
                 'runner_sha256': sha256(__file__), 'vendor_bundle_sha256': bundle.hexdigest(),
                 'python': sys.version, 'args': args, 'inputs': records, 'output_path': str(output)}
    fingerprint = hashlib.sha256(json.dumps(signature, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    receipt_path = sidecar(output)
    if reuse and receipt_path.is_file() and output.is_file():
        old = load(receipt_path)
        if old.get('status') == 'completed' and old.get('fingerprint') == fingerprint and old.get('outputs') == [file_record(output)]:
            return 0, {'status': 'reused', 'output': str(output), 'receipt': str(receipt_path), 'fingerprint': fingerprint}
    receipt = {**signature, 'fingerprint': fingerprint, 'status': 'running',
               'started_at': datetime.now(timezone.utc).isoformat()}
    write(receipt_path, receipt)
    try:
        result = subprocess.run([sys.executable, str(script), *args], env=env)
        if result.returncode:
            raise RuntimeError(f'Media tool exited with {result.returncode}.')
        if records != [file_record(path, include_parent=True) for path in paths]:
            raise ValueError('Input changed during processing; output is not certified.')
        receipt.update(status='completed', outputs=[file_record(output)],
                       completed_at=datetime.now(timezone.utc).isoformat())
        write(receipt_path, receipt)
        return 0, {'status': 'completed', 'output': str(output), 'receipt': str(receipt_path), 'fingerprint': fingerprint}
    except Exception as error:
        receipt.update(status='failed', error=str(error))
        write(receipt_path, receipt)
        raise


# Only transformations that preserve the original picture can count as a recording.
PICTURE_OPERATIONS = {'video': {'cut', 'speed', 'aspect', 'compress'},
                      'reframe': {'reframe'}, 'subtitles': {'burn'}}


def validate_capture_lineage(output, output_sha, root_recording, receipt_path, seen=None):
    seen = set() if seen is None else set(seen)
    path = Path(receipt_path).resolve()
    if path in seen or len(seen) >= 20:
        raise ValueError('Cyclic or excessive recording-processing lineage.')
    seen.add(path)
    receipt = load(path)
    if receipt.get('status') != 'completed' or {'path': str(Path(output).resolve()), 'sha256': output_sha} not in receipt.get('outputs', []):
        raise ValueError('Processed recording does not match its completed receipt.')
    args = receipt.get('args', [])
    if not args or args[0] not in PICTURE_OPERATIONS.get(receipt.get('tool'), set()):
        raise ValueError('This operation does not preserve recording evidence; do not classify it as original_capture.')
    inputs = receipt.get('inputs', [])
    if not inputs:
        raise ValueError('Recording receipt has no original input.')
    for item in inputs:
        if sha256(item['path']) != item['sha256']:
            raise ValueError('A processing input has changed: '+item['path'])
    primary = inputs[0]
    if primary['sha256'] == root_recording.get('sha256'):
        return {'root_sha256': primary['sha256'], 'root_path': primary['path'], 'depth': len(seen)}
    parent = primary.get('processing_manifest')
    if not parent or sha256(parent) != primary.get('processing_sha256'):
        raise ValueError('Processed recording lost its original recording lineage.')
    return validate_capture_lineage(primary['path'], primary['sha256'], root_recording, parent, seen)
