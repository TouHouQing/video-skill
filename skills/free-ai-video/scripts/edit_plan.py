"""Resolve editorial shots onto actual narration time, without silent freeze frames."""
from __future__ import annotations
import math
import re
from media import validate_rights

MODES = ('cards', 'screencast', 'motion', 'montage', 'hybrid')


def positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def rectangle(rect):
    return (isinstance(rect, list) and len(rect) == 4
            and all(isinstance(n, (int, float)) and math.isfinite(n) for n in rect)
            and rect[0] >= 0 and rect[1] >= 0 and rect[2] > 0 and rect[3] > 0
            and rect[0] + rect[2] <= 1.000001 and rect[1] + rect[3] <= 1.000001)


def scene_shots(project, scene):
    if scene.get('shots'):
        return scene['shots']
    if project.get('visual_mode') == 'motion':
        return [{'id': scene['id'] + '-motion', 'type': 'motion', 'duration': 1,
                 'motion': {'layout': 'kinetic', 'words': [scene['headline'].replace('\n', ''), *scene.get('body', [])]}}]
    return []


def validate_edit(project):
    mode = project.get('visual_mode', 'cards')
    if mode not in MODES:
        raise ValueError(f'visual_mode must be one of {MODES}.')
    media = {}
    for item in project.get('media', []):
        if not all(item.get(k) for k in ('id', 'type', 'path')) or item['type'] not in ('image', 'video'):
            raise ValueError('Every media item needs id, type (image/video) and path.')
        if item['id'] in media:
            raise ValueError('Duplicate media ID.')
        validate_rights(item.get('rights', {}))
        if item['rights']['kind'] == 'source_excerpt' and item['type'] != 'image':
            raise ValueError('source_excerpt is for short text/image evidence, not third-party video reuse.')
        media[item['id']] = item
    ids, kinds, asset_count = set(), set(), 0
    for scene in project['scenes']:
        shots = scene_shots(project, scene)
        if mode != 'cards' and not shots:
            raise ValueError(f'Add actual shots to scene {scene["id"]}; do not silently substitute cards.')
        for shot in shots:
            if not shot.get('id') or shot['id'] in ids:
                raise ValueError('Each shot needs a globally unique ID.')
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', shot['id']):
                raise ValueError('Shot IDs must be safe ASCII filenames (letters, digits, underscore, hyphen).')
            ids.add(shot['id'])
            kind = shot.get('type')
            if kind not in ('video', 'image', 'motion') or not positive(shot.get('duration', 1)):
                raise ValueError('Shot type or positive duration weight is invalid.')
            kinds.add(kind)
            if shot.get('transition', 'cut') not in ('cut', 'dissolve', 'wipe'):
                raise ValueError('Unsupported transition.')
            if shot.get('fit', 'contain') not in ('contain', 'cover'):
                raise ValueError('fit must be contain or cover.')
            if shot.get('presentation','standard') not in ('standard','full_bleed'):
                raise ValueError('presentation must be standard or full_bleed.')
            if 'callout' in shot:
                if not isinstance(shot['callout'],str) or not 1 <= len(shot['callout']) <= 64:
                    raise ValueError('A source-footage callout must be a short nonempty string.')
                position=shot.get('callout_y',.12)
                if not isinstance(position,(int,float)) or not .08 <= position <= .65:
                    raise ValueError('callout_y must stay between .08 and .65 of the frame, clear of captions.')
            if kind in ('video', 'image'):
                asset = media.get(shot.get('media_id'))
                if not asset or asset['type'] != kind:
                    raise ValueError('Shot media reference is missing or has the wrong type.')
                asset_count += 1
            if kind == 'motion':
                motion = shot.get('motion', {})
                layout = motion.get('layout', 'kinetic')
                if layout not in ('kinetic', 'flow', 'compare', 'bars', 'table'):
                    raise ValueError('Unsupported motion layout.')
                if layout in ('bars', 'table'):
                    rows = motion.get('rows', [])
                    if not motion.get('title') or not 2 <= len(rows) <= 4 or any(not row.get('label') for row in rows):
                        raise ValueError('Data graphics need a title and 2–4 labelled rows for portrait readability.')
                    if layout == 'bars':
                        values = [row.get('value') for row in rows]
                        if any(not isinstance(v, (int,float)) or isinstance(v,bool) or not math.isfinite(v) or v < 0 for v in values):
                            raise ValueError('Chart values must be finite nonnegative numbers.')
                        maximum = motion.get('max_value')
                        if not positive(maximum) or maximum < max(values) or motion.get('min_value',0) != 0:
                            raise ValueError('Comparison bars require a zero baseline and a maximum covering all values.')
                    else:
                        columns = motion.get('columns', [])
                        if not 1 <= len(columns) <= 3 or not all(isinstance(c,str) and c.strip() for c in columns):
                            raise ValueError('Tables need 1–3 named value columns.')
                        if any(len(row.get('cells',[])) != len(columns) or any(not isinstance(c,str) or not c.strip() for c in row.get('cells',[])) for row in rows):
                            raise ValueError('Each table row must provide a nonempty string for every column.')
                else:
                    words = motion.get('words') or motion.get('nodes')
                    if not words or not all(isinstance(w, str) and w.strip() for w in words):
                        raise ValueError('Motion shots require nonempty words or nodes.')
            if kind == 'video':
                start = shot.get('source_in', 0)
                end = shot.get('source_out')
                if not isinstance(start, (int, float)) or not math.isfinite(start) or start < 0:
                    raise ValueError('source_in must be finite and nonnegative.')
                if end is not None and (not positive(end) or end <= start):
                    raise ValueError('source_out must be after source_in.')
                if shot.get('speed', 'auto') != 'auto' and not positive(shot['speed']):
                    raise ValueError('speed must be auto or a positive number.')
            camera = shot.get('camera', {})
            for key in ('start', 'end'):
                if key in camera and not rectangle(camera[key]):
                    raise ValueError('Camera rectangles must stay inside normalized source coordinates.')
            for mark in shot.get('highlights', []):
                if not rectangle(mark.get('rect')):
                    raise ValueError('Highlight rect is invalid.')
                if not 0 <= mark.get('start', 0) < mark.get('end', 1) <= 1:
                    raise ValueError('Highlight start/end use 0–1 shot progress.')
    if mode == 'screencast' and 'video' not in kinds:
        raise ValueError('screencast mode needs an actual video recording.')
    if mode == 'montage' and asset_count < 2:
        raise ValueError('montage mode needs at least two media shots.')
    if mode == 'hybrid' and len(kinds) < 2:
        raise ValueError('hybrid mode needs at least two visual types.')
    requirements=project.get('requirements',{})
    used_ids={s.get('media_id') for scene in project['scenes'] for s in scene_shots(project,scene)}
    used=[m for mid,m in media.items() if mid in used_ids]
    if requirements.get('real_operation') and not any(m.get('role') in ('target_app','terminal_execution')
                                                     and m['type']=='video' and m['rights']['kind']=='original_capture' for m in used):
        raise ValueError('Real operation requires target application or terminal execution footage; a custom result viewer does not satisfy it.')
    required_sources=requirements.get('stock_montage_sources',0)
    distinct={m['rights'].get('source_url') for m in used if m.get('role')=='b_roll'
              and m['type']=='video' and m['rights']['kind'] in ('licensed','public_domain')}
    distinct.discard(None)
    if len(distinct)<required_sources:
        raise ValueError('Montage requires distinct footage sources; recutting the same viewer is insufficient.')


