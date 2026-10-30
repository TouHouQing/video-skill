"""Measure the actual edit duration occupied by source material and recordings."""
from __future__ import annotations
import math

SOURCE_ROLES = {'source_page','source_recording','vendor_demo','target_app','terminal_execution'}


def visual_mix(project, shots):
    requirements = project.get('requirements', {})
    defaults = {'source_material_min_ratio': .90, 'recording_min_ratio': .65,
                'max_consecutive_motion_seconds': 3}
    limits = dict(defaults) if project.get('visual_style') == 'source_led' else {}
    configurable = set(defaults) | {'min_distinct_source_assets'}
    limits.update({k: requirements[k] for k in configurable if k in requirements})
    for key in ('source_material_min_ratio','recording_min_ratio'):
        value = limits.get(key)
        if value is not None and (isinstance(value,bool) or not isinstance(value,(int,float))
                                  or not math.isfinite(value) or not 0 <= value <= 1):
            raise ValueError(f'{key} must be a finite ratio between 0 and 1.')
    for key in ('min_distinct_source_assets','max_consecutive_motion_seconds'):
        value = limits.get(key)
        if value is not None and (isinstance(value,bool) or not isinstance(value,(int,float))
                                  or not math.isfinite(value) or value < 0):
            raise ValueError(f'{key} must be finite and nonnegative.')
    total = sum(s['duration'] for s in shots)
    if total <= 0:
        raise ValueError('Visual mix requires a positive edit duration.')
    source_seconds = recording_seconds = motion_run = longest_motion = 0.
    distinct = set()
    segments = []
    for shot in shots:
        duration = shot['duration']
        media = shot.get('media', {})
        rights = media.get('rights', {})
        source = (shot['type'] in ('video','image') and media.get('role') in SOURCE_ROLES
                  and (rights.get('source_url') or media.get('role') in ('target_app','terminal_execution')))
        recorded = bool(source and shot['type'] == 'video' and rights.get('kind') == 'original_capture')
        if source:
            source_seconds += duration
            distinct.add(media.get('source_asset_id') or
                         (rights.get('source_url') if media.get('role') in ('source_page','source_recording') else None) or
                         media.get('sha256') or media.get('path') or media.get('id'))
        if recorded:
            recording_seconds += duration
        motion_run = motion_run + duration if shot['type'] == 'motion' else 0.
        longest_motion = max(longest_motion,motion_run)
        segments.append({'shot_id':shot['id'],'start':shot['start'],'end':shot['end'],
                         'type':shot['type'],'source_material':bool(source),'recording':recorded,
                         'media_id':media.get('id'),'source_url':rights.get('source_url')})
    report = {'duration_seconds':total,'source_material_seconds':source_seconds,
              'recording_seconds':recording_seconds,'source_material_ratio':source_seconds/total,
              'recording_ratio':recording_seconds/total,'distinct_source_assets':len(distinct),
              'longest_consecutive_motion_seconds':longest_motion,'limits':limits,
              'measurement':'Actual allocated shot durations; brief callouts/captions do not change the primary material type. source_asset_id groups crops/recordings of one original; source pages default to URL, other material to SHA.',
              'provenance_scope':'Media metadata and hashes checked separately; this count does not establish editorial relevance or authenticity on its own.',
              'segments':segments}
    checks = {
        'source_material_min_ratio': report['source_material_ratio'],
        'recording_min_ratio': report['recording_ratio'],
        'min_distinct_source_assets': report['distinct_source_assets']}
    failed = [f'{k}: actual {checks[k]:.3f}, required {v:g}' for k,v in limits.items()
              if k in checks and checks[k]+1e-8 < v]
    if 'max_consecutive_motion_seconds' in limits and longest_motion > limits['max_consecutive_motion_seconds']+1e-8:
        failed.append(f'consecutive motion {longest_motion:.3f}s exceeds {limits["max_consecutive_motion_seconds"]:g}s')
    report['passed'] = not failed
    if failed:
        raise ValueError('Source material coverage failed: '+'; '.join(failed)+'. Add relevant recordings/screenshots; do not fill with generated slides.')
    return report
