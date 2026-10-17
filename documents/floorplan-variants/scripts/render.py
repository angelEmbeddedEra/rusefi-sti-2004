#!/usr/bin/env python3
"""render.py BOARD.kicad_pcb OUT.png : placement picture from the board file (pads, part boxes, refs, J1-to-driver airwires)."""
import sys, importlib.util
from PIL import Image, ImageDraw
spec = importlib.util.spec_from_file_location('fs', '/home/angel/kicad-lib/scripting/pcb/floorplan_score.py'); fs = importlib.util.module_from_spec(spec); spec.loader.exec_module(fs)
b = fs.load_board(sys.argv[1]); x0, y0, x1, y1 = b['outline']; S = 7
img = Image.new('RGB', (int((x1 - x0) * S) + 20, int((y1 - y0) * S) + 20), 'white'); g = ImageDraw.Draw(img)
X = lambda v: 10 + (v - x0) * S; Y = lambda v: 10 + (v - y0) * S
g.rectangle([X(x0), Y(y0), X(x1), Y(y1)], outline='black', width=2)
P = {p.ref: p for p in b['parts']}
col = lambda r: 'red' if r == 'J1' else 'blue' if r[:1] in 'UQ' and r != 'U20' else 'darkgreen' if r[0] in 'MJHG' or r == 'U20' else '#888'
# airwires from each driver output pad to its J1 pad
j1 = {d.net: d for d in P['J1'].pads if d.net}
for r, p in P.items():
    if r in ([f'U{i}' for i in range(10, 20)] + ['Q16']):
        for d in p.pads:
            if d.net in j1 and d.net.startswith('OUT'):
                g.line([X(d.x), Y(d.y), X(j1[d.net].x), Y(j1[d.net].y)], fill='#f90', width=1)
for r, p in P.items():
    c = col(r)
    for d in p.pads:
        g.rectangle([X(d.x - d.hx), Y(d.y - d.hy), X(d.x + d.hx), Y(d.y + d.hy)], outline=c if r != 'J1' else '#fbb')
    if p.bbox and (c != '#888' or r[0] in 'FJ'):
        bb = p.bbox; g.rectangle([X(bb[0]), Y(bb[1]), X(bb[2]), Y(bb[3])], outline=c, width=1)
    if c != '#888' or r[:1] in 'FR' and False:
        g.text((X(p.x) + 2, Y(p.y) + 2), r, fill=c)
img.save(sys.argv[2]); print('wrote', sys.argv[2], img.size)
