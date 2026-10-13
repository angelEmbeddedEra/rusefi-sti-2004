#!/usr/bin/env python3
"""Tidy KiCad 10 schematic sheets to the house style (SOP-021 step 8):

1. A two-pin part (R, JP, F, C, D, L) whose one pin goes straight to a power symbol stands
   vertical: GND-type rails at the bottom, supply rails at the top. The other pin stays put.
2. A test point on a rail gets the rail symbol directly on its pin, the test point turned to face it.
3. Every other power symbol points the house way (GND down, rails up); when turning it in place
   would sit on its own wire, it moves out to the end of a short wire stub first.
4. Reference/Value of every small part are placed the way KiCad's Autoplace Fields (the O key)
   does it: first free pin-less side in the order right, top, left, bottom; stacked on 2.54 mm,
   snapped to the 50 mil grid. Power symbols get their library field positions.

Every change is kept only if it adds no overlap (tools/sch_overlap_check.py) and no new contact.
The caller checks the netlist is unchanged (tools/tidy-check.sh does both).

    python3 tools/sch_tidy.py SHEET.kicad_sch [...]
"""
import math, re, sys, tempfile, os, uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sch_overlap_check as ovl
from sch_overlap_check import parse, kids, one, xform

DIRS = {'U': (0, -1), 'D': (0, 1), 'L': (-1, 0), 'R': (1, 0)}
HPAD, VPAD, GRID, SLOT = 0.635, 0.381, 1.27, 2.54      # KiCad autoplace: 25 mil, 15 mil, 50 mil
TWO_PIN = re.compile(r'^(R|JP|F|C|D|L)\d+$')
SMALL = re.compile(r'^(R|JP|F|C|D|L|P|Q|U)\d+$')


def fmt(v):
    s = f'{v:.4f}'.rstrip('0').rstrip('.')
    return '0' if s == '-0' else s


def block_at(t, start):
    d = 0
    for i in range(start, len(t)):
        if t[i] == '(':
            d += 1
        elif t[i] == ')':
            d -= 1
            if d == 0:
                return i + 1
    raise ValueError('unbalanced')


# ---- model ----------------------------------------------------------------------------------
class Sheet:
    def __init__(self, text):
        self.t = text
        root = parse(text)
        self.libs = {l[1]: l for l in kids(one(root, 'lib_symbols'), 'symbol')}
        self.scan()

    def scan(self):
        """Index top-level symbols, wires and connectable points from the current text."""
        t = self.t
        self.syms, self.wires, self.points = {}, [], []     # points: (x, y, kind, id)
        for m in re.finditer(r'\n\t\((symbol|wire|label|global_label|hierarchical_label|junction|no_connect)\b', t):
            s = m.start() + 2; e = block_at(t, s); node = parse(t[s:e]); kind = m.group(1)
            if kind == 'symbol':
                sym = self.symbol(node, s, e)
                self.syms[sym['uuid']] = sym
                for num, (px, py) in sym['pins'].items():
                    self.points.append((px, py, 'pin', (sym['uuid'], num)))
            elif kind == 'wire':
                pts = [(float(q[1]), float(q[2])) for q in kids(one(node, 'pts'), 'xy')]
                u = one(node, 'uuid')[1]
                self.wires.append({'uuid': u, 'a': pts[0], 'b': pts[-1], 'span': (s, e)})
            else:
                at = one(node, 'at')
                self.points.append((float(at[1]), float(at[2]), kind, one(node, 'uuid')[1]))

    def symbol(self, node, s, e):
        at = one(node, 'at'); mir = one(node, 'mirror')
        props = {p[1]: p[2] for p in kids(node, 'property')}
        sym = {'uuid': one(node, 'uuid')[1], 'lib': one(node, 'lib_id')[1], 'ref': props.get('Reference', '?'),
               'value': props.get('Value', ''), 'x': float(at[1]), 'y': float(at[2]),
               'rot': int(float(at[3])) if len(at) > 3 else 0, 'mir': mir[1] if mir else None,
               'unit': int(one(node, 'unit')[1]) if one(node, 'unit') else 1, 'span': (s, e)}
        lib = self.libs[sym['lib']]
        sym['power'] = any(isinstance(c, list) and c[0] == 'power' for c in lib)
        sym['gnd'] = sym['power'] and 'GND' in sym['value']
        sym['libpins'] = lib_pins(lib, sym['unit'])
        sym['pins'] = {n: rnd(xform(px, py, sym['x'], sym['y'], sym['rot'], sym['mir'])) for n, (px, py) in sym['libpins'].items()}
        return sym

    # connectivity helpers
    def at(self, p, skip=()):
        """Everything that connects at point p: ('pin'|label kinds, id) plus ('wire', uuid) for wire ends and wire interiors."""
        out = [(k, i) for x, y, k, i in self.points if close((x, y), p) and i not in skip]
        for w in self.wires:
            if w['uuid'] in skip:
                continue
            if close(w['a'], p) or close(w['b'], p) or on_segment(p, w['a'], w['b']):
                out.append(('wire', w['uuid']))
        return out

    def wire(self, u):
        return next(w for w in self.wires if w['uuid'] == u)


