"""Capture genuine public pages with the existing/free Playwright browser."""
from pathlib import Path
import base64
import html
import json
import re
import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from runtime import emit, save_json


def github_excerpt(url):
    parsed = urlparse(url)
    bits = parsed.path.strip('/').split('/')
    if parsed.hostname != 'github.com' or len(bits) < 2:
        raise RuntimeError('No public GitHub excerpt fallback for this URL.')
    repo = '/'.join(bits[:2])
    file = '/'.join(bits[4:]) if len(bits) > 4 and bits[2] == 'blob' else 'README.md'
    request = Request(f'https://api.github.com/repos/{repo}/contents/{file}', headers={'User-Agent': 'Free-AI-Video/1.0'})
    with urlopen(request, timeout=22) as response:
        data = json.load(response)
    text = base64.b64decode(data['content']).decode('utf-8')
    full_text = text
    if parsed.fragment and not re.match(r'L\d', parsed.fragment):
        headings = list(re.finditer(r'^(#{1,6})\s+(.+)$', text, re.M))
        for index, match in enumerate(headings):
            slug = re.sub(r'[^\w\s-]', '', match.group(2)).lower().replace(' ', '-')
            if slug == parsed.fragment:
                ending = next((h.start() for h in headings[index+1:] if len(h.group(1)) <= len(match.group(1))), len(text))
                text = text[match.start():ending]
                break
    lines = [re.sub(r'!\[[^]]*\]\([^)]*\)', '', line).strip() for line in text.splitlines()]
    selected = []
    for line in lines:
        if not line or line.startswith(('<', '[![', '![', '```')) or re.search(r'badge|sponsor|感谢|赞助|优惠', line, re.I):
            continue
        selected.append(line)
        if sum(map(len, selected)) > 1900:
            break
    excerpt = '\n\n'.join(selected)[:2100]
    # Clearly identified transcription of authentic source bytes, never a fake page screenshot.
    rendered = f'''<!doctype html><meta charset="utf-8"><style>
    body{{margin:0;background:#fff;font:26px/1.55 "Microsoft YaHei",sans-serif;color:#17302b}}
    main{{padding:46px 52px}}small{{font-size:18px;color:#657768}}h1{{font-size:38px;margin:20px 0}}
    pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:23px/1.55 Consolas,"Microsoft YaHei",monospace}}
    footer{{font-size:16px;color:#657768;border-top:1px solid #ccc;padding-top:15px}}</style>
    <main><small>真实原文摘录 · GitHub 公开内容接口</small><h1>{html.escape(repo)}</h1>
    <pre>{html.escape(excerpt)}</pre><footer>{html.escape(file)} · {html.escape(url)}</footer></main>'''
    return rendered, f'{repo} / {file}', {'git_blob_sha': data.get('sha'),
           'source_text_sha256': hashlib.sha256(full_text.encode()).hexdigest(), 'excerpt': excerpt,
           'retrieved_at': datetime.now(timezone.utc).isoformat()}


def capture(url, output, selector=None, excerpt_only=False):
    from playwright.sync_api import sync_playwright
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1280, 'height': 900}, device_scale_factor=1)
        method = 'page-screenshot'
        provenance = {}
        try:
            if excerpt_only:
                raise RuntimeError('Use a clearly labelled source excerpt for this page.')
            response = page.goto(url, wait_until='domcontentloaded', timeout=18000)
            if response and response.status >= 400:
                raise RuntimeError(f'Source returned HTTP {response.status}')
            page.wait_for_timeout(1200)
            if selector:
                element = page.locator(selector).first
                element.wait_for(timeout=8000)
                # Long articles must stay readable instead of shrinking a whole README.
                rect = element.bounding_box()
                page.screenshot(path=str(path), clip={'x':rect['x'], 'y':rect['y'], 'width':min(rect['width'],1176), 'height':min(rect['height'],650)})
            else:
                if 'github.com/' in url:
                    content = page.locator('article').first
                    if content.count():
                        content.scroll_into_view_if_needed()
                page.screenshot(path=str(path), full_page=False)
            title = page.title()
        except Exception:
            document, title, provenance = github_excerpt(url)
            page.close()
            page = browser.new_page(viewport={'width': 1280, 'height': 900}, device_scale_factor=1)
            page.set_content(document, wait_until='domcontentloaded')
            page.screenshot(path=str(path), full_page=False)
            method = 'public-source-excerpt'
        browser.close()
    data = {'url': url, 'path': str(path), 'title': title, 'status': 'captured', 'method': method}
    if provenance:
        path.with_suffix('.source.txt').write_text(provenance.pop('excerpt'), 'utf-8')
        data['provenance'] = provenance
    save_json(path.with_suffix('.meta.json'), data)
    emit('capture', **data)
    return data
