"""Geometrie gefüllter Word-Tabellen aus beiden Microsoft-PDF-Exportwegen.

Kein OCR und keine Wiederherstellung von Rich Text. Seiten-/Zellpositionen bleiben
als Prüfnachweis erhalten. Unbekannte Layouts werden im Import manuell geprüft.
"""
from __future__ import annotations

import re
from pypdf import PdfReader


def normalize_lines(lines):
    result = ''
    for line in lines:
        line = re.sub(r'\s+', ' ', line.replace('\u00ad', '')).strip()
        if not line:
            continue
        if not result:
            result = line
        elif re.match(r'^(?:[•●▪–-]\s|\d+[.)]\s)', line):
            result += '\n' + line
        elif result.endswith('-') and line[0].islower():
            result = result[:-1] + line
        else:
            result += ' ' + line
    return result


def positioned_lines(runs):
    """Reassemble Word's split font runs without losing word boundaries."""
    groups = []
    for run in sorted(runs, key=lambda r: (round(r['y']), r['x'])):
        if not groups or abs(groups[-1][0] - run['y']) > 1.5:
            groups.append((run['y'], [run]))
        else:
            groups[-1][1].append(run)
    result = []
    for y, row in groups:
        value, previous = '', None
        for run in sorted(row, key=lambda r: r['x']):
            if (previous and value and not value[-1].isspace() and not run['text'][0].isspace()
                    and 'end_x' in previous and run['x'] - previous['end_x'] > float(previous['size']) * .15):
                value += ' '
            value += run['text']
            previous = run
        result.append((y, re.sub(r'\s+', ' ', value).strip()))
    return result


def page_cells(page):
    height = float(page.mediabox.height)
    rects, runs, stack, points = [], [], [], []
    color = (0., 0., 0.)
    def xy(x, y, cm):
        return (float(x)*cm[0]+float(y)*cm[2]+cm[4],
                height-(float(x)*cm[1]+float(y)*cm[3]+cm[5]))
    def operand(op, args, cm, tm):
        nonlocal points, color
        if op == b'q':
            stack.append(color)
        elif op == b'Q' and stack:
            color = stack.pop()
        elif op == b'rg':
            color = tuple(map(float, args))
        elif op == b'g':
            color = (float(args[0]),)*3
        elif op == b'k':
            c,m,y,k = map(float,args)
            color = tuple(1-min(1,v+k) for v in (c,m,y))
        elif op == b're':
            x,y,w,h = map(float,args)
            points = [xy(x,y,cm),xy(x+w,y,cm),xy(x+w,y+h,cm),xy(x,y+h,cm)]
        elif op == b'm':
            points = [xy(*args,cm)]
        elif op == b'l':
            points.append(xy(*args,cm))
        elif op in (b'c',b'v',b'y'):
            points = []
        if op in (b'f',b'f*',b'B',b'B*') and len(points) == 4:
            xs,ys=zip(*points)
            x0,y0,x1,y1=min(xs),min(ys),max(xs),max(ys)
            rectangular = all(any(abs(x-edge)<.1 for edge in (x0,x1)) and any(abs(y-edge)<.1 for edge in (y0,y1)) for x,y in points)
            kind = 'blue' if color[2]-color[0]>.04 and min(color)>.75 else 'grey' if max(color)-min(color)<.015 and .89<min(color)<.98 else ''
            if rectangular and kind and x1-x0>30 and y1-y0>5:
                rects.append(dict(x0=x0,y0=y0,x1=x1,y1=y1,color=kind))
        if op in (b'f',b'f*',b'B',b'B*',b'n',b'S',b's'):
            points=[]
    def text(value,cm,tm,font,size):
        if value.strip():
            x,y=xy(tm[4],tm[5],cm)
            run = dict(x=x, y=y, text=value.rstrip('\n'), size=size)
            # Some Word exports omit spaces between separately positioned runs.
            # Use embedded simple-font advances, not an average letter width:
            # arbitrary splitting (e.g. äu + ss + eren) must stay intact.
            if font and font.get('/Encoding') == '/WinAnsiEncoding' and '/Widths' in font:
                try:
                    encoded = run['text'].encode('cp1252')
                    widths = font['/Widths']
                    first = int(font.get('/FirstChar', 0))
                    if all(0 <= code-first < len(widths) for code in encoded):
                        width = sum(float(widths[code-first]) for code in encoded) * float(size) / 1000
                        run['end_x'] = x + width * float(cm[0])
                except (UnicodeEncodeError, TypeError, ValueError):
                    pass
            runs.append(run)
    page.extract_text(visitor_operand_before=operand, visitor_text=text)
    # Word zeichnet Zellfläche und Absatzhintergründe mehrfach. Nur äussere
    # Rechtecke behalten; benachbarte Zielzeilen niemals zusammenführen.
    cells=[]
    for r in sorted(rects,key=lambda r:-(r['x1']-r['x0'])*(r['y1']-r['y0'])):
        if any(r['color']==s['color'] and r['x0']>=s['x0']-.15 and r['x1']<=s['x1']+.15 and r['y0']>=s['y0']-.15 and r['y1']<=s['y1']+.15 for s in cells):
            continue
        cells.append(r)
    def lines(selected):
        grouped=[]
        for run in sorted(selected,key=lambda r:(round(r['y'],0),r['x'])):
            if not grouped or abs(grouped[-1][0]-run['y'])>1.5:
                grouped.append((run['y'],[run]))
            else:
                grouped[-1][1].append(run)
        result = []
        for _, row in grouped:
            value = ''
            previous = None
            for run in sorted(row, key=lambda r: r['x']):
                if (previous and value and not value[-1].isspace() and not run['text'][0].isspace()
                        and 'end_x' in previous and run['x'] - previous['end_x'] > float(previous['size']) * .15):
                    value += ' '
                value += run['text']
                previous = run
            result.append(value.strip())
        return result
    for cell in cells:
        selected=[r for r in runs if cell['x0']-.2<=r['x']<cell['x1'] and cell['y0']<=r['y']<=cell['y1']+.2]
        cell['lines']=lines(selected)
        cell['text']=normalize_lines(cell['lines'])
    return sorted(cells,key=lambda c:(c['y0'],c['x0'])), runs, lines


def read_cells(path):
    result=[]
    for number,page in enumerate(PdfReader(path).pages,1):
        cells,runs,lines=page_cells(page)
        external = [r for r in runs if not any(c['x0']-.2 <= r['x'] < c['x1'] and c['y0'] <= r['y'] <= c['y1']+.2 for c in cells)]
        result.append(dict(page=number,cells=cells,runs=runs,external_lines=positioned_lines(external)))
    return result