def lib_pins(lib, unit):
    out = {}
    for sub in kids(lib, 'symbol'):
        m = re.search(r'_(\d+)_(\d+)$', sub[1])
        if m and int(m.group(1)) not in (0, unit):
            continue
        for p in kids(sub, 'pin'):
            at = one(p, 'at')
            out[one(p, 'number')[1]] = (float(at[1]), float(at[2]))
    return out


def rnd(p):
    return (round(p[0], 3), round(p[1], 3))


def close(a, b):
    return abs(a[0] - b[0]) < 0.01 and abs(a[1] - b[1]) < 0.01


def on_segment(p, a, b):
    if close(p, a) or close(p, b):
        return False
    if abs(a[0] - b[0]) < 0.01:
        return abs(p[0] - a[0]) < 0.01 and min(a[1], b[1]) < p[1] < max(a[1], b[1])
    if abs(a[1] - b[1]) < 0.01:
        return abs(p[1] - a[1]) < 0.01 and min(a[0], b[0]) < p[0] < max(a[0], b[0])
    return False


# ---- text edits -----------------------------------------------------------------------------
def set_symbol_at(block, x, y, rot, mir):
    block = re.sub(r'\(at [-\d.]+ [-\d.]+(?: [-\d.]+)?\)', f'(at {fmt(x)} {fmt(y)} {rot})', block, count=1)
    block = re.sub(r'\n\t\t\(mirror [xy]\)', '', block)
    if mir:
        block = block.replace('\n\t\t(unit ', f'\n\t\t(mirror {mir})\n\t\t(unit ', 1)
    return block


def set_field(block, name, x, y, angle, hjust=None):
    m = re.search(r'\(property "' + re.escape(name) + r'" ', block)
    if not m:
        return block
    s = m.start(); e = block_at(block, s); p = block[s:e]
    p = re.sub(r'\(at [-\d.]+ [-\d.]+ [-\d.]+\)', f'(at {fmt(x)} {fmt(y)} {angle})', p, count=1)
    if hjust is not None:
        es = p.index('(effects'); ee = block_at(p, es); eff = p[es:ee]
        eff = re.sub(r'\s*\(justify [^)]*\)', '', eff)
        if hjust != 'center':
            eff = eff[:-1].rstrip() + f'\n\t\t\t\t(justify {hjust})\n\t\t\t)'
        p = p[:es] + eff + p[ee:]
    return block[:s] + p + block[e:]


def mark_autoplaced(block):
    if '(fields_autoplaced' in block:
        return block
    return re.sub(r'(\n\t\t\(dnp [a-z]+\))', r'\1\n\t\t(fields_autoplaced yes)', block, count=1)


def wire_text(a, b):
    return (f'\t(wire\n\t\t(pts\n\t\t\t(xy {fmt(a[0])} {fmt(a[1])}) (xy {fmt(b[0])} {fmt(b[1])})\n\t\t)\n'
            f'\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n')


class Edit:
    """Collects replacements on one text snapshot; apply() returns the new text."""
    def __init__(self, sh):
        self.sh, self.rep, self.add = sh, {}, []

    def symbol(self, u):
        s, e = self.sh.syms[u]['span']
        return self.rep.get((s, e), self.sh.t[s:e])

    def put(self, u, block):
        self.rep[self.sh.syms[u]['span']] = block

    def drop_wire(self, wu):
        self.rep[self.sh.wire(wu)['span']] = None

    def apply(self):
        t = self.sh.t
        for (s, e), b in sorted(self.rep.items(), reverse=True):
            if b is None:                     # drop the block and its line
                t = t[:s - 1] + t[e:]
            else:
                t = t[:s] + b + t[e:]
        if self.add:
            i = next((t.index(k) for k in ('\n\t(sheet_instances', '\n\t(embedded_fonts') if k in t), t.rstrip().rindex('\n'))
            t = t[:i + 1] + ''.join(self.add) + t[i + 1:]
        return t


