#!/usr/bin/env python3
"""Fail if any text on a KiCad schematic sheet overlaps other text or a symbol body.

    python3 tools/sch_overlap_check.py rusefiSTI2004.kicad_sch [--json]

Checks net labels, visible symbol fields (Reference, Value, power-symbol names) and sheet
names against each other, and every text against the bodies of symbols it does not belong to.
Text size is estimated from KiCad's stroke font (about 0.9 x height per character), so this
is a conservative geometry check, not a renderer. Exit code 1 when anything overlaps.
"""
import json, math, re, sys
from pathlib import Path

TOK = re.compile(r'\s*(?:(\()|(\))|("(?:[^"\\]|\\.)*")|([^\s()"]+))')
CHAR_W = 0.9   # x font height, KiCad stroke font average advance (conservative)
PAD = 0.15     # mm clearance each side


def parse(text):
    stack, cur, pos = [], [], 0
    while True:
        m = TOK.match(text, pos)
        if not m:
            break
        pos = m.end()
        if m.group(1):
            stack.append(cur); cur = []
        elif m.group(2):
            done = cur; cur = stack.pop(); cur.append(done)
        elif m.group(3) is not None:
            cur.append(m.group(3)[1:-1])
        elif m.group(4) is not None:
            cur.append(m.group(4))
    return cur[0]


kids = lambda n, k: [c for c in n if isinstance(c, list) and c and c[0] == k]
one = lambda n, k: (kids(n, k) or [None])[0]


def xform(px, py, x, y, rot, mirror):
    py = -py
    if mirror == 'x':
        py = -py
    elif mirror == 'y':
        px = -px
    a = math.radians(-rot)
    return x + px * math.cos(a) - py * math.sin(a), y + px * math.sin(a) + py * math.cos(a)


def text_box(s, x, y, angle, size, justify):
    """Axis-aligned box of a single-line text anchored KiCad-style.
    KiCad always draws text readable: 180 deg is horizontal and 270 deg vertical, with the
    justification saying which way it runs from the anchor."""
    angle = {180: 0, 270: 90}.get(int(round(angle)) % 360, int(round(angle)) % 360)
    w, h = max(len(s), 1) * size * CHAR_W, size * 1.25
    hj = 'right' if 'right' in justify else 'left' if 'left' in justify else 'center'
    vj = 'top' if 'top' in justify else 'bottom' if 'bottom' in justify else 'center'
    x0 = {'left': 0, 'center': -w / 2, 'right': -w}[hj]
    y0 = {'top': 0, 'center': -h / 2, 'bottom': -h}[vj]
    pts = [(x0, y0), (x0 + w, y0), (x0, y0 + h), (x0 + w, y0 + h)]
    a = math.radians(-angle)
    pts = [(x + px * math.cos(a) - py * math.sin(a), y + px * math.sin(a) + py * math.cos(a)) for px, py in pts]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs) - PAD, min(ys) - PAD, max(xs) + PAD, max(ys) + PAD)


def effects(node):
    e = one(node, 'effects')
    size, just, hide = 1.27, '', False
    if e:
        f = one(e, 'font')
        if f and one(f, 'size'):
            size = float(one(f, 'size')[1])
        j = one(e, 'justify')
        just = ' '.join(j[1:]) if j else ''
        hide = 'hide' in e or any(isinstance(c, list) and c[:2] == ['hide', 'yes'] for c in e)
    return size, just, hide


def body_box(lib, unit, x, y, rot, mirror):
    pts = []
    for sub in kids(lib, 'symbol'):
        m = re.search(r'_(\d+)_(\d+)$', sub[1])
        if m and int(m.group(1)) not in (0, unit):
            continue
        for kind in ('rectangle', 'polyline', 'circle', 'arc'):
            for g in kids(sub, kind):
                for k in ('start', 'end', 'center', 'mid'):
                    p = one(g, k)
                    if p:
                        pts.append((float(p[1]), float(p[2])))
                for xy in kids(one(g, 'pts') or [], 'xy'):
                    pts.append((float(xy[1]), float(xy[2])))
    if not pts:
        return None
    tp = [xform(px, py, x, y, rot, mirror) for px, py in pts]
    xs, ys = [p[0] for p in tp], [p[1] for p in tp]
    shrink = 0.4 if (max(xs) - min(xs) > 2.6 and max(ys) - min(ys) > 2.6) else 0.0
    return (min(xs) + shrink, min(ys) + shrink, max(xs) - shrink, max(ys) - shrink)


