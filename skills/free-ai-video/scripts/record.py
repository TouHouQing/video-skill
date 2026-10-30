"""Record real isolated browser operations, preserving trace and action evidence."""
from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from urllib.parse import urlparse
from media import probe, sha256
from runtime import emit, ffmpeg, run, save_json


def target_url(value, base):
    parsed = urlparse(value)
    if parsed.scheme in ('https', 'http') and parsed.hostname and not parsed.username:
        return value
    path = Path(value)
    if not path.is_absolute():
        path = Path(base) / path
    if path.is_file():
        return path.resolve().as_uri()
    raise ValueError('Recording target must be a public/localhost URL or an existing local page.')


def record_browser(plan_path, output):
    from playwright.sync_api import sync_playwright
    plan_path, output = Path(plan_path).resolve(), Path(output).resolve()
    spec = json.loads(plan_path.read_text('utf-8-sig'))
    target = target_url(spec['url'], plan_path.parent)
    if not spec.get('steps'):
        raise ValueError('A real operation recording needs steps, not just a still screenshot.')
    evidence = output.parent / (output.stem + '-evidence')
    evidence.mkdir(parents=True, exist_ok=True)
    manifest = {'status': 'recording', 'kind': 'real-browser-operation', 'url': target,
                'started_at': datetime.now(timezone.utc).isoformat(), 'actions': [],
                'timing_method': 'Approximate wallclock from page creation; not frame-accurate input timestamps.',
                'paid_api_cost': 0, 'label': spec.get('label', '实际浏览器操作录屏')}
    manifest_path = output.with_suffix('.recording.json')
    save_json(manifest_path, manifest)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            viewport = spec.get('viewport', {'width': 1280, 'height': 900})
            context = browser.new_context(viewport=viewport, record_video_dir=str(evidence), record_video_size=viewport,
                                          locale='zh-CN', reduced_motion='no-preference')
            context.set_default_timeout(12000)
            context.tracing.start(screenshots=True, snapshots=True, sources=False)
            page = context.new_page()
            video = page.video
            started = time.monotonic()
            try:
                response = page.goto(target, wait_until='domcontentloaded', timeout=30000)
                if response and response.status >= 400:
                    raise ValueError(f'Recording target returned HTTP {response.status}.')
                page.wait_for_timeout(int(1000 * spec.get('lead_in', .8)))
                (evidence/'before.html').write_text(page.content(), 'utf-8')
                for index, step in enumerate(spec['steps']):
                    action = step['action']
                    record = {'index': index, 'action': action, 'label': step.get('label', action),
                              'start': time.monotonic()-started}
                    locator = page.locator(step['selector']).first if step.get('selector') else None
                    if locator is not None:
                        locator.wait_for(state='visible')
                        locator.scroll_into_view_if_needed()
                        record['selector'] = step['selector']
                        record['bounding_box'] = locator.bounding_box()
                    if action == 'click':
                        locator.click()
                    elif action == 'fill':
                        locator.fill(step['text'])
                    elif action == 'type':
                        locator.press_sequentially(step['text'], delay=step.get('delay_ms', 65))
                    elif action == 'press':
                        locator.press(step['key']) if locator is not None else page.keyboard.press(step['key'])
                    elif action == 'hover':
                        locator.hover()
                    elif action == 'scroll':
                        page.mouse.wheel(step.get('x', 0), step.get('y', 500))
                    elif action == 'wait':
                        seconds = step.get('seconds', .7)
                        if not 0 <= seconds <= 30:
                            raise ValueError('Each recorded wait must be between 0 and 30 seconds.')
                        page.wait_for_timeout(round(seconds*1000))
                    elif action == 'assert_text':
                        from playwright.sync_api import expect
                        expect(locator).to_contain_text(step['text'])
                    elif action == 'assert_visible':
                        locator.wait_for(state='visible')
                    elif action == 'goto':
                        page.goto(target_url(step['url'], plan_path.parent), wait_until='domcontentloaded')
                    else:
                        raise ValueError(f'Unsupported recording action: {action}')
                    record['end'] = time.monotonic()-started
                    page.wait_for_timeout(int(1000 * step.get('pause', .45)))
                    frame = evidence/f'action-{index:02}.png'
                    page.screenshot(path=str(frame))
                    record.update(status='completed', screenshot=str(frame))
                    manifest['actions'].append(record)
                    save_json(manifest_path, manifest)
                    emit('record_action', index=index, action=action, status='completed')
                page.wait_for_timeout(int(1000 * spec.get('tail', 1)))
                (evidence/'after.html').write_text(page.content(), 'utf-8')
            finally:
                context.tracing.stop(path=str(evidence/'trace.zip'))
                context.close()  # Playwright finalizes video only on context closure.
                browser.close()
            raw = Path(video.path())
        run([ffmpeg(), '-y', '-hide_banner', '-loglevel', 'error', '-i', raw, '-an', '-c:v', 'libx264',
             '-pix_fmt', 'yuv420p', '-preset', 'veryfast', '-crf', '18', '-movflags', '+faststart', output])
        manifest.update(status='completed', path=str(output), raw_path=str(raw), sha256=sha256(output),
                        **probe(output), trace=str(evidence/'trace.zip'),
                        suggested_cuts=[{'source_in': max(0,a['start']-.35),
                                         'source_out': a['end']+.55, 'action_index': a['index']}
                                        for a in manifest['actions'] if a['action'] not in ('wait','assert_text','assert_visible')])
        save_json(manifest_path, manifest)
        return manifest
    except Exception as error:
        manifest.update(status='failed', error=str(error))
        save_json(manifest_path, manifest)
        raise


def record_window(title, seconds, output):
    import os
    if os.name != 'nt' or not title or not 1 <= seconds <= 120:
        raise ValueError('Window recording needs Windows, an explicit window title and 1–120 seconds.')
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    run([ffmpeg(), '-y', '-hide_banner', '-loglevel', 'error', '-f', 'gdigrab', '-framerate', '24',
         '-draw_mouse', '1', '-i', 'title='+title, '-t', seconds, '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2',
         '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'veryfast', output], timeout=seconds+45)
    result = {'status':'completed', 'kind':'real-window-recording', 'title':title, 'path':str(output),
              'sha256':sha256(output), **probe(output), 'paid_api_cost':0}
    save_json(output.with_suffix('.recording.json'), result)
    return result
