"""Local content state, scheduling records and comparable performance summaries."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import statistics
import sys
import tempfile

REQUIRED = {
    'topics': ('id', 'title', 'audience_problem', 'sources'),
    'calendar': ('id', 'topic_id', 'planned_at', 'status'),
    'performance': ('id', 'post_id', 'platform', 'observed_at', 'window_hours'),
    'learning': ('id', 'observation', 'evidence', 'recorded_at'),
}
COUNTS = ('views', 'impressions', 'completions', 'follows', 'qualified_leads', 'likes', 'saves', 'shares')


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text('utf-8-sig'))


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    fd, name = tempfile.mkstemp(prefix=path.name+'.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError('Timestamp needs a timezone: '+value)
    return parsed


def validate(kind, row):
    if not isinstance(row, dict):
        raise ValueError('Each record must be an object.')
    for key in REQUIRED[kind]:
        if row.get(key) is None or row[key] == '' or row[key] == []:
            raise ValueError(f'{kind}: missing {key}')
    for key in REQUIRED[kind]:
        if key not in ('sources', 'evidence', 'window_hours') and not isinstance(row[key], str):
            raise ValueError(f'{key} must be text.')
    for field in ('planned_at', 'observed_at', 'recorded_at', 'occurred_at', 'published_at'):
        if row.get(field):
            timestamp(row[field])
    for field in ('sources', 'evidence'):
        if field in row and (not isinstance(row[field], list) or not row[field]):
            raise ValueError(field+' must be a nonempty list.')
    if kind == 'calendar':
        if row['status'] not in ('planned', 'in_production', 'ready', 'published', 'cancelled'):
            raise ValueError('Unsupported calendar status.')
        if row['status'] == 'published' and not (row.get('published_at') and row.get('url')):
            raise ValueError('A published record needs its actual published_at and URL.')
    if kind == 'performance':
        hours = row['window_hours']
        if isinstance(hours, bool) or not isinstance(hours, (int, float)) or not math.isfinite(hours) or hours <= 0:
            raise ValueError('window_hours must be positive and finite.')
        for key in COUNTS:
            value = row.get(key)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                raise ValueError(key+' must be a nonnegative integer or null.')
        if row.get('completions') is not None and row.get('views') is not None and row['completions'] > row['views']:
            raise ValueError('completions cannot exceed views.')
    return row


def initialize(root):
    root.mkdir(parents=True, exist_ok=True)
    profile = {
        'created_at': now(),
        'identity': {'language': 'zh-CN', 'niche': 'AI 资讯与实际应用', 'offer': None},
        'audience': {'region': '中国大陆', 'specific_customer': None},
        'platforms': [], 'goals': ['涨粉', '获客'],
        'preferences': {
            'format': '9:16 vertical video', 'visual_style': 'source_led',
            'voice_mode': 'ming', 'voice_profile': 'anime-c', 'backup_tts': 'VoxCPM2 (reserved)',
            'domestic_model_currency': 'CNY / domestic official prices',
            'foreign_model_currency': 'official native currency', 'paid_apis_enabled': False,
            'editing': '真实操作与相关素材、连贯切镜、口语开头',
            'model_launch_focus': ['新模型能力', '国内可用方式与价格', '合理竞品对比', '适合谁用与限制'],
            'opening': '先说核实的新闻重点与观众收益，可用真实发布事件和日期切入',
            'footage': '素材逐句贴合文案；完整观点保持连贯，不按固定秒数频繁切页',
            'source_led_targets': {'source_material_ratio': .9, 'recording_ratio': .65, 'max_standalone_motion_seconds': 3},
            'draft_gate': '仅在该任务要求先审草稿时等待同意；直接要求成片则继续制作',
        },
        'content_pillars': [],
    }
    created = []
    for name, data in [('profile', profile), *[(kind, []) for kind in REQUIRED]]:
        path = root/(name+'.json')
        if not path.exists():
            write(path, data)
            created.append(path.name)
    return {'workspace': str(root), 'created': created, 'publishing_enabled': False}


def record(root, kind, input_path):
    rows = read(input_path)
    return record_rows(root, kind, rows if isinstance(rows, list) else [rows])


def record_rows(root, kind, rows):
    if not (root/'profile.json').exists():
        raise ValueError('Initialize this workspace before recording content state.')
    identifiers = set()
    for row in rows:
        validate(kind, row)
        if row['id'] in identifiers:
            raise ValueError('Duplicate id in input batch: '+row['id'])
        identifiers.add(row['id'])
    path = root/(kind+'.json')
    old = read(path)
    lookup = {item['id']: item for item in old}
    audit = []
    for row in rows:
        previous = lookup.get(row['id'])
        if previous != row:
            audit.append({'at': now(), 'kind': kind, 'id': row['id'], 'before': previous, 'after': row})
        lookup[row['id']] = row
    write(path, list(lookup.values()))
    if audit:
        with (root/'history.jsonl').open('a', encoding='utf-8') as f:
            for item in audit:
                f.write(json.dumps(item, ensure_ascii=False, allow_nan=False)+'\n')
    return {'workspace': str(root), 'kind': kind, 'received': len(rows), 'changed': len(audit), 'total': len(lookup)}


def brief(root, stage='discover', topic_id=None, limit=8):
    if not 1 <= limit <= 30:
        raise ValueError('Brief limit must be 1–30.')
    data = {key: read(root/(key+'.json')) for key in ('profile', *REQUIRED)}
    selected = next((row for row in data['topics'] if row['id'] == topic_id), None) if topic_id else None
    if topic_id and selected is None:
        raise ValueError('Unknown topic_id: '+topic_id)
    result = {'workspace': str(root), 'stage': stage, 'profile': data['profile'],
              'counts': {key: len(data[key]) for key in REQUIRED}, 'selected_topic': selected}
    if stage in ('discover', 'draft'):
        result['learning'] = data['learning'][-limit:]
    if stage == 'discover':
        result['open_topics'] = [row for row in data['topics'] if row.get('status') not in ('published', 'cancelled')][-limit:]
    if stage in ('draft', 'produce'):
        result['calendar'] = [row for row in data['calendar'] if not topic_id or row['topic_id'] == topic_id][-limit:]
    if stage == 'review':
        result['learning'] = data['learning'][-limit:]
        result['performance_command'] = 'analyze --workspace '+str(root)
    return result


def attach_production(root, topic_id, project_path, report_path):
    topics = read(root/'topics.json')
    topic = next((row for row in topics if row['id'] == topic_id), None)
    if topic is None:
        raise ValueError('Unknown topic_id; create the verified topic before linking production.')
    report_path = Path(report_path).resolve()
    report = read(report_path)
    video = Path(report.get('video', ''))
    if report.get('status') != 'completed' or not report.get('verification', {}).get('passed') or not video.is_file():
        raise ValueError('Only a completed and technically verified production can be linked.')
    artifact = {'project_path': str(Path(project_path).resolve()), 'report_path': str(report_path),
                'video': str(video.resolve()), 'project_hash': report.get('project_hash'),
                'recorded_at': now(), 'editorial_review': 'pending'}
    previous = topic.get('artifacts', [])
    artifacts = [row for row in previous if (row.get('video'), row.get('project_hash')) != (artifact['video'], artifact['project_hash'])]
    artifacts.append(artifact)
    updated = {**topic, 'project_path': artifact['project_path'], 'deliverable_path': str(video.resolve().parent), 'artifacts': artifacts}
    if topic.get('status') not in ('published', 'cancelled'):
        updated['status'] = 'produced_pending_review'
    result = record_rows(root, 'topics', [updated])
    return {**result, 'topic_id': topic_id, 'production_state': updated['status'], 'account_action': None}


def analyze(root):
    latest = {}
    rows = read(root/'performance.json')
    for row in rows:
        validate('performance', row)
        key = (row['platform'], row['post_id'], row['window_hours'])
        if key not in latest or timestamp(row['observed_at']) > timestamp(latest[key]['observed_at']):
            latest[key] = row
    groups = {}
    for (platform, post, hours), row in latest.items():
        groups.setdefault((platform, hours), []).append(row)
    summaries = []
    for (platform, hours), batch in sorted(groups.items()):
        item = {'platform': platform, 'window_hours': hours, 'posts': len(batch), 'metrics': {}}
        for numerator, denominator, label in [('completions', 'views', 'completion_rate'),
                                               ('follows', 'views', 'follow_rate'),
                                               ('qualified_leads', 'views', 'qualified_lead_rate')]:
            eligible = [r for r in batch if r.get(numerator) is not None and r.get(denominator) is not None and r[denominator] > 0]
            item['metrics'][label] = {
                'weighted_rate': sum(r[numerator] for r in eligible)/sum(r[denominator] for r in eligible) if eligible else None,
                'median_rate': statistics.median(r[numerator]/r[denominator] for r in eligible) if eligible else None,
                'included_posts': len(eligible), 'missing_or_zero_denominator_posts': len(batch)-len(eligible),
            }
        for field in ('views', 'follows', 'qualified_leads'):
            known = [r[field] for r in batch if r.get(field) is not None]
            item[field] = {'known_sum': sum(known) if known else None, 'missing_posts': len(batch)-len(known)}
        summaries.append(item)
    return {'generated_at': now(), 'raw_snapshots': len(rows), 'unique_post_windows': len(latest), 'groups': summaries,
            'note': 'Latest snapshot per post/platform/window; descriptive statistics only. No causal or viral-performance inference.'}


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('init', 'context', 'brief', 'record', 'analyze', 'attach'):
        p = sub.add_parser(name)
        p.add_argument('--workspace', required=True)
        if name == 'record':
            p.add_argument('--kind', choices=REQUIRED, required=True)
            p.add_argument('--input', required=True)
        if name == 'analyze':
            p.add_argument('--output')
        if name == 'brief':
            p.add_argument('--stage', choices=['discover', 'draft', 'produce', 'review'], default='discover')
            p.add_argument('--topic-id')
            p.add_argument('--limit', type=int, default=8)
        if name == 'attach':
            p.add_argument('--topic-id', required=True)
            p.add_argument('--project', required=True)
            p.add_argument('--report', required=True)
    args = parser.parse_args()
    root = Path(args.workspace).resolve()
    if args.command == 'init':
        result = initialize(root)
    elif args.command == 'context':
        result = {key: read(root/(key+'.json')) for key in ('profile', *REQUIRED)}
    elif args.command == 'brief':
        result = brief(root, args.stage, args.topic_id, args.limit)
    elif args.command == 'attach':
        result = attach_production(root, args.topic_id, args.project, args.report)
    elif args.command == 'record':
        result = record(root, args.kind, args.input)
    else:
        result = analyze(root)
        if args.output:
            write(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, TypeError) as e:
        print(json.dumps({'error': str(e)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