def items(path):
    root = parse(Path(path).read_text(encoding='utf-8'))
    libs = {l[1]: l for l in kids(one(root, 'lib_symbols'), 'symbol')}
    out = []   # (kind, owner, text, box)
    for l in kids(root, 'label') + kids(root, 'global_label') + kids(root, 'hierarchical_label'):
        at = one(l, 'at'); size, just, hide = effects(l)
        out.append(('label', None, l[1], text_box(l[1], float(at[1]), float(at[2]), float(at[3]), size, just or 'left bottom')))
    for s in kids(root, 'symbol'):
        ref = next((p[2] for p in kids(s, 'property') if p[1] == 'Reference'), '?')
        at = one(s, 'at'); x, y, rot = float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0
        mir = one(s, 'mirror'); mir = mir[1] if mir else None
        unit = int(one(s, 'unit')[1]) if one(s, 'unit') else 1
        lib = libs.get(one(s, 'lib_id')[1])
        for p in kids(s, 'property'):
            size, just, hide = effects(p)
            if hide or p[1] not in ('Reference', 'Value') or not p[2]:
                continue
            pa = one(p, 'at')
            ang = (float(pa[3]) if len(pa) > 3 else 0) + rot      # field angles are relative to the symbol
            out.append(('field', ref, p[2], text_box(p[2], float(pa[1]), float(pa[2]), ang, size, just or 'center')))
        if lib is not None and not ref.startswith('#'):
            b = body_box(lib, unit, x, y, rot, mir)
            if b:
                out.append(('body', ref, ref, b))
    for sh in kids(root, 'sheet'):
        at = one(sh, 'at'); sz = one(sh, 'size'); name = next(p[2] for p in kids(sh, 'property') if p[1] == 'Sheetname')
        x, y = float(at[1]), float(at[2])
        out.append(('body', 'sheet:' + name, name, (x, y, x + float(sz[1]), y + float(sz[2]))))
        for p in kids(sh, 'property'):
            size, just, hide = effects(p)
            if hide:
                continue
            pa = one(p, 'at')
            out.append(('field', 'sheet:' + name, p[2], text_box(p[2], float(pa[1]), float(pa[2]), float(pa[3]), size, just)))
        for pin in kids(sh, 'pin'):   # sheet pin names sit inside the sheet box: part of the body
            pass
    return out


def overlaps(path):
    it = items(path)
    hit = lambda a, b: not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])
    bad = []
    for i, a in enumerate(it):
        for b in it[i + 1:]:
            if a[0] == 'body' and b[0] == 'body':
                continue                      # body vs body is layout, not text
            if a[1] is not None and a[1] == b[1] and 'body' in (a[0], b[0]):
                continue                      # a symbol's own fields may sit on its own body (not on each other)
            if hit(a[3], b[3]):
                bad.append((a, b))
    return bad


if __name__ == '__main__':
    sch = sys.argv[1] if len(sys.argv) > 1 else 'rusefiSTI2004.kicad_sch'
    bad = overlaps(sch)
    if '--json' in sys.argv:
        print(json.dumps([[a[0], a[1], a[2], [round(v, 2) for v in a[3]], b[0], b[1], b[2], [round(v, 2) for v in b[3]]] for a, b in bad]))
    else:
        for a, b in bad:
            print(f'{a[0]} {a[2]!r} ({a[1] or ""}) @ {tuple(round(v, 1) for v in a[3][:2])}  x  {b[0]} {b[2]!r} ({b[1] or ""}) @ {tuple(round(v, 1) for v in b[3][:2])}')
        print(f'{len(bad)} overlap(s)')
    sys.exit(1 if bad else 0)