# ---- power symbols --------------------------------------------------------------------------
def power_block(ed, sym, x, y):
    """Place power symbol `sym` with its pin at (x, y), pointing the house way, fields from the library."""
    b = set_symbol_at(ed.symbol(sym['uuid']), x, y, 0, None)
    lib = ed.sh.libs[sym['lib']]
    for p in kids(lib, 'property'):
        if p[1] in ('Reference', 'Value'):
            a = one(p, 'at')
            b = set_field(b, p[1], x + float(a[1]), y - float(a[2]), 0, 'center')
    return b


def want_dir(sym):
    return 'D' if sym['gnd'] else 'U'


def points_dir(sym):
    """Which way a power symbol points now (GND lib draws down at rot 0, rails up)."""
    base = {0: 'D', 90: 'R', 180: 'U', 270: 'L'} if sym['gnd'] else {0: 'U', 90: 'L', 180: 'D', 270: 'R'}
    d = base[sym['rot'] % 360]
    if sym['mir'] == 'x' and d in 'UD':
        d = 'U' if d == 'D' else 'D'
    if sym['mir'] == 'y' and d in 'LR':
        d = 'L' if d == 'R' else 'R'
    return d


# ---- rules ----------------------------------------------------------------------------------
def power_side(sh, sym, num):
    """If pin `num` of sym runs to one power symbol through a bare chain of wires (no branches,
    nothing else attached): (power symbol, [wire uuids])."""
    p = sym['pins'][num]
    used, prev = [], sym['uuid']
    while True:
        here = [h for h in sh.at(p, skip=tuple(used))
                if not (h[0] == 'pin' and h[1][0] == sym['uuid'])]
        if len(here) != 1:
            return None
        k, i = here[0]
        if k == 'pin':
            other = sh.syms[i[0]]
            return (other, used) if other['power'] and len(other['pins']) == 1 else None
        if k != 'wire':
            return None
        w = sh.wire(i)
        if not (close(w['a'], p) or close(w['b'], p)):
            return None
        used.append(i)
        p = w['b'] if close(w['a'], p) else w['a']


def plan_two_pin(sh, sym, stub=0):
    nums = list(sym['pins'])
    if len(nums) != 2 or not TWO_PIN.match(sym['ref']):
        return None
    for pnum, snum in ((nums[0], nums[1]), (nums[1], nums[0])):
        ps = power_side(sh, sym, pnum)
        if not ps or (power_side(sh, sym, snum)):
            continue
        pwr, wus = ps
        sig0 = sym['pins'][snum]
        bx, by = sym['pins'][pnum][0] - sig0[0], sym['pins'][pnum][1] - sig0[1]
        if stub and abs(by) > 0.01:
            return None                       # already vertical: nothing to slide along
        step = (math.copysign(1, bx), 0) if stub else (0, 0)
        sig = rnd((sig0[0] + step[0] * stub, sig0[1]))
        down = pwr['gnd']
        # choose rot 0 / mirror so that the signal pin sits at `sig` and the power pin straight below/above
        for mir in (None, 'x'):
            lp = {n: rnd(xform(px, py, 0, 0, 0, mir)) for n, (px, py) in sym['libpins'].items()}
            dx, dy = lp[pnum][0] - lp[snum][0], lp[pnum][1] - lp[snum][1]
            if abs(dx) < 0.01 and ((dy > 0) == down):
                x0, y0 = sig[0] - lp[snum][0], sig[1] - lp[snum][1]
                ppin = rnd((sig[0] + dx, sig[1] + dy))
                already = sym['rot'] % 360 == 0 and sym['mir'] == mir and not wus and points_dir(pwr) == want_dir(pwr)
                if already:
                    return None
                ed = Edit(sh)
                ed.put(sym['uuid'], set_symbol_at(ed.symbol(sym['uuid']), x0, y0, 0, mir))
                if stub:
                    ed.add.append(wire_text(sig0, sig))
                for wu in wus:
                    ed.drop_wire(wu)
                ed.put(pwr['uuid'], power_block(ed, pwr, *ppin))
                return ed, {sym['uuid'], pwr['uuid']}, [ppin], wus
    return None


