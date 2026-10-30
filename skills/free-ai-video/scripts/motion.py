"""Original continuous motion graphics; no paid image/video generator."""
from __future__ import annotations
import math
from PIL import Image, ImageDraw
from compose import font, wrap, INK, PAPER, MINT, round_box

W, H = 720, 1280


def fitted(draw, text, box, size=78, fill=PAPER, bold=True, max_lines=3, align='left'):
    x, y, width, height = box
    while size >= 24:
        face = font(size, bold)
        lines = wrap(text, width, face)
        if len(lines) <= max_lines and len(lines)*(size+12) <= height:
            break
        size -= 2
    if len(lines) > max_lines or len(lines)*(size+12) > height:
        raise ValueError(f'Motion text is too long: {text}')
    for line in lines:
        dx = (width-face.getlength(line))/2 if align == 'center' else 0
        draw.text((x+dx,y), line, font=face, fill=fill)
        y += size+12


def background(t, dark=True):
    image = Image.new('RGB', (W,H), INK if dark else PAPER)
    d = ImageDraw.Draw(image)
    color = '#28443E' if dark else '#E0E4D9'
    for x in range(-80, 800, 80):
        drift = int(14*math.sin(t*.5))
        d.line((x+drift,180,x+drift,1080),fill=color,width=1)
    for y in range(180,1080,80):
        d.line((0,y,720,y),fill=color,width=1)
    return image


def frame(spec, elapsed, duration):
    progress = min(.999999, max(0, elapsed/duration))
    image = background(elapsed)
    d = ImageDraw.Draw(image)
    layout = spec.get('layout', 'kinetic')
    if layout in ('bars', 'table'):
        return data_frame(spec, elapsed, duration)
    words = spec.get('words') or spec['nodes']
    if layout == 'kinetic':
        at = min(len(words)-1, int(progress*len(words)))
        phase = progress*len(words)-at
        entrance = 1-(1-min(1,phase/.22))**3
        d.text((48,290),f'{at+1:02} / {len(words):02}',font=font(28,True),fill=MINT)
        offset = int(70*(1-entrance))
        fitted(d,words[at],(48,430+offset,624,340),size=92,fill=PAPER,max_lines=3)
        d.rectangle((48,815,48+int(624*entrance),826), fill=MINT)
        if at:
            fitted(d, words[at-1], (48,905,624,110), size=30,fill='#90AAA0',max_lines=2)
        # A moving signal accent supplies continuous motion between word entrances.
        x = 48+int(600*phase)
        d.ellipse((x,1010,x+22,1032),fill=MINT)
    elif layout == 'flow':
        nodes = words[:4]
        tops = [280+i*205 for i in range(len(nodes))]
        for i,y in enumerate(tops[:-1]):
            next_y = tops[i+1]
            d.line((360,y+104,360,next_y),fill='#627D70',width=4)
            travel = (elapsed*.75-i*.16)%1
            cy = y+112+(next_y-y-112)*travel
            d.ellipse((350,cy-10,370,cy+10),fill=MINT)
        active = min(len(nodes)-1, int(progress*len(nodes)))
        for i,(text,y) in enumerate(zip(nodes,tops)):
            scale = 1+.025*math.sin(elapsed*4) if i == active else 1
            half = int(288*scale)
            round_box(d,(360-half,y,360+half,y+110),24,MINT if i == active else '#2C483F')
            fitted(d,text,(96,y+23,528,80),size=39,fill=INK if i == active else PAPER,max_lines=1,align='center')
    else:
        divider = int(360+110*math.sin(progress*math.pi*2))
        d.rectangle((0,260,divider,1030),fill='#203C35')
        d.rectangle((divider,260,720,1030),fill=MINT)
        fitted(d,words[0],(36,430,max(170,divider-72),390),size=72,fill=PAPER,max_lines=4)
        fitted(d,words[min(1,len(words)-1)],(divider+24,430,720-divider-48,390),size=72,fill=INK,max_lines=4)
        d.line((divider,260,divider,1030),fill=PAPER,width=4)
        d.ellipse((divider-28,640,divider+28,696),fill=PAPER)
    return image


def data_frame(spec, elapsed, duration):
    """Original animated, zero-based comparisons; values remain readable after entry."""
    image = background(elapsed)
    d = ImageDraw.Draw(image)
    fitted(d, spec['title'], (48,190,624,155), size=49, max_lines=2)
    fitted(d, spec.get('unit',''), (48,348,624,80), size=25, max_lines=2, fill='#ACC4B8')
    rows = spec['rows']
    step = min(170, 375/max(1,len(rows)-1))
    row_top = 450
    if spec['layout'] == 'table':
        columns = spec['columns']
        left = 322
        cell_width = (672-left)/len(columns)
        for i,column in enumerate(columns):
            fitted(d,column,(left+i*cell_width,420,cell_width,48),size=25,max_lines=1,align='center',fill='#ACC4B8')
        row_top = 488
        step = min(144,360/max(1,len(rows)-1))
    for i,row in enumerate(rows):
        y = row_top+i*step
        # Animate all rows into their final values early; do not cycle away the comparison.
        entry = min(1,max(0,(elapsed-i*.12)/.8))
        ease = 1-(1-entry)**3
        color = row.get('color',MINT if i == 0 else '#89AFA0')
        if spec['layout'] == 'bars':
            fitted(d,row['label'],(48,y-12,455,58),size=30,max_lines=1)
            value = row.get('display',f"{row['value']:g}")
            face = font(40,True)
            d.text((672-face.getlength(value),y-18),value,font=face,fill=color)
            d.rounded_rectangle((48,y+54,672,y+86),8,fill='#29483E')
            length = 624*row['value']/spec['max_value']*ease
            if length >= 2:
                d.rounded_rectangle((48,y+54,48+length,y+86),min(8,length/2),fill=color)
            d.line((48,y+99,672,y+99),fill='#37544A',width=1)
            if i == len(rows)-1:
                d.text((48,y+103),'0',font=font(19),fill='#A6BEB2')
                high=f"{spec['max_value']:g}"
                d.text((672-font(19).getlength(high),y+103),high,font=font(19),fill='#A6BEB2')
        else:
            d.rounded_rectangle((34,y-9,686,y+104),14,fill='#29483E' if i == 0 else '#1A372E')
            fitted(d,row['label'],(48,y+22,264,65),size=29,max_lines=1,fill=color)
            for j,cell in enumerate(row['cells']):
                fitted(d,cell,(left+j*cell_width,y+18+int(10*(1-ease)),cell_width,72),size=45,max_lines=1,align='center',fill=color)
    if spec.get('note'):
        fitted(d,spec['note'],(48,975,624,75),size=24,max_lines=2,fill='#B6CBBF')
    return image
