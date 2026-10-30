"""Require a reviewable research record for projects explicitly marked AI news."""
import json
from pathlib import Path
from urllib.parse import urlparse

def load_research(project,project_path):
    if project.get('content_type')!='ai_news':return None
    research_file=project.get('research_file')
    if not research_file:raise ValueError('AI news requires research_file: dated searches, topic selection, verified claims and a media plan must precede production.')
    path=Path(research_file)
    if not path.is_absolute():path=Path(project_path).resolve().parent/path
    if not path.is_file():raise ValueError(f'AI news research_file is missing: {path}')
    data=json.loads(path.read_text('utf-8-sig'))
    if not data.get('recorded_at') or not data.get('searches') or not all(s.get('query') and s.get('result_urls') for s in data['searches']):
        raise ValueError('AI news research must record executed searches and their actual result URLs.')
    candidates=data.get('candidates',[])
    selected=next((c for c in candidates if c.get('id')==data.get('selected_id')),None)
    if not selected or not selected.get('primary_sources') or not data.get('selection_reason'):
        raise ValueError('AI news research needs a selected candidate, primary sources and an editorial selection reason.')
    source_urls={s['url'] for s in project['sources']}
    checks=data.get('claim_checks',[])
    if not checks or any(not c.get('claim') or c.get('source_url') not in source_urls for c in checks):
        raise ValueError('News claim checks must cite original URLs also declared in project sources.')
    if not data.get('media_plan'):raise ValueError('AI news research must connect topic-specific footage to the script.')
    for url in selected['primary_sources']:
        parsed=urlparse(url)
        if parsed.scheme!='https' or not parsed.hostname or parsed.username:raise ValueError('News primary sources must be public HTTPS URLs.')
    return path,data
