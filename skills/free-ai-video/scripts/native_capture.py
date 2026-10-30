"""Capture one observed native Windows window with PrintWindow, including occluded regions."""
from __future__ import annotations
from datetime import datetime,timezone
import ctypes
import math
import os
from pathlib import Path
import subprocess
import time
from PIL import Image
from media import sha256,probe
from runtime import ffmpeg,save_json,emit


def find_window(title):
    import win32gui
    matches=[]
    def each(hwnd,_):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd)==title:matches.append(hwnd)
    win32gui.EnumWindows(each,None)
    if len(matches)!=1:raise ValueError(f'Expected one exact native window for {title!r}, found {len(matches)}.')
    return matches[0]


class WindowCapture:
    def __init__(self,hwnd):
        import win32gui,win32ui
        self.gui=win32gui;self.hwnd=hwnd
        left,top,right,bottom=win32gui.GetWindowRect(hwnd)
        self.size=((right-left)//2*2,(bottom-top)//2*2)
        self.dc=win32gui.GetWindowDC(hwnd)
        self.source=win32ui.CreateDCFromHandle(self.dc)
        self.memory=self.source.CreateCompatibleDC()
        self.bitmap=win32ui.CreateBitmap();self.bitmap.CreateCompatibleBitmap(self.source,*self.size)
        self.memory.SelectObject(self.bitmap)
    def frame(self):
        if not ctypes.windll.user32.PrintWindow(self.hwnd,self.memory.GetSafeHdc(),2):
            raise RuntimeError('Native application window capture failed.')
        return Image.frombuffer('RGB',self.size,self.bitmap.GetBitmapBits(True),'raw','BGRX',0,1)
    def close(self):
        for operation in (lambda:self.gui.DeleteObject(self.bitmap.GetHandle()),self.memory.DeleteDC,self.source.DeleteDC,
                          lambda:self.gui.ReleaseDC(self.hwnd,self.dc)):
            try:operation()
            except Exception:pass # A closed target window must not mask the original capture error.


def record_native(title,seconds,output,fps=12,ready_callback=None,tick_callback=None):
    import win32gui,win32process
    if os.name!='nt' or not 1<=seconds<=120 or fps not in (12,24):
        raise ValueError('Native capture requires Windows, 1–120 seconds and 12/24 fps.')
    hwnd=find_window(title)
    capture=WindowCapture(hwnd)
    out=Path(output).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    record={'status':'recording','kind':'native-application-window','capture_method':'PrintWindow/PW_RENDERFULLCONTENT',
            'title':title,'hwnd':hwnd,'pid':win32process.GetWindowThreadProcessId(hwnd)[1],
            'fps':fps,'actions':[],'path':str(out),'started_at':datetime.now(timezone.utc).isoformat(),
            'timing_method':'Real capture wallclock; video frame times are fixed-rate samples.','paid_api_cost':0}
    save_json(out.with_suffix('.recording.json'),record)
    log=out.with_suffix('.capture.log')
    try:
        with log.open('wb') as errors:
            process=subprocess.Popen([ffmpeg(),'-y','-hide_banner','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
                '-s',f'{capture.size[0]}x{capture.size[1]}','-r',str(fps),'-i','pipe:0',
                '-an','-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],
                stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=errors,creationflags=subprocess.CREATE_NO_WINDOW)
            started=time.monotonic()
            if ready_callback:ready_callback(record)
            for index in range(math.ceil(seconds*fps)):
                target=index/fps
                if tick_callback:tick_callback(target,record)
                process.stdin.write(capture.frame().tobytes())
                remaining=started+(index+1)/fps-time.monotonic()
                if remaining>0:time.sleep(remaining)
            process.stdin.close()
            if process.wait(timeout=90):raise RuntimeError(log.read_text('utf-8',errors='replace')[-1600:])
        record.update(status='completed',sha256=sha256(out),**probe(out))
        save_json(out.with_suffix('.recording.json'),record)
        emit('native_record',title=title,duration=record['duration'],output=str(out))
        return record
    except Exception as error:
        if 'process' in locals() and process.poll() is None:process.kill();process.wait()
        record.update(status='failed',error=str(error));save_json(out.with_suffix('.recording.json'),record)
        raise
    finally:capture.close()
