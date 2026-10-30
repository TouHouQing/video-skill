"""Action-aware rough cuts, dropping recorded loading/idle gaps between operations."""
from pathlib import Path
import json
from media import sha256


def rough_cut(manifest_path):
    path=Path(manifest_path).resolve()
    data=json.loads(path.read_text('utf-8-sig'))
    if data.get('status')!='completed' or not data.get('actions'):
        raise ValueError('Autocut needs a completed browser recording with actual actions.')
    video=Path(data['path'])
    if sha256(video)!=data['sha256']:
        raise ValueError('Recording bytes no longer match the action manifest.')
    windows=[]
    for action in data['actions']:
        if action['action'] in ('wait','hover'):
            continue
        start=max(0,action['start']-.35)
        end=min(data['duration'],action['end']+.8)
        if windows and start<=windows[-1]['source_out']+.15:
            windows[-1]['source_out']=max(windows[-1]['source_out'],end)
            windows[-1]['action_indices'].append(action['index'])
        else:
            windows.append({'source_in':start,'source_out':end,'action_indices':[action['index']]})
    if not windows:
        raise ValueError('No active operations/results to cut; add a real interaction or an assertion.')
    shots=[]
    for i,w in enumerate(windows):
        span=w['source_out']-w['source_in']
        shot={'id':f'auto-{i:02}','type':'video','media_id':'recording',
              'duration':round(span,3),'source_in':w['source_in'],
              'source_out':w['source_out'],'speed':'auto','transition':'cut',
              'recording_actions':w['action_indices']}
        marks=[]
        for action in data['actions']:
            box=action.get('bounding_box')
            if action['index'] not in w['action_indices'] or not box:
                continue
            x=max(0,box['x']/data['width']);y=max(0,box['y']/data['height'])
            width=min(1-x,box['width']/data['width']);height=min(1-y,box['height']/data['height'])
            if width<=0 or height<=0:
                continue
            at=max(0,min(.9,(action['end']-w['source_in'])/span))
            marks.append({'rect':[x,y,width,height],'start':at,'end':min(1,at+.3)})
        if marks:
            shot['highlights']=marks
            x,y,wid,hgt=marks[-1]['rect']
            cw,ch=min(1,max(.55,wid+.14)),min(1,max(.4,hgt+.18))
            cx,cy=max(0,min(1-cw,x+wid/2-cw/2)),max(0,min(1-ch,y+hgt/2-ch/2))
            shot['camera']={'start':[0,0,1,1],'end':[cx,cy,cw,ch]}
        shots.append(shot)
    kept=sum(w['source_out']-w['source_in'] for w in windows)
    return {'status':'rough-cut-plan','media':{'id':'recording','type':'video','path':str(video),
            'recording_manifest':str(path),'rights':{'kind':'original_capture'}},'shots':shots,
            'input_seconds':data['duration'],'selected_seconds':kept,'omitted_seconds':data['duration']-kept,
            'timing_note':data['timing_method'],
            'editorial_note':'Action-window heuristic, not semantic scene understanding. Review that asynchronous results remain visible.'}
