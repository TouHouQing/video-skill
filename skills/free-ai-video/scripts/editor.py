"""Narration-driven local editor for real clips, motion graphics and montage."""
from __future__ import annotations
import math
import os
from pathlib import Path
import subprocess
import time
from PIL import Image, ImageDraw, ImageOps, ImageFilter
from compose import font, wrap, subtitle_layer, mix_audio, INK, PAPER, MINT
from edit_plan import plan
from motion import frame as motion_frame, fitted
from runtime import emit, ffmpeg, run, save_json

W,H = 720,1280


class Decoder:
    def __init__(self, shot, fps, log_dir):
        media = shot['media']
        scale = min(1, 1440/max(media['width'],media['height']))
        self.size = (max(2,int(media['width']*scale)//2*2),max(2,int(media['height']*scale)//2*2))
        self.bytes = self.size[0]*self.size[1]*3
        self.log = Path(log_dir)/(shot['id']+'-decode.log')
        self.errors = self.log.open('wb')
        options = {'stdout':subprocess.PIPE,'stdin':subprocess.DEVNULL,'stderr':self.errors}
        if os.name == 'nt':
            options['creationflags'] = subprocess.CREATE_NO_WINDOW
        selected = shot['source_out']-shot['source_in']
        self.process = subprocess.Popen([ffmpeg(),'-hide_banner','-loglevel','error',
            '-ss',str(shot['source_in']),'-t',str(selected),'-i',media['path'],'-an',
            '-vf',f'setpts=(PTS-STARTPTS)/{shot["effective_speed"]:.10f},'
                  f'tpad=stop_mode=clone:stop_duration={1/fps:.10f},fps={fps},scale={self.size[0]}:{self.size[1]}',
            '-pix_fmt','rgb24','-f','rawvideo','pipe:1'],**options)

    def read(self):
        data = self.process.stdout.read(self.bytes)
        if len(data) != self.bytes:
            raise RuntimeError('Media ended before its allocated shot time; adjust cuts/speed. '+self.log.read_text('utf-8',errors='replace')[-500:])
        return Image.frombytes('RGB',self.size,data)

    def close(self):
        if self.process.poll() is None:
            self.process.kill()
        self.process.stdout.close()
        self.process.wait(timeout=10)
        self.errors.close()


def place_media(source, shot, progress):
    result = Image.new('RGB',(W,H),'#101D1A')
    camera = shot.get('camera',{})
    start = camera.get('start',[0,0,1,1])
    end = camera.get('end',start)
    p = progress*progress*(3-2*progress)
    rect = [a+(b-a)*p for a,b in zip(start,end)]
    x,y,cw,ch = rect
    left,top = int(x*source.width),int(y*source.height)
    right,bottom = max(left+1,round((x+cw)*source.width)),max(top+1,round((y+ch)*source.height))
    crop = source.crop((left,top,right,bottom))
    # The image occupies the shot, rather than being a tiny screenshot inside a slide.
    cinema=shot.get('presentation')=='full_bleed'
    area = (W,H) if cinema else (W,900)
    origin_y=0 if cinema else 180
    cover = shot.get('fit','contain') == 'cover'
    if cover:
        fitted_image = ImageOps.fit(crop,area,Image.Resampling.LANCZOS)
        factor = max(area[0]/crop.width,area[1]/crop.height)
        offset_x,offset_y = (W-crop.width*factor)/2,origin_y+(area[1]-crop.height*factor)/2
        result.paste(fitted_image,(0,origin_y))
    else:
        fitted_image = ImageOps.contain(crop,area,Image.Resampling.LANCZOS)
        factor = min(area[0]/crop.width,area[1]/crop.height)
        offset_x,offset_y = (W-fitted_image.width)/2,origin_y+(area[1]-fitted_image.height)/2
        if cinema:
            result=ImageOps.fit(crop,(W,H),Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(22))
            result=Image.blend(result,Image.new('RGB',(W,H),'#061013'),.45)
        result.paste(fitted_image,(round(offset_x),round(offset_y)))
    overlay = Image.new('RGBA',(W,H),(0,0,0,0))
    d = ImageDraw.Draw(overlay)
    for mark in shot.get('highlights',[]):
        if mark.get('start',0) <= progress <= mark.get('end',1):
            mx,my,mw,mh = mark['rect']
            box = (max(4,offset_x+(mx*source.width-left)*factor),
                   max(4 if cinema else 184,offset_y+(my*source.height-top)*factor),
                   min(716,offset_x+((mx+mw)*source.width-left)*factor),
                   min(H-4 if cinema else 1076,offset_y+((my+mh)*source.height-top)*factor))
            if box[2] > box[0] and box[3] > box[1]:
                pulse = int(135+100*(.5+.5*math.sin(progress*16)))
                d.rounded_rectangle(box,12,outline=(213,250,115,pulse),width=5)
                if mark.get('label'):
                    text = mark['label']
                    face = font(23,True)
                    width = face.getlength(text)+24
                    lx,ly = min(box[0],W-width-8),max(185,box[1]-38)
                    d.rounded_rectangle((lx,ly,lx+width,ly+34),7,fill=MINT)
                    d.text((lx+12,ly+2),text,font=face,fill=INK)
    return Image.alpha_composite(result.convert('RGBA'),overlay).convert('RGB')


def decorations(image, project, shot, timestamp, total, caption=None, draft=False):
    if shot.get('presentation')=='full_bleed':
        overlay=Image.new('RGBA',(W,H),(0,0,0,0));d=ImageDraw.Draw(overlay)
        label=shot.get('label','')
        if label:
            width=min(650,font(22,True).getlength(label)+36)
            d.rounded_rectangle((28,36,28+width,81),12,fill=(5,13,15,205))
            d.text((46,43),label,font=font(22,True),fill='#F4F5EF')
        if shot.get('callout'):
            lines=wrap(shot['callout'],624,font(35,True))
            if len(lines)>2:raise ValueError('Source footage callout exceeds two lines.')
            top=round(H*shot.get('callout_y',.12))
            d.rounded_rectangle((28,top-12,692,top+len(lines)*46+12),14,fill=(4,16,19,205))
            for line in lines:
                d.text((48,top),line,font=font(35,True),fill=MINT)
                top+=46
        if caption:
            lines=wrap(caption,620,font(32,True))
            if len(lines)>2:raise ValueError('Full-screen caption exceeds two lines.')
            top=1080
            for y in range(top-28,1238):
                alpha=int(145*min(1,(y-top+28)/50))
                d.line((0,y,W,y),fill=(0,0,0,alpha))
            for line in lines:
                face=font(32,True);x=(W-face.getlength(line))/2
                d.text((x,top),line,font=face,fill='#FFFFFF',stroke_width=2,stroke_fill='#07100F')
                top+=47
        if draft:d.text((30,1200),'镜头草稿',font=font(22,True),fill=MINT)
        return Image.alpha_composite(image.convert('RGBA'),overlay).convert('RGB')
    d = ImageDraw.Draw(image)
    d.rectangle((0,0,720,178),fill=INK)
    d.text((40,37),project.get('brand','AI 工具观察'),font=font(23,True),fill='#B8CCC0')
    label = shot.get('label') or {'video':'实际操作','image':'来源画面','motion':'动态解说'}[shot['type']]
    d.text((470,39),label[:10],font=font(19),fill=MINT)
    fitted(d,shot.get('headline',shot['scene_headline']).replace('\n',' '),(40,85,640,88),size=35,max_lines=2)
    if caption:
        layer = subtitle_layer(caption)
        image.paste(layer,(0,1090),layer)
    d.text((40,1212),project.get('brand','AI 工具观察'),font=font(17),fill='#9AB1A6')
    d.rectangle((40,1254,680,1258),fill='#456456')
    d.rectangle((40,1254,40+int(640*min(1,timestamp/max(total,.1))),1258),fill=MINT)
    if draft:
        d.rounded_rectangle((465,1170,680,1205),9,fill='#FFD897')
        d.text((481,1172),'镜头草稿 · 非成片',font=font(21,True),fill=INK)
    return image


def extract_frame(media, at, destination):
    run([ffmpeg(),'-y','-hide_banner','-loglevel','error','-ss',str(at),'-i',media,
         '-frames:v','1',destination],timeout=60)
    return Image.open(destination).convert('RGB')


def draft(project, inventory, output):
    """Static review only: no TTS, no video encoding, no hidden approval."""
    output = Path(output)
    output.mkdir(parents=True,exist_ok=True)
    clocks, cursor = [],0
    for scene in project['scenes']:
        duration = scene.get('planned_duration', max(3,len(scene['narration'])/4.8))
        clocks.append({'start':cursor,'duration':duration})
        cursor += duration
    shots = plan(project,clocks,inventory)
    from visual_mix import visual_mix
    save_json(output/'visual-mix.json',visual_mix(project,shots))
    frames=[]
    for index, shot in enumerate(shots):
        if shot['type'] == 'motion':
            image = motion_frame(shot['motion'],shot['duration']*.4,shot['duration'])
        elif shot['type'] == 'image':
            image = place_media(Image.open(shot['media']['path']).convert('RGB'),shot,.4)
        else:
            image = place_media(extract_frame(shot['media']['path'],shot['source_in']+.4*(shot['source_out']-shot['source_in']),
                                              output/f'input-{index:02}.png'),shot,.4)
        image=decorations(image,project,shot,shot['start']+.4*shot['duration'],cursor,draft=True)
        path=output/f'shot-{index:02}.jpg'
        image.resize((1080,1920),Image.Resampling.LANCZOS).save(path,quality=93)
        frames.append(path)
    contact_sheet(frames,output/'分镜预览.jpg')
    save_json(output/'edit-plan.json',{'status':'draft','timing':'planned, before narration', 'shots':shots})
    save_json(output/'project.json',project)
    return {'status':'draft','audio_generated':False,'video_generated':False,'shots':len(shots),'output':str(output)}


def contact_sheet(frames, path):
    board=Image.new('RGB',(1080,640*math.ceil(len(frames)/3)),'#DCE3D5')
    for i, sample in enumerate(frames):
        with Image.open(sample) as picture:
            board.paste(picture.resize((360,640),Image.Resampling.LANCZOS),((i%3)*360,(i//3)*640))
    board.save(path,quality=94)


def render(project,voice,inventory,output):
    output=Path(output)
    assets=output/'assets'
    assets.mkdir(parents=True,exist_ok=True)
    shots=plan(project,voice['timeline'],inventory)
    from visual_mix import visual_mix
    save_json(output/'visual-mix.json',visual_mix(project,shots))
    save_json(output/'edit-plan.json',{'timing':'actual scene narration; proportional phrase captions',
              'frame_boundary_padding_max_seconds':1/project.get('fps',24),'shots':shots})
    save_json(output/'media-manifest.json',{'assets':list(inventory.values()),
              'rights_verification':'Declarations recorded; editorial license verification is still required.'})
    fps=project.get('fps',24)
    width,height=project.get('width',1080),project.get('height',1920)
    soundtrack=assets/'soundtrack.wav'
    mix_audio(voice['narration'],soundtrack,voice['duration'],project.get('music',True))
    video=output/'final.mp4'
    command=[ffmpeg(),'-y','-hide_banner','-loglevel','warning','-f','rawvideo','-pix_fmt','rgb24',
             '-s',f'{W}x{H}','-r',str(fps),'-i','pipe:0','-i',str(soundtrack),
             '-vf',f'scale={width}:{height}:flags=lanczos','-c:v','libx264','-preset','veryfast','-crf','20',
             '-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart','-shortest',str(video)]
    options={'stdin':subprocess.PIPE,'stdout':subprocess.DEVNULL}
    if os.name=='nt':
        options['creationflags']=subprocess.CREATE_NO_WINDOW
    shot_index,subtitle_index=0,0
    decoder,source,previous,last_base=None,None,None,None
    frames=[]
    started=time.monotonic()
    with (assets/'render.log').open('wb') as errors:
        process=subprocess.Popen(command,stderr=errors,**options)
        try:
            for number in range(math.ceil(voice['duration']*fps)):
                timestamp=number/fps
                changed=number==0
                while shot_index+1<len(shots) and timestamp>=shots[shot_index+1]['start']-1e-8:
                    shot_index+=1;changed=True
                shot=shots[shot_index]
                elapsed=timestamp-shot['start']
                progress=max(0,min(1,elapsed/shot['duration']))
                if changed:
                    previous=last_base
                    if decoder:
                        decoder.close();decoder=None
                    if shot['type']=='video':
                        decoder=Decoder(shot,fps,assets)
                    elif shot['type']=='image':
                        source=Image.open(shot['media']['path']).convert('RGB')
                if shot['type']=='motion':
                    base=motion_frame(shot['motion'],elapsed,shot['duration'])
                else:
                    raw=decoder.read() if decoder else source
                    base=place_media(raw,shot,progress)
                transition=shot.get('transition','cut')
                seconds=min(.22,shot['duration']/3)
                if previous is not None and elapsed<seconds and transition!='cut':
                    fraction=max(0,min(1,elapsed/seconds))
                    if transition=='dissolve':
                        base=Image.blend(previous,base,fraction)
                    else:
                        boundary=round(W*fraction)
                        merged=previous.copy();merged.paste(base.crop((0,0,boundary,H)),(0,0));base=merged
                last_base=base.copy()
                while subtitle_index+1<len(voice['subtitles']) and timestamp>=voice['subtitles'][subtitle_index]['end']:
                    subtitle_index+=1
                sub=voice['subtitles'][subtitle_index]
                caption=sub['text'] if sub['start']<=timestamp<sub['end'] else None
                frame=decorations(base,project,shot,timestamp,voice['duration'],caption)
                process.stdin.write(frame.tobytes())
                if (number+1)%(fps*5)==0:
                    emit('edit_render',percent=round(100*(number+1)/(voice['duration']*fps)),elapsed_seconds=round(time.monotonic()-started))
            process.stdin.close()
            if process.wait(timeout=180):
                raise RuntimeError((assets/'render.log').read_text('utf-8',errors='replace')[-1800:])
        except Exception:
            if process.poll() is None:
                process.kill()
            process.wait()
            raise
        finally:
            if decoder:
                decoder.close()
    for index,shot in enumerate(shots):
        path=assets/f'edited-{index:02}.jpg'
        extract_frame(video,shot['start']+min(1,shot['duration']/2),path)
        frames.append(path)
    contact_sheet(frames,output/'contact-sheet.jpg')
    with Image.open(frames[0]) as cover:
        cover.save(output/'cover.png')
    return video,frames