def plan_test_point(sh, sym):
    if not sym['ref'].startswith('P') or len(sym['pins']) != 1:
        return None
    num = next(iter(sym['pins']))
    ps = power_side(sh, sym, num)
    if not ps:
        return None
    pwr, wus = ps
    p = sym['pins'][num]
    mir = None if pwr['gnd'] else 'x'          # TP circle above its pin at rot 0
    lpx, lpy = sym['libpins'][num]
    o = rnd(xform(lpx, lpy, 0, 0, 0, mir))
    if sym['rot'] % 360 == 0 and sym['mir'] == mir and not wus and points_dir(pwr) == want_dir(pwr):
        return None
    ed = Edit(sh)
    ed.put(sym['uuid'], set_symbol_at(ed.symbol(sym['uuid']), p[0] - o[0], p[1] - o[1], 0, mir))
    for wu in wus:
        ed.drop_wire(wu)
    ed.put(pwr['uuid'], power_block(ed, pwr, *p))
    return ed, {sym['uuid'], pwr['uuid']}, [], wus


def plan_power(sh, sym, stub):
    """Turn a power symbol the house way, optionally after a straight stub of `stub` mm."""
    p = next(iter(sym['pins'].values()))
    ed = Edit(sh)
    if points_dir(sym) == want_dir(sym) and stub == 0:      # right way already: library field positions
        b = power_block(ed, sym, *p)
        if b == ed.symbol(sym['uuid']):
            return None
        ed.put(sym['uuid'], b)
        return ed, {sym['uuid']}, [], None
    if stub:
        d = DIRS[points_dir(sym)]
        if points_dir(sym) in 'UD':          # vertical already (either way): go sideways first
            d = (1, 0)
        q = rnd((p[0] + d[0] * stub, p[1] + d[1] * stub))
        ed.add.append(wire_text(p, q))
        ed.put(sym['uuid'], power_block(ed, sym, *q))
        return ed, {sym['uuid']}, [q], None
    ed.put(sym['uuid'], power_block(ed, sym, *p))
    return ed, {sym['uuid']}, [], None


def plan_sideways_text(sh, sym, stub=0):
    """A power symbol that has to stay sideways: Value horizontal just past the tip, Reference on the
    pin; with `stub`, first moved out along a longer wire."""
    p0 = next(iter(sym['pins'].values()))
    d = points_dir(sym)
    if d not in 'LR':
        return None
    dx = DIRS[d][0]
    p = rnd((p0[0] + dx * stub, p0[1]))
    ed = Edit(sh); b = ed.symbol(sym['uuid'])
    if stub:
        ed.add.append(wire_text(p0, p))
        b = re.sub(r'\(at [-\d.]+ [-\d.]+ ([-\d.]+)\)', lambda m: f'(at {fmt(p[0])} {fmt(p[1])} {m.group(1)})', b, count=1)
    stored = (-sym['rot']) % 360
    if sym['mir'] == 'x' and stored % 180:
        stored = (stored + 180) % 360
    just = 'left' if dx > 0 else 'right'
    if ovl.field_hflip(stored + sym['rot'], sym['rot'], sym['mir']):
        just = 'right' if just == 'left' else 'left'
    b = set_field(b, 'Value', p[0] + dx * 3.81, p[1], stored, just)
    b = set_field(b, 'Reference', p[0], p[1], stored, None)
    if b == ed.symbol(sym['uuid']):
        return None
    ed.put(sym['uuid'], b)
    return ed, {sym['uuid']}, [p] if stub else [], None


def in_overlap(text):
    """References of power symbols that take part in an overlap now."""
    with tempfile.NamedTemporaryFile('w', suffix='.kicad_sch', delete=False) as f:
        f.write(text); name = f.name
    try:
        return {o[1] for pair in ovl.overlaps(name) for o in pair if (o[1] or '').startswith('#')}
    finally:
        os.unlink(name)


def chains(sh):
    """Sideways power symbols of one rail stacked on 2.54 mm in one column: [[sym, ...], ...]."""
    groups = {}
    for s in sh.syms.values():
        if s['power'] and points_dir(s) in 'LR':
            p = next(iter(s['pins'].values()))
            groups.setdefault((s['value'], points_dir(s), p[0]), []).append((p[1], s))
    out = []
    for (_, d, _), items in groups.items():
        items.sort(key=lambda i: i[0])
        cur = [items[0]]
        for it in items[1:]:
            if abs(it[0] - cur[-1][0] - 2.54) < 0.01:
                cur.append(it)
            else:
                out.append(cur); cur = [it]
        out.append(cur)
    return [[s for _, s in c] for c in out if len(c) > 1]


