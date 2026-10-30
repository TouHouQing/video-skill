"""Connect channel preferences, preflight evidence and local production records."""
from __future__ import annotations

from datetime import datetime, timezone
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def ops_module():
    path = ROOT.parent/'ai-content-ops/scripts/content_ops.py'
    spec = importlib.util.spec_from_file_location('video_content_ops', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_project(path):
    path = Path(path).resolve()
    project = json.loads(path.read_text('utf-8-sig'))
    trace = {'project_path': str(path), 'input_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'profile_path': None, 'defaults_applied': []}
    if project.get('channel_dir'):
        channel = Path(project['channel_dir'])
        if not channel.is_absolute():
            channel = path.parent/channel
        channel = channel.resolve()
        profile_path = channel/'profile.json'
        profile = json.loads(profile_path.read_text('utf-8-sig'))
        preferences = profile.get('preferences', {})
        project['channel_dir'] = str(channel)
        trace.update(profile_path=str(profile_path), profile_sha256=hashlib.sha256(profile_path.read_bytes()).hexdigest())
        defaults = {key: preferences[key] for key in ('voice_mode', 'voice_profile') if key in preferences}
        if project.get('content_type') == 'ai_news' and project.get('visual_mode', 'cards') != 'cards':
            if preferences.get('visual_style'):
                defaults['visual_style'] = preferences['visual_style']
        for key, value in defaults.items():
            if key not in project:
                project[key] = copy.deepcopy(value)
                trace['defaults_applied'].append(key)
        if project.get('visual_style') == 'source_led':
            requirements = project.setdefault('requirements', {})
            mapping = {'source_material_ratio': 'source_material_min_ratio', 'recording_ratio': 'recording_min_ratio',
                       'max_standalone_motion_seconds': 'max_consecutive_motion_seconds'}
            for key, value in preferences.get('source_led_targets', {}).items():
                if key in mapping and mapping[key] not in requirements:
                    requirements[mapping[key]] = value
                    trace['defaults_applied'].append('requirements.'+mapping[key])
    trace['effective_sha256'] = hashlib.sha256(json.dumps(project, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return project, trace


def prepare_inputs(path, stage='produce'):
    if stage not in ('draft', 'produce'):
        raise ValueError('Preflight stage must be draft or produce.')
    from factory import validate
    from newsroom import load_research
    from edit_plan import scene_shots
    from media import resolve_media
    path = Path(path).resolve()
    project, trace = load_project(path)
    validate(project)
    if stage == 'produce' and project.get('approval_status') in ('draft', 'awaiting_user'):
        raise ValueError('This project is awaiting user approval. Do not produce it; update approval_status only after explicit consent.')
    research = load_research(project, path)
    warnings = []
    if research:
        try:
            checked = datetime.fromisoformat(research[1]['recorded_at'].replace('Z', '+00:00'))
            if checked.tzinfo is None:
                warnings.append('Research timestamp has no timezone. Verify the original local date before treating it as recent news.')
            else:
                age = (datetime.now(timezone.utc)-checked).total_seconds()/3600
                if age > 72 or age < -2:
                    warnings.append('Research is older than 72 hours or dated in the future. Check event wording and re-verify current prices before posting.')
        except (ValueError, TypeError):
            warnings.append('Research time cannot be parsed; verify its actual date before treating this as recent news.')
    inventory = resolve_media(project, path.parent) if stage == 'produce' else {}
    declared = {item['id']: item for item in project.get('media', [])}
    evidence = project.get('evidence_map', [])
    if not isinstance(evidence, list):
        raise ValueError('evidence_map must be a list of scene mappings.')
    mapping = {}
    for row in evidence:
        if not isinstance(row, dict) or row.get('scene_id') in mapping or not row.get('scene_id'):
            raise ValueError('evidence_map needs unique scene_id records.')
        mapping[row['scene_id']] = row
    scene_ids = {scene['id'] for scene in project['scenes']}
    if set(mapping)-scene_ids:
        raise ValueError('evidence_map references an unknown scene.')
    if not evidence:
        warnings.append('No evidence_map: legacy project accepted. Review narration-to-material matching before TTS for new jobs.')
    material_map = []
    for scene in project['scenes']:
        used = list(dict.fromkeys(shot['media_id'] for shot in scene_shots(project, scene) if shot.get('media_id')))
        row = mapping.get(scene['id'])
        if evidence and (not row or not row.get('viewer_focus')):
            raise ValueError('Every scene needs an evidence_map entry and viewer_focus when the map is provided.')
        if row and (set(row.get('source_ids', []))-set(scene.get('source_ids', [])) or set(row.get('media_ids', []))-set(used)):
            raise ValueError('Evidence mapping must reference sources/media actually used by that scene.')
        if row and (set(row.get('media_ids', [])) != set(used) or set(row.get('source_ids', [])) != set(scene.get('source_ids', []))):
            raise ValueError('Evidence mapping is stale: its sources/media differ from the scene.')
        material_map.append({'scene_id': scene['id'], 'narration': scene['narration'], 'source_ids': scene.get('source_ids', []),
                             'media': [{key: declared[mid].get(key) for key in ('id', 'path', 'type', 'role')} for mid in used],
                             'viewer_focus': row.get('viewer_focus') if row else None,
                             'evidence_limit': row.get('evidence_limit') if row else None})
    if project.get('channel_dir') and project.get('topic_id'):
        # Detect a broken handoff before spending time on rendering.
        ops_module().brief(Path(project['channel_dir']), 'produce', project['topic_id'])
    captures = [source['id'] for source in project['sources']
                if source.get('capture', project.get('visual_mode', 'cards') == 'cards') is not False]
    report = {'delivery_stage': stage, 'technical_inputs_ready': True, 'settings': trace, 'warnings': warnings,
              'sources_to_capture': captures, 'scene_material_map': material_map,
              'research_path': str(research[0]) if research else None,
              'editorial_review': 'Codex must assess the hook, factual support, footage relevance and pacing; schema validity does not certify them.'}
    return report, project, inventory, research


def sync_production(project, project_path, report_path):
    if not (project.get('channel_dir') and project.get('topic_id')):
        return {'status': 'not_linked', 'reason': 'No channel_dir/topic_id on this project.'}
    return ops_module().attach_production(Path(project['channel_dir']), project['topic_id'], project_path, report_path)