def plan(project, clocks, inventory):
    result = []
    for scene, clock in zip(project['scenes'], clocks, strict=True):
        shots = scene_shots(project, scene)
        total_weight = sum(s.get('duration', 1) for s in shots)
        cursor = clock['start']
        for index, shot in enumerate(shots):
            end = clock['start'] + clock['duration'] if index == len(shots)-1 else cursor + clock['duration'] * shot.get('duration', 1) / total_weight
            item = {**shot, 'scene_id': scene['id'], 'scene_headline': scene['headline'],
                    'start': cursor, 'end': end, 'duration': end-cursor}
            if shot['type'] in ('video', 'image'):
                item['media'] = inventory[shot['media_id']]
            if shot['type'] == 'video':
                native = item['media']['duration']
                src_in, src_out = shot.get('source_in', 0), shot.get('source_out', native)
                if src_out > native + .05 or src_in >= native:
                    raise ValueError(f'Shot {shot["id"]} requests media beyond its end.')
                selected = min(src_out, native) - src_in
                speed = selected / item['duration'] if shot.get('speed', 'auto') == 'auto' else shot['speed']
                if not .25 <= speed <= 4:
                    raise ValueError(f'Shot {shot["id"]} needs {speed:.2f}x speed; add footage or adjust shot weights (allowed .25–4x).')
                if selected / speed + .045 < item['duration']:
                    raise ValueError(f'Shot {shot["id"]} is too short; refusing to freeze or loop a genuine demonstration.')
                item.update(source_in=src_in, source_out=min(src_out, native), effective_speed=speed)
            result.append(item)
            cursor = end
    return result