def plan_chain(sh, group, stub):
    """Join a stacked group at `stub` mm out with one wire and keep one symbol, at the bottom (GND)
    or top (rails), pointing the house way."""
    d = DIRS[points_dir(group[0])][0]
    pts = [next(iter(s['pins'].values())) for s in group]
    xs = rnd((pts[0][0] + d * stub, 0))[0]
    ed = Edit(sh)
    for p in pts:
        ed.add.append(wire_text(p, (xs, p[1])))
    top, bot = (xs, pts[0][1]), (xs, pts[-1][1])
    ed.add.append(wire_text(top, bot))
    for p in pts[1:-1]:
        ed.add.append(junction_text(xs, p[1]))
    keep = group[-1] if group[0]['gnd'] else group[0]
    end = bot if keep['gnd'] else top
    ed.add.append(junction_text(*end))
    for s in group:
        if s is keep:
            ed.put(s['uuid'], power_block(ed, s, *end))
        else:
            ed.rep[s['span']] = None
    return ed, {s['uuid'] for s in group}, [(xs, p[1]) for p in pts], None


def junction_text(x, y):
    return (f'\t(junction\n\t\t(at {fmt(x)} {fmt(y)})\n\t\t(diameter 0)\n\t\t(color 0 0 0 0)\n'
            f'\t\t(uuid "{uuid.uuid4()}")\n\t)\n')


# ---- autoplace (KiCad AUTOPLACER, eeschema/autoplace_fields.cpp, 10.0) -----------------------
def body_bbox(lib, unit, x, y, rot, mir):
    pts = []
    for sub in kids(lib, 'symbol'):
        m = re.search(r'_(\d+)_(\d+)$', sub[1])
        if m and int(m.group(1)) not in (0, unit):
            continue
        for kind in ('rectangle', 'polyline', 'circle', 'arc'):
            for g in kids(sub, kind):
                if kind == 'circle':
                    c = one(g, 'center'); r = float(one(g, 'radius')[1])
                    pts += [(float(c[1]) - r, float(c[2]) - r), (float(c[1]) + r, float(c[2]) + r)]
                for k in ('start', 'end', 'mid'):
                    q = one(g, k)
                    if q:
                        pts.append((float(q[1]), float(q[2])))
                for xy in kids(one(g, 'pts') or [], 'xy'):
                    pts.append((float(xy[1]), float(xy[2])))
    tp = [xform(px, py, x, y, rot, mir) for px, py in pts]
    xs, ys = [p[0] for p in tp], [p[1] for p in tp]
    return min(xs), min(ys), max(xs), max(ys)


def round_n(v, n, up):
    q = v / n
    return n * (math.ceil(q - 1e-6) if up else math.floor(q + 1e-6))


