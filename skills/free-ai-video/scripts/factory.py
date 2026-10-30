"""CLI for the zero-additional-paid-API AI short video skill."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import urlparse
from runtime import ROOT, emit, ffmpeg, font_path, run, save_json

BLOCKED_HOSTS = {'api.openai.com', 'api.anthropic.com', 'api.elevenlabs.io',
                 'queue.fal.run', 'fal.run', 'api.fal.ai', 'api.replicate.com',
                 'api.runwayml.com', 'api.heygen.com', 'api.tikhub.io'}


def validate(project):
    for key in ('title', 'angle', 'sources', 'scenes'):
        if not project.get(key):
            raise ValueError(f'Missing required project field: {key}')
    if not 3 <= len(project['scenes']) <= 12:
        raise ValueError('Use 3–12 scenes for a short video.')
    sources = {}
    for source in project['sources']:
        if not all(source.get(key) for key in ('id', 'url', 'label', 'claims')):
            raise ValueError('Each source needs id, url, label and verified claims.')
        parsed = urlparse(source['url'])
        if parsed.scheme != 'https' or not parsed.hostname or parsed.hostname in BLOCKED_HOSTS or parsed.username:
            raise ValueError(f'Only public HTTPS source pages are permitted, not paid model/data endpoints: {source["id"]}')
        if source['id'] in sources:
            raise ValueError(f'Duplicate source ID: {source["id"]}')
        sources[source['id']] = source
    scene_ids = set()
    for scene in project['scenes']:
        if not all(scene.get(key) for key in ('id', 'headline', 'narration', 'kind')):
            raise ValueError('Each scene needs id, headline, narration and kind.')
        if scene['kind'] not in ('hook', 'evidence', 'steps', 'comparison', 'close'):
            raise ValueError(f'Unsupported scene kind: {scene["kind"]}')
        if scene['id'] in scene_ids:
            raise ValueError(f'Duplicate scene ID: {scene["id"]}')
        scene_ids.add(scene['id'])
        unknown = set(scene.get('source_ids', [])) - sources.keys()
        if unknown:
            raise ValueError(f'Unresolved source references: {sorted(unknown)}')
        if len(scene['narration']) > 350:
            raise ValueError('A scene narration must be under 350 characters.')
    if project.get('voice_mode', 'auto') not in ('auto', 'edge', 'local', 'ming'):
        raise ValueError('voice_mode must be auto, edge, local or ming.')
    width, height, fps = project.get('width', 1080), project.get('height', 1920), project.get('fps', 24)
    if not all(isinstance(n, int) for n in (width, height, fps)) or width < 360 or width % 2 or height % 2 or width*16 != height*9 or not 12 <= fps <= 60:
        raise ValueError('Expected even 9:16 portrait dimensions, width >=360, and integer fps 12–60.')
    if project.get('approval_status') not in (None, 'draft', 'awaiting_user', 'approved'):
        raise ValueError('approval_status must be draft, awaiting_user or approved.')
    from edit_plan import validate_edit
    validate_edit(project)
    return project


def doctor():
    modules = {name: importlib.util.find_spec(name) is not None for name in ('PIL', 'numpy', 'edge_tts', 'imageio_ffmpeg', 'playwright')}
    status = {'python': sys.executable, 'modules': modules, 'paid_apis_enabled': False}
    try:
        status['ffmpeg'] = ffmpeg()
        status['font'] = font_path()
    except Exception as e:
        status['error'] = str(e)
    status['ready'] = all(modules[name] for name in ('PIL', 'numpy', 'playwright')) and 'error' not in status
    status['editing_modes'] = ['screencast', 'motion', 'montage', 'hybrid', 'cards (legacy)']
    status['capabilities'] = ['browser-recording', 'named-window-recording (Windows)', 'shot-timeline',
                            'trim', 'retime', 'camera-reframe', 'highlights', 'cut/dissolve/wipe', 'draft-only-preview']
    companions = {'media': ROOT.parent/'local-media-studio/scripts/studio.py',
                  'ops': ROOT.parent/'ai-content-ops/scripts/content_ops.py',
                  'rss': ROOT/'scripts/vendor/easel/rss_digest.py'}
    status['integrated_tools'] = {key: {'path': str(path), 'installed': path.is_file()} for key, path in companions.items()}
    status['requires_easel_server'] = False
    save_json(ROOT / '.runtime/runtime.json', status)
    emit('doctor', **status)
    return status


def verify(video, output=None, expected_duration=None, expected_width=None):
    video = Path(video)
    if not video.exists() or video.stat().st_size < 20000:
        raise RuntimeError('Final video is missing or implausibly small.')
    result = run([ffmpeg(), '-hide_banner', '-i', video, '-vf', 'blackdetect=d=0.5:pix_th=0.03',
                  '-af', 'volumedetect', '-f', 'null', '-'], timeout=300, check=False)
    log = result.stderr
    duration_match = re.search(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)', log)
    resolution = re.search(r'Video:.*?\b(\d{3,5})x(\d{3,5})\b', log)
    peak = re.search(r'max_volume:\s*(-?[\d.]+) dB', log)
    if not duration_match or not resolution or not peak:
        raise RuntimeError(f'Could not verify duration, dimensions or audible audio: {log[-1800:]}')
    h, m, s = map(float, duration_match.groups())
    seconds = h*3600 + m*60 + s
    w, hgt = map(int, resolution.groups())
    checks = {'decode_success': result.returncode == 0, 'portrait_9_16': w*16 == hgt*9,
              'audible_audio': float(peak.group(1)) > -45,
              'no_black_sections': 'black_start:' not in log,
              'h264_video': bool(re.search(r'Video: h264', log)),
              'aac_audio': bool(re.search(r'Audio: aac', log))}
    if expected_duration is not None:
        checks['duration_matches_audio'] = abs(seconds - expected_duration) < 0.5
    if expected_width:
        checks['requested_resolution'] = w == expected_width
    report = {'passed': all(checks.values()), 'checks': checks, 'duration_seconds': seconds,
              'width': w, 'height': hgt, 'audio_peak_db': float(peak.group(1)), 'bytes': video.stat().st_size,
              'checked_at': datetime.now(timezone.utc).isoformat()}
    if output:
        save_json(output, report)
    if not report['passed']:
        raise RuntimeError(f'Video verification failed: {report}')
    return report


def publishing(project, output, voice):
    from voice import timestamp
    path = Path(output)
    text = []
    for i, item in enumerate(voice['subtitles'], 1):
        text.append(f'{i}\n{timestamp(item["start"])} --> {timestamp(item["end"])}\n{item["text"]}\n')
    (path/'captions.srt').write_text('\n'.join(text), 'utf-8')
    titles = project.get('titles') or [project['title']]
    md = [f'# {project["title"]}', '', '**标题候选**', '', *[f'- {t}' for t in titles], '',
          '**发布正文**', '', project.get('description') or project['angle'], '',
          ' '.join('#'+str(tag).lstrip('#') for tag in project.get('hashtags', ['AI工具', 'AI自动化'])), '',
          '**字幕稿**', '', *[scene['narration']+'\n' for scene in project['scenes']], '', '**事实来源**', '']
    md += [f'- [{s["label"]}]({s["url"]})' for s in project['sources']]
    credited = [item for item in project.get('media', []) if item.get('rights', {}).get('source_url')]
    if credited:
        md += ['', '**素材来源与署名**', '']
        for item in credited:
            rights = item['rights']
            label = item.get('label', item['id'])
            creator = rights.get('creator', '作者见原始来源')
            license_text = f'[{rights["license"]}]({rights["license_url"]})' if rights.get('license_url') else rights['kind']
            md.append(f'- [{label}]({rights["source_url"]}) · {creator} · {license_text}')
    md += ['', '本片画面与配音含自动制作内容。零额外 API 费用不包含已有 Codex 额度、设备和电力。',
           f'配音后端：{voice["provider"]}；字幕为分句时长分配，未做逐字强制对齐。']
    (path/'publishing.md').write_text('\n'.join(md), 'utf-8')


def produce(project_path, output):
    project_path, out = Path(project_path).resolve(), Path(output).resolve()
    from workflow import prepare_inputs, sync_production
    preflight, project, inventory, news_research = prepare_inputs(project_path, 'produce')
    out.mkdir(parents=True, exist_ok=True)
    media = out/'assets'
    media.mkdir(exist_ok=True)
    report = {'status': 'running', 'started_at': datetime.now(timezone.utc).isoformat(),
              'pipeline_version': 4,
              'project_hash': preflight['settings']['effective_sha256'],
              'settings': preflight['settings'],
              'paid_api_cost': 0, 'paid_apis_enabled': False,
              'cost_scope': 'Existing Codex usage, computer and electricity excluded; no paid API calls are implemented.',
              'source_captures': [], 'warnings': list(preflight['warnings'])}
    save_json(out/'preflight.json', preflight)
    save_json(out/'project.json', project)
    save_json(out/'sources.json', project['sources'])
    if news_research:
        save_json(out/'research.json', news_research[1])
    save_json(out/'report.json', report)
    try:
        from capture import capture
        source_assets = {}
        for source in project['sources']:
            if source['id'] not in preflight['sources_to_capture']:
                continue
            # Hash URL/selector so stale screenshots cannot silently survive a changed source.
            research_hash = hashlib.sha256(news_research[0].read_bytes()).hexdigest() if news_research else ''
            capture_key = hashlib.sha256((source['url']+str(source.get('capture_selector'))+research_hash).encode()).hexdigest()[:12]
            image = media/f'source-{capture_key}.png'
            try:
                if not image.exists():
                    data = capture(source['url'], image, source.get('capture_selector'), source.get('excerpt_only', False))
                else:
                    metadata = image.with_suffix('.meta.json')
                    data = json.loads(metadata.read_text('utf-8')) if metadata.exists() else {'url': source['url'], 'path': str(image), 'method': 'unknown-cached'}
                    data['status'] = 'cached'
                source_assets[source['id']] = image
                report['source_captures'].append(data)
            except Exception as e:
                message = f'{source["id"]}: {str(e)[:400]}'
                report['warnings'].append(message)
                report['source_captures'].append({'url': source['url'], 'status': 'failed', 'error': str(e)[:400]})
                emit('capture_warning', message=message)
        assets = {}
        for i, scene in enumerate(project['scenes']):
            if scene.get('asset'):
                candidate = Path(scene['asset'])
                if not candidate.is_absolute():
                    candidate = project_path.parent/candidate
                if not candidate.is_file():
                    raise ValueError(f'Explicit scene asset is missing: {candidate}')
                assets[i] = candidate
            elif scene['kind'] == 'evidence':
                for source_id in scene.get('source_ids', []):
                    if source_id in source_assets:
                        assets[i] = source_assets[source_id]
                        break
        from voice import prepare
        voice = prepare(project, media)
        save_json(media/'timeline.json', {k:v for k,v in voice.items() if k != 'records'})
        publishing(project, out, voice)
        if project.get('visual_mode', 'cards') == 'cards':
            from compose import render
            video, frames = render(project, voice, assets, out)
        else:
            from editor import render
            video, frames = render(project, voice, inventory, out)
        quality = verify(video, out/'verification.json', voice['duration'], project.get('width',1080))
        report.update(status='completed', completed_at=datetime.now(timezone.utc).isoformat(),
                      narration={k:v for k,v in voice.items() if k in ('provider','voice','fallback_reason','duration','timing_method')},
                      verification=quality, video=str(video), cover=str(out/'cover.png'),
                      visual_mode=project.get('visual_mode', 'cards'),
                      edit_plan=str(out/'edit-plan.json') if project.get('visual_mode', 'cards') != 'cards' else None,
                      visual_mix=str(out/'visual-mix.json') if project.get('visual_mode', 'cards') != 'cards' else None,
                      frame_samples=[str(p) for p in frames],
                      editorial_review='Pending Codex visual inspection of contact-sheet.jpg and factual review of source claims.')
        if voice['fallback_reason']:
            report['warnings'].append('Online TTS unavailable; the whole narration was synthesized with a local Chinese voice for consistency.')
        save_json(out/'report.json', report)
        try:
            report['channel_sync'] = sync_production(project, project_path, out/'report.json')
        except Exception as error:
            report['warnings'].append('Production completed, but local topic update failed: '+str(error))
        save_json(out/'report.json', report)
        emit('complete', video=str(video), report=str(out/'report.json'), duration_seconds=quality['duration_seconds'], paid_api_cost=0)
        return report
    except Exception as error:
        report.update(status='failed', error=str(error), failed_at=datetime.now(timezone.utc).isoformat())
        save_json(out/'report.json', report)
        raise


def main():
    parser = argparse.ArgumentParser(description='Free AI short video tools. No paid providers or model keys.')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor')
    pf = sub.add_parser('preflight', help='Inspect settings, research and scene/material handoff without TTS or rendering.')
    pf.add_argument('--project', required=True)
    pf.add_argument('--stage', choices=['draft', 'produce'], default='produce')
    pf.add_argument('--output')
    cp = sub.add_parser('collect')
    cp.add_argument('--output', required=True)
    cp.add_argument('--hours', type=int, default=168)
    cp.add_argument('--limit', type=int, default=40)
    cp.add_argument('--feeds', help='Optional JSON list of {name,url} public RSS sources, replacing the default feed list.')
    cp.add_argument('--hotlists', default='', help='Optional third-party trend leads: weibo,douyin,zhihu,bilibili. No keys.')
    for command, help_text in [('media', 'Local media tools'), ('ops', 'Local content operations'), ('rss', 'Custom RSS/Atom digest')]:
        forward = sub.add_parser(command, help=help_text, add_help=False)
        forward.add_argument('args', nargs=argparse.REMAINDER)
    sp = sub.add_parser('capture')
    sp.add_argument('--url', required=True)
    sp.add_argument('--output', required=True)
    sp.add_argument('--selector')
    sp.add_argument('--source-excerpt', action='store_true')
    rp = sub.add_parser('record')
    rp.add_argument('--plan', required=True)
    rp.add_argument('--output', required=True)
    ac = sub.add_parser('autocut')
    ac.add_argument('--manifest', required=True)
    ac.add_argument('--output', required=True)
    wp = sub.add_parser('record-window')
    wp.add_argument('--title', required=True)
    wp.add_argument('--seconds', type=float, required=True)
    wp.add_argument('--output', required=True)
    np = sub.add_parser('record-native')
    np.add_argument('--title', required=True)
    np.add_argument('--seconds', type=float, required=True)
    np.add_argument('--output', required=True)
    dp = sub.add_parser('draft')
    dp.add_argument('--project', required=True)
    dp.add_argument('--output', required=True)
    mp = sub.add_parser('fetch-media')
    mp.add_argument('--url', required=True)
    mp.add_argument('--rights', required=True, help='JSON file with license, source_url and license_url.')
    mp.add_argument('--output', required=True)
    pp = sub.add_parser('produce')
    pp.add_argument('--project', required=True)
    pp.add_argument('--output', required=True)
    vp = sub.add_parser('verify')
    vp.add_argument('--video', required=True)
    vp.add_argument('--output')
    args = parser.parse_args()
    if args.command == 'doctor':
        if not doctor()['ready']:
            sys.exit(2)
    elif args.command == 'preflight':
        from workflow import prepare_inputs
        report, _, _, _ = prepare_inputs(args.project, args.stage)
        if args.output:
            save_json(args.output, report)
        emit('preflight', **report)
    elif args.command == 'collect':
        from collect import collect
        result = collect(args.output, args.hours, args.limit, feeds_file=args.feeds, hotlists=args.hotlists)
        emit('collect', candidates=len(result['candidates']), undated_leads=len(result['undated_leads']), source_errors=result['source_errors'], output=args.output, paid_api_cost=0)
    elif args.command in ('media', 'ops', 'rss'):
        import os, subprocess
        paths = {'media': ROOT.parent/'local-media-studio/scripts/studio.py',
                 'ops': ROOT.parent/'ai-content-ops/scripts/content_ops.py',
                 'rss': ROOT/'scripts/vendor/easel/rss_digest.py'}
        script = paths[args.command]
        if not script.is_file():
            raise ValueError(f'Integrated tool is missing: {script}')
        env = dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
        rest = args.args[1:] if args.args[:1] == ['--'] else args.args
        sys.exit(subprocess.run([sys.executable, str(script), *(rest or ['--help'])], env=env).returncode)
    elif args.command == 'capture':
        from capture import capture
        capture(args.url, args.output, args.selector, args.source_excerpt)
    elif args.command == 'produce':
        produce(args.project, args.output)
    elif args.command == 'record':
        from record import record_browser
        emit('record', **record_browser(args.plan, args.output))
    elif args.command == 'record-window':
        from record import record_window
        emit('record_window', **record_window(args.title, args.seconds, args.output))
    elif args.command == 'record-native':
        from native_capture import record_native
        emit('record_native', **record_native(args.title, args.seconds, args.output))
    elif args.command == 'autocut':
        from autocut import rough_cut
        data = rough_cut(args.manifest)
        save_json(args.output, data)
        emit('autocut', output=args.output, shots=len(data['shots']), omitted_seconds=data['omitted_seconds'])
    elif args.command == 'fetch-media':
        from media import fetch_media
        emit('fetch_media', **fetch_media(args.url, args.output, json.loads(Path(args.rights).read_text('utf-8-sig'))))
    elif args.command == 'draft':
        from media import resolve_media
        from editor import draft
        path = Path(args.project).resolve()
        from workflow import prepare_inputs
        _, project, _, _ = prepare_inputs(path, 'draft')
        if project.get('visual_mode', 'cards') == 'cards':
            raise ValueError('Shot preview expects a new visual_mode; legacy cards are not converted implicitly.')
        emit('draft', **draft(project, resolve_media(project, path.parent), args.output))
    elif args.command == 'verify':
        emit('verify', **verify(args.video, args.output))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        emit('error', message=str(error))
        sys.exit(1)
