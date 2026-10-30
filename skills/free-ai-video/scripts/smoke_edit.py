"""Offline technical fixtures only, not a topical video or a product demonstration."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import wave
import numpy as np
from PIL import Image, ImageChops, ImageStat
from record import record_browser
from autocut import rough_cut
from media import resolve_media, sha256
from editor import render, draft, extract_frame
from factory import validate, verify, produce
from runtime import save_json


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workdir',required=True)
    args=parser.parse_args()
    root=Path(args.workdir).resolve();root.mkdir(parents=True,exist_ok=True)
    # This page performs a real local sort. It never impersonates MarkItDown or another product.
    html='''<!doctype html><meta charset="utf-8"><style>
    body{margin:0;background:#eff4eb;color:#142d2a;font:26px "Microsoft YaHei",sans-serif;padding:48px}
    h1{font-size:44px}small{font-size:20px}textarea{box-sizing:border-box;width:100%;height:270px;font:30px monospace;padding:20px}
    button{background:#d5fa73;color:#142d2a;font:30px "Microsoft YaHei";padding:16px 25px;margin:25px 0;border:0;border-radius:12px}
    #result{font-size:46px;background:#fff;min-height:120px;padding:30px;border-radius:20px}</style>
    <small>仅用于录屏与剪辑功能验证</small><h1>真实操作测试台</h1>
    <p>输入数字，点击按钮，在本地执行排序。</p><textarea id="input">9, 3, 6</textarea>
    <button id="sort">执行排序</button><div id="result">等待操作</div>
    <p>这不是 MarkItDown，也不是正式选题视频。</p>
    <script>document.querySelector('#sort').onclick=()=>{document.querySelector('#result').textContent=
    document.querySelector('#input').value.split(',').map(Number).sort((a,b)=>a-b).join(' → ')};</script>'''
    (root/'fixture.html').write_text(html,'utf-8')
    recording={'url':'fixture.html','viewport':{'width':720,'height':1100},'lead_in':.5,'tail':.7,
               'label':'本地排序测试台的真实操作',
               'steps':[{'action':'fill','selector':'#input','text':'9, 3, 6','pause':.4},
                        {'action':'wait','seconds':2,'pause':0},
                        {'action':'click','selector':'#sort','pause':.7},
                        {'action':'assert_text','selector':'#result','text':'3 → 6 → 9','pause':.6}]}
    save_json(root/'recording.json',recording)
    evidence=record_browser(root/'recording.json',root/'capture.mp4')
    cuts=rough_cut(root/'capture.recording.json');save_json(root/'rough-cut.json',cuts)
    assert evidence['status']=='completed' and len(evidence['actions'])==4
    assert evidence['sha256']==sha256(root/'capture.mp4')
    assert cuts['omitted_seconds']>.5
    source_image=Path(evidence['actions'][-1]['screenshot'])
    base={'title':'技术功能测试片段','angle':'仅验证录屏和渲染，不作选题成片', 'brand':'功能测试 · 非正式成片',
          'width':360,'height':640,'fps':12,'music':False,
          'sources':[{'id':'docs','url':'https://playwright.dev/python/docs/videos','label':'录屏文档',
                      'claims':['浏览器可以保存实际录制视频'],'capture':False}],
          'media':[cuts['media'],{'id':'result','type':'image','path':str(source_image),'rights':{'kind':'owned'}}],
          'scenes':[]}
    end=evidence['duration']
    for i in range(3):
        base['scenes'].append({'id':f'scene-{i}','kind':'evidence','headline':['实际点击与结果','连续动态图形','素材裁切与推近'][i],
                               'narration':'这是功能测试。','source_ids':['docs'],'planned_duration':2,'shots':[]})
    duration=6
    rate=24000
    samples=(np.sin(2*np.pi*330*np.arange(duration*rate)/rate)*.08*32767).astype('<i2')
    audio=root/'test-tone.wav'
    with wave.open(str(audio),'wb') as f:
        f.setparams((1,2,rate,0,'NONE','not compressed'));f.writeframes(samples.tobytes())
    voice={'narration':str(audio),'duration':duration,
           'timeline':[{'start':i*2,'duration':2} for i in range(3)],
           'subtitles':[{'start':i*2,'end':i*2+2,'text':'仅用于技术验证'} for i in range(3)]}
    checks={}
    for mode in ('screencast','motion','montage','hybrid'):
        project=json.loads(json.dumps(base));project['visual_mode']=mode
        for i,scene in enumerate(project['scenes']):
            kind={'screencast':'video','motion':'motion','montage':('video' if i==0 else 'image'),
                  'hybrid':('video','motion','image')[i]}[mode]
            shot={'id':f'{mode}-{i}','type':kind,'duration':1,'transition':('cut','dissolve','wipe')[i]}
            if kind=='video':
                shot.update(media_id='recording',source_in=max(0,end-3.5),source_out=end,speed='auto',
                            highlights=[{'rect':[.06,.53,.88,.16],'start':.2,'end':.9,'label':'实际结果'}])
            elif kind=='image':
                shot.update(media_id='result',camera={'start':[0,0,1,1],'end':[.04,.04,.92,.92]})
            else:
                shot['motion']={'layout':('kinetic','flow','compare')[i], 'words':['真实操作','核对结果','自动剪辑']}
            scene['shots']=[shot]
        validate(project)
        inventory=resolve_media(project,root)
        out=root/mode;(out/'assets').mkdir(parents=True,exist_ok=True)
        video,_=render(project,voice,inventory,out)
        quality=verify(video,out/'verification.json',duration,360)
        a=extract_frame(video,.5,out/'motion-a.png');b=extract_frame(video,1.5,out/'motion-b.png')
        difference=sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)
        assert difference>1, f'{mode}: no observable moving picture'
        checks[mode]={'verification':quality,'frame_difference':difference}
        save_json(out/'project.json',project)
        if mode=='hybrid':
            preview=draft(project,inventory,root/'draft-only')
            assert not list((root/'draft-only').glob('*.mp4')) and not preview['audio_generated']
            # One complete factory dispatch with Chinese local speech and native 1080p output.
            project.update(width=1080,height=1920,fps=24,voice_mode='local',approval_status='approved')
            save_json(root/'integration-project.json',project)
            full=produce(root/'integration-project.json',root/'factory-integration')
            checks['factory_integration']={'status':full['status'],'visual_mode':full['visual_mode'],
                                          'verification':full['verification'],'paid_api_cost':full['paid_api_cost']}
    automatic=json.loads((root/'hybrid/project.json').read_text('utf-8'))
    cuts=rough_cut(root/'capture.recording.json')
    automatic['scenes'][0]['shots']=[cuts['shots'][0]]
    automatic['scenes'][2]['shots']=[{**cuts['shots'][-1],'id':'last-action'}]
    validate(automatic)
    auto_out=root/'autocut-integration'
    auto_video,_=render(automatic,voice,resolve_media(automatic,root),auto_out)
    checks['automatic_action_cut']={'verification':verify(auto_video,auto_out/'verification.json',duration,360),
                                   'selected_shots':len(cuts['shots']),'omitted_seconds':cuts['omitted_seconds'],
                                   'automatic_camera_and_highlights':True}
    save_json(root/'smoke-report.json',{'status':'passed','fixture_only':True,'checks':checks,
              'recording':{'duration':evidence['duration'],'completed_actions':len(evidence['actions']),
                           'rough_cut_omitted_seconds':cuts['omitted_seconds']},
              'draft_only_verified':True,'named_window_capture':'Implemented, not exercised in this headless fixture.'})
    print(json.dumps({'status':'passed','report':str(root/'smoke-report.json')},ensure_ascii=False))


if __name__=='__main__':
    main()