def autoplace(sh, sym, others=(), force=None):
    """New property positions for sym's visible Reference/Value, KiCad-style; returns (plan, sides in
    KiCad's preference order). others: boxes to avoid; force: use this side."""
    s, e = sym['span']; node = parse(sh.t[s:e])
    fields = []
    for p in kids(node, 'property'):
        size, _, hide = ovl.effects(p)
        if p[1] in ('Reference', 'Value') and not hide and p[2]:
            fields.append((p[1], p[2], size))
    if not fields:
        return None, []
    lib = sh.libs[sym['lib']]
    bx0, by0, bx1, by1 = body_bbox(lib, sym['unit'], sym['x'], sym['y'], sym['rot'], sym['mir'])
    cx, cy, bw, bh = (bx0 + bx1) / 2, (by0 + by1) / 2, bx1 - bx0, by1 - by0
    fw = max(len(v) * sz * ovl.CHAR_W for _, v, sz in fields)
    fh = SLOT * len(fields)
    pin_side = {}
    for px, py in sym['pins'].values():
        dx, dy = px - cx, py - cy
        side = ('R' if dx > 0 else 'L') if abs(dx) > abs(dy) else ('D' if dy > 0 else 'U')
        pin_side[side] = pin_side.get(side, 0) + 1
    order = ['R', 'U', 'L', 'D']
    if bh and bw / bh > 3.0:
        order = ['U', 'D', 'L', 'R']

    def box_for(side):
        sx, sy = DIRS[side]
        ox = (bw + fw) / 2 + (HPAD if sx else 0)
        oy = (bh + fh) / 2 + (VPAD if sy else 0)
        x = cx + sx * ox - fw / 2; y = cy + sy * oy - fh / 2
        return x, y

    def collides(side):
        x, y = box_for(side)
        b = (x, y, x + fw, y + fh)
        return any(not (b[2] <= o[0] or o[2] <= b[0] or b[3] <= o[1] or o[3] <= b[1]) for o in others)

    free = [sd for sd in order if not pin_side.get(sd)]
    prefs = free + sorted((sd for sd in order if sd not in free), key=lambda sd: pin_side[sd])
    side = force or next((sd for sd in free if not collides(sd)), prefs[0])
    x, y = box_for(side)
    hj = {'R': 'left', 'L': 'right', 'U': 'center', 'D': 'center'}[side]
    if pin_side.get(side):
        hj = 'left' if side in 'UD' else 'center'
    angle = 90 if sym['rot'] % 180 else 0                     # displayed horizontal
    out = []
    for i, (name, val, sz) in enumerate(fields):
        fx = {'left': x, 'center': x + fw / 2, 'right': x + fw}[hj]
        fy = y + SLOT / 2 + SLOT * i
        sx, sy = DIRS[side]
        if sx:
            fx = round_n(fx, GRID, sx >= 0)
        if sy:
            fy = round_n(fy, GRID, sy >= 0)
        stored = hj
        if hj != 'center' and ovl.field_hflip(angle + sym['rot'], sym['rot'], sym['mir']):
            stored = 'right' if hj == 'left' else 'left'
        out.append((name, fx, fy, angle, stored))
    return out, prefs


def place_fields(text, u, limit):
    """Autoplace the fields of symbol u: first side (KiCad order) that keeps overlaps <= limit."""
    sh = Sheet(text)
    sym = sh.syms[u]
    plan, prefs = autoplace(sh, sym)
    for side in prefs:
        plan, _ = autoplace(sh, sym, force=side)
        ed = Edit(sh); b = ed.symbol(u)
        for name, fx, fy, ang, hj in plan:
            b = set_field(b, name, fx, fy, ang, hj)
        ed.put(u, mark_autoplaced(b))
        new = ed.apply()
        if limit is None or no_worse(count_overlaps(new), limit):
            return new
    return None


# ---- driver ---------------------------------------------------------------------------------
def count_overlaps(text):
    """(overlaps at the checker's clearance, overlaps at the tidy clearance)."""
    with tempfile.NamedTemporaryFile('w', suffix='.kicad_sch', delete=False) as f:
        f.write(text); name = f.name
    try:
        out = []
        for pad in (CHECK_PAD, TIDY_PAD):
            ovl.PAD = pad
            out.append(len(ovl.overlaps(name)))
        return tuple(out)
    finally:
        ovl.PAD = CHECK_PAD
        os.unlink(name)


def no_worse(score, base):
    return all(s <= b for s, b in zip(score, base))


def new_contacts(sh, new_text, moved, new_points, dropped_wire):
    """True if a moved part's pin (or a new stub end) now lands on something it did not touch before."""
    after = Sheet(new_text)
    for u in moved:
        if u not in after.syms:
            continue
        for num, p in after.syms[u]['pins'].items():
            hits = [h for h in after.at(p, skip=tuple(moved)) if not (h[0] == 'pin' and h[1][0] in moved)]
            before = sh.syms[u]['pins'].get(num)
            if before and close(before, p):
                continue                      # pin did not move: whatever it touched it still touches
            if hits and not all(h[0] in ('wire', 'junction') and is_new(sh, h[1]) for h in hits):
                return True
        # nor may its body now sit on a wire that is not its own
        s = after.syms[u]
        x0, y0, x1, y1 = body_bbox(after.libs[s['lib']], s['unit'], s['x'], s['y'], s['rot'], s['mir'])
        for w in after.wires:
            if any(close(w[k], q) for k in ('a', 'b') for q in s['pins'].values()):
                continue
            wx0, wx1 = sorted((w['a'][0], w['b'][0])); wy0, wy1 = sorted((w['a'][1], w['b'][1]))
            if wx0 < x1 and x0 < wx1 + 0.01 and wy0 < y1 and y0 < wy1 + 0.01:
                return True
    return False


def is_new(sh, u):
    return all(w['uuid'] != u for w in sh.wires) and all(i != u for *_, i in sh.points)


CHECK_PAD = ovl.PAD   # the checker's own clearance: must never get worse
TIDY_PAD = 0.45       # stricter text clearance, so moved text never ends up touching


def tidy(path):
    return _tidy(path)


def _tidy(path):
    text = Path(path).read_text()
    cur = [count_overlaps(text)]          # the score only ever goes down
    done = {'two_pin': 0, 'test_point': 0, 'power': 0, 'fields': 0, 'skipped': []}

    def attempt(planner, *args):
        nonlocal text
        sh = Sheet(text)
        res = planner(sh, *args)
        if not res:
            return False
        ed, moved, pts, wu = res
        new = ed.apply()
        if new_contacts(sh, new, moved, pts, wu):
            return None
        for mu in moved:
            if not sh.syms[mu]['power'] and SMALL.match(sh.syms[mu]['ref']):
                new = place_fields(new, mu, None) or new
        score = count_overlaps(new)
        if not no_worse(score, cur[0]):
            return None
        text = new; cur[0] = score
        return True

    for rule, planner, stubs in (('two_pin', plan_two_pin, (0, 2.54, 5.08, 7.62, 10.16, 12.7)),
                                 ('test_point', plan_test_point, (0,))):
        for u in list(Sheet(text).syms):
            sh = Sheet(text)
            if u not in sh.syms or sh.syms[u]['power']:
                continue
            for st in stubs:
                r = attempt(lambda s, uu=u, k=st: planner(s, s.syms[uu], k) if k else planner(s, s.syms[uu]))
                if r is not None:
                    break
            if r:
                done[rule] += 1
            elif r is None:
                done['skipped'].append(sh.syms[u]['ref'])
    for u in list(Sheet(text).syms):
        sh = Sheet(text)
        if not sh.syms[u]['power']:
            continue
        if points_dir(sh.syms[u]) == want_dir(sh.syms[u]):
            attempt(lambda s, uu=u: plan_power(s, s.syms[uu], 0))
            continue
        for stub in [0] + [2.54 * k for k in range(1, 5)]:   # longer stubs read worse than a sideways symbol
            r = attempt(lambda s, uu=u, st=stub: plan_power(s, s.syms[uu], st))
            if r:
                done['power'] += 1; break
        else:
            done['skipped'].append(sh.syms[u]['value'] + '@' + sh.syms[u]['ref'])
    # stacked sideways symbols of one rail: share one symbol
    while True:
        sh = Sheet(text)
        progress = False
        for group in chains(sh):
            for stub in [2.54 * k for k in range(1, 9)]:
                g = [sh.syms[s['uuid']] for s in group]
                if attempt(lambda s, gg=g, st=stub: plan_chain(s, [s.syms[x['uuid']] for x in gg], st)):
                    done['power'] += len(group); progress = True
                    done['skipped'] = [k for k in done['skipped'] if k.split('@')[-1] not in {x['ref'] for x in group}]
                    break
            if progress:
                break
        if not progress:
            break
    # whatever still points sideways: its text past the tip
    for u in list(Sheet(text).syms):
        sym = Sheet(text).syms[u]
        if sym['power'] and points_dir(sym) in 'LR':
            attempt(lambda s, uu=u: plan_sideways_text(s, s.syms[uu]))
    # repair: a power symbol still in an overlap gets a longer wire (house way first, then sideways)
    for ref in sorted(in_overlap(text)):
        sh = Sheet(text)
        u = next((s['uuid'] for s in sh.syms.values() if s['ref'] == ref), None)
        if not u:
            continue
        for stub in [2.54 * k for k in range(1, 5)]:
            if attempt(lambda s, uu=u, st=stub: plan_power(s, s.syms[uu], st)):
                break
            if attempt(lambda s, uu=u, st=stub: plan_sideways_text(s, s.syms[uu], st)):
                break
    # fields last, on the final geometry
    for u in list(Sheet(text).syms):
        sym = Sheet(text).syms[u]
        if sym['power'] or not SMALL.match(sym['ref']) or len(sym['pins']) > 6:
            continue
        new = place_fields(text, u, cur[0])
        if new and new != text:
            text = new; done['fields'] += 1; cur[0] = count_overlaps(text)
    Path(path).write_text(text)
    return done


if __name__ == '__main__':
    for f in sys.argv[1:]:
        print(f, tidy(f))
