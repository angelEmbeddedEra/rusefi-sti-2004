#!/usr/bin/env python3
"""opt.py : congestion-aware floorplan SA. Scores every candidate with the REAL scorer (floorplan_score.score,
imported unmodified, fed an in-memory board). Units (modules, connectors, drivers, ...) carry their passives
as rigid clusters taken from the t1 board. Output plan json (local mm, board corner 0,0).
usage: opt.py W H --seed N --iters N --out F.json [--init plan.json] [--m1rot 90] [--t0 8] [--drvrot 0|90|any] [--j1face left]
"""
import sys, json, math, random, time, argparse, copy
sys.path.insert(0, '/home/angel/kicad-lib/scripting/pcb')
import floorplan_score as fs

F = '/home/angel/eeroute/work/floorplan_v2'
T1 = F + '/runs/t1/rusefiSTI2004.kicad_pcb'
OFF = (80, 30)
base = fs.load_board(T1)
MEAS = json.load(open(F + '/measure_t1.json'))
CLASSIFY = fs.load_classes(T1, 0.2)
DRV = ['U10', 'U11', 'U12', 'U13', 'U14', 'U15', 'U18', 'U19', 'U16', 'U17']   # array order = ascending J1 pad y (from the t1 board)
BIG = ['J1', 'J2', 'J3', 'M1', 'M2', 'M3', 'M5', 'M8', 'M9', 'M10', 'M11', 'M12', 'M13', 'M14', 'U20', 'Q16', 'G1']
HOLES = ['H1', 'H2', 'H3', 'H4']
UNITS = BIG + DRV + HOLES
parts = {p.ref: p for p in base['parts']}
HOLE_INSET = 4


def court(ref, rot):
    c = MEAS[ref]['court']
    pts = [fs.rot(x, y, rot) for x in (c[0], c[2]) for y in (c[1], c[3])]
    return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))


def abox(ref):
    p = parts[ref]
    b = court(ref, p.ang)
    return (p.x + b[0], p.y + b[1], p.x + b[2], p.y + b[3])


def boxdist(x, y, b):
    dx = max(b[0] - x, 0, x - b[2]); dy = max(b[1] - y, 0, y - b[3])
    return math.hypot(dx, dy)


# Placement model of the real tool (pcb_from_netlist.place): units are fixed; then non-anchored parts (everything that is
# not a 2-pad R/C/JP/L/D/F) go to the centroid of the pads they share small nets (<= 8 pins) with, biggest first, else the
# zone ('P' bottom middle) else the board centre; then 2-pad passives sit next to the best-priority placed part sharing a
# non-rail net (priority Q, U, F, D, J, M, P) at their t1 offset from that pad.
PRIO = ['Q', 'U', 'F', 'D', 'J', 'M', 'P']
import re as _re
netsize = {}
for p in base['parts']:
    for d in p.pads:
        if d.net:
            netsize.setdefault(d.net, set()).add((p.ref, d.name))
railish = lambda n: (not n) or len(netsize.get(n, ())) > 8 or _re.match(r'^(\+|GND|VCC|VDD)', n)
ANCH_RE = _re.compile(r'^(R|C|JP|L|D|F)\d+$')


def area(ref):
    c = MEAS[ref]['court'] if ref in MEAS else None
    return (c[2] - c[0]) * (c[3] - c[1]) if c else 0


def small_partners(ref, placed):
    out = []
    for d in parts[ref].pads:
        if not d.net or len(netsize.get(d.net, ())) > 8:
            continue
        for r2, pn in netsize[d.net]:
            if r2 != ref and r2 in placed:
                out.append((r2, pn))
    return out


def nominal_offset(p, host, ud):
    """where the tool puts a 2-pad passive relative to the anchor pad (host frame as in t1): outward from the host body
    through the pad, at the courtyard edge plus half the part, at the pad's other coordinate (collision slides ignored)"""
    hb = abox(host)
    cx0, cy0, cx1, cy1 = hb
    ccx, ccy = (cx0 + cx1) / 2, (cy0 + cy1) / 2
    dx, dy = ud.x - ccx, ud.y - ccy
    first = (1 if dx >= 0 else -1, 0) if abs(dx) * ((cy1 - cy0) or 1) >= abs(dy) * ((cx1 - cx0) or 1) else (0, 1 if dy >= 0 else -1)
    cands = [first, (-first[0], -first[1]), (first[1], first[0]), (-first[1], -first[0])]
    X0_, Y0_, X1_, Y1_ = OFF[0] + 0.5, OFF[1] + 0.5, OFF[0] + 170 - 0.5, OFF[1] + 130 - 0.5
    room = lambda o: {(1, 0): X1_ - cx1, (-1, 0): cx0 - X0_, (0, 1): Y1_ - cy1, (0, -1): cy0 - Y0_}[o]
    ox, oy = next((o for o in cands if room(o) >= 4), first)
    c = MEAS[p.ref]['court']
    L = max(c[2] - c[0], c[3] - c[1])
    gap = L / 2 + 0.35 + 0.25 + 0.05
    if ox:
        return ((cx1 + gap if ox > 0 else cx0 - gap) - ud.x, 0.0)
    return (0.0, (cy1 + gap if oy > 0 else cy0 - gap) - ud.y)


FREE1 = sorted((p.ref for p in base['parts'] if p.ref not in UNITS and not (ANCH_RE.match(p.ref) and len(p.pads) == 2)), key=lambda r: -area(r))
PULL = {}
_pl = set(UNITS)
for r in FREE1:
    PULL[r] = small_partners(r, _pl)
    _pl.add(r)
HOSTS = UNITS + FREE1
member = {u: [] for u in HOSTS}       # host -> [(passive ref, host pad name, offset)]
freepass = []                          # passives with no anchor: placed by centroid like the free parts
CLAMP = 40.0
for p in base['parts']:
    if p.ref in UNITS or p.ref in FREE1:
        continue
    best = None
    for d in p.pads:
        n = d.net
        if railish(n):
            continue
        for u in HOSTS:
            pre = _re.sub(r'\d+$', '', u)
            if pre not in PRIO:
                continue
            for ud in parts[u].pads:
                if ud.net == n:
                    key = PRIO.index(pre)
                    if best is None or key < best[0]:
                        best = (key, u, ud)
    if best:
        _, u, ud = best
        member[u].append((p.ref, ud.name, nominal_offset(p, u, ud)))
    else:
        freepass.append((p.ref, small_partners(p.ref, set(HOSTS))))
O = {u: (parts[u].x, parts[u].y, parts[u].ang % 360) for u in parts}


def mkpart(src, x, y, ang, pads):
    p = fs.Part()
    p.ref, p.lib, p.value, p.layer, p.module = src.ref, src.lib, src.value, src.layer, src.module
    p.x, p.y, p.ang, p.pads = x, y, ang, pads
    p.bbox = (min(d.x - d.hx for d in pads), min(d.y - d.hy for d in pads), max(d.x + d.hx for d in pads), max(d.y + d.hy for d in pads)) if pads else (x, y, x, y)
    return p


def move_part(src, cx, cy, da):
    """src part with its centre at (cx, cy) and turned by da degrees about its own origin"""
    pads = []
    swap = int(round(da)) % 180 != 0
    for d in src.pads:
        q = fs.Pad()
        q.fp = None; q.name = d.name; q.net = d.net; q.tht = d.tht; q.np = d.np; q.layers = d.layers
        ex, ey = fs.rot(d.x - src.x, d.y - src.y, da)
        q.x, q.y = cx + ex, cy + ey
        q.hx, q.hy = (d.hy, d.hx) if swap else (d.hx, d.hy)
        pads.append(q)
    p = mkpart(src, cx, cy, (src.ang + da) % 360, pads)
    for q in pads:
        q.fp = p
    return p


class State:
    def __init__(self, W, H, place, drv, j1):
        self.W, self.H = W, H
        self.place = {k: list(v) for k, v in place.items()}   # ref -> [x, y, rot] local, for BIG minus J1 minus DRV
        self.drv = list(drv)                                   # x, y, rot, cols, px, py
        self.j1 = list(j1)                                     # x, y (rot 0)

    def copy(self):
        return State(self.W, self.H, self.place, self.drv, self.j1)

    def unit_pos(self):
        W, H = self.W, self.H
        pos = {'J1': (self.j1[0], self.j1[1], 0)}
        for r, v in self.place.items():
            pos[r] = tuple(v)
        x, y, rot, cols, px, py = self.drv
        for i, u in enumerate(DRV):
            pos[u] = (x + (i % cols) * px, y + (i // cols) * py, rot)
        pos['H1'] = (HOLE_INSET, HOLE_INSET, 0); pos['H2'] = (W - HOLE_INSET, HOLE_INSET, 0)
        pos['H3'] = (HOLE_INSET, H - HOLE_INSET, 0); pos['H4'] = (W - HOLE_INSET, H - HOLE_INSET, 0)
        return pos


def build(st):
    pos = st.unit_pos()
    W, H = st.W, st.H
    out, boxes, built = [], {}, {}
    padpos = lambda ref, name: next(((d.x, d.y) for d in built[ref].pads if d.name == name), None)
    for u in UNITS:
        x, y, rot = pos[u]
        ox, oy, oa = O[u]
        nx, ny = x + OFF[0], y + OFF[1]
        p = move_part(parts[u], nx, ny, (rot - oa) % 360)
        out.append(p); built[u] = p
        cb = court(u, rot)
        boxes[u] = (x + cb[0], y + cb[1], x + cb[2], y + cb[3])

    def put_free(ref, tx, ty):
        c = MEAS[ref]['court'] if ref in MEAS else (0, 0, 0, 0)
        cx_, cy_ = (c[0] + c[2]) / 2, (c[1] + c[3]) / 2
        ox, oy, oa = O[ref]
        # footprints go down at rotation 0; the t1 part is turned by oa, the courtyard centre is rotated with it
        q = move_part(parts[ref], tx - cx_, ty - cy_, (-oa) % 360)
        out.append(q); built[ref] = q

    def target(ref, pulls):
        pts = [padpos(r2, pn) for r2, pn in pulls if r2 in built]
        pts = [p_ for p_ in pts if p_]
        if pts:
            return sum(p_[0] for p_ in pts) / len(pts), sum(p_[1] for p_ in pts) / len(pts)
        if _re.sub(r'\d+$', '', ref) == 'P':
            return OFF[0] + W // 2, OFF[1] + H - 5
        return OFF[0] + W / 2, OFF[1] + H / 2

    for r in FREE1:
        tx, ty = target(r, PULL[r])
        put_free(r, tx, ty)
    for h in HOSTS:
        ox, oy, oa = O[h]
        hp = built[h]
        da = (hp.ang - oa) % 360
        for m, padname, off in member[h]:
            ap = padpos(h, padname)
            fx, fy = fs.rot(off[0], off[1], da)
            q = move_part(parts[m], ap[0] + fx, ap[1] + fy, da)
            out.append(q)
    for r, pulls in freepass:
        tx, ty = target(r, pulls)
        put_free(r, tx, ty)
    board = {'path': 'MEM', 'parts': out, 'outline': (OFF[0], OFF[1], OFF[0] + st.W, OFF[1] + st.H), 'holes': []}
    return board, boxes


def penalty(st, boxes):
    W, H = st.W, st.H
    pen = 0.0
    us = [u for u in UNITS]
    for i, a in enumerate(us):
        A = boxes[a]
        for b in us[i + 1:]:
            if a in HOLES and b in HOLES:
                continue
            B = boxes[b]
            g = 8.0 if (a == 'M1' or b == 'M1') else (1.0 if (a in DRV and b in DRV) else 1.5)
            if a in HOLES or b in HOLES:
                g = 0.5
            sep = max(max(B[0] - A[2], A[0] - B[2]), max(B[1] - A[3], A[1] - B[3]))
            if sep < g:
                pen += g - sep
    for u in UNITS:
        if u in HOLES:
            continue
        A = boxes[u]
        m = 8.0 if u == 'M1' else 1.0
        l, t, r, b = (0.0 if u == 'J1' else m), m, m, m
        r_ok, b_ok = W - r, H - b
        if u == 'J2':
            r_ok, b_ok = W + 1.0, H + 1.0   # USB-C receptacle: shell may overhang the edge by up to 1 mm
        pen += max(0, l - A[0]) + max(0, t - A[1]) + max(0, A[2] - r_ok) + max(0, A[3] - b_ok)
    pen += max(0, W - 1.0 - boxes['J2'][2])     # J2 flush with the far edge (the brief: USB and CAN connectors on the far edge)
    pen += max(0, W - 6.0 - boxes['J3'][2])     # J3 (CAN / harness Mini-Fit) within 6 mm of the far edge
    # WBO (M3) in a quiet corner: courtyard within 25 mm of both nearest edges, and 20 mm clear of the driver bank
    M = boxes['M3']
    pen += max(0, min(M[0], W - M[2]) - 25.0) + max(0, min(M[1], H - M[3]) - 25.0)
    for u in DRV:
        D = boxes[u]
        sep = max(max(D[0] - M[2], M[0] - D[2]), max(D[1] - M[3], M[1] - D[3]))
        pen += max(0, 20.0 - sep)
    return pen


W_OVER, W_EDGE, W_HPWL, W_X, W_PEN = 30.0, 60.0, 0.004, 0.01, 300.0
_cache = {}


def evaluate(st, layers=2):
    board, boxes = build(st)
    fs.load_board = lambda path: board
    fs.load_classes = lambda p, t: CLASSIFY
    r = fs.score('MEM', layers)
    s = r['summary']
    pen = penalty(st, boxes)
    cost = W_OVER * s['overload_tracks'] + W_EDGE * s['edge_short_mm'] + W_HPWL * s['hpwl_mm'] + W_X * s['ratsnest_crossings'] + W_PEN * pen
    return cost, s, pen, r


def plan_of(st, s=None, pen=None, cost=None):
    d = {'board': [st.W, st.H], 'place': {k: list(v) for k, v in st.place.items()}, 'j1': list(st.j1), 'drv': list(st.drv),
         'hole_inset': HOLE_INSET, 'drv_order': DRV}
    if s:
        d['summary'] = s; d['pen'] = pen; d['cost'] = cost
    return d


def load_plan(path, W, H):
    d = json.load(open(path))
    place = {k: v for k, v in d['place'].items() if k not in ('DRV', 'J1')}
    if 'drv' in d:
        drv = d['drv']
    else:
        x, y, r = d['place']['DRV']; drv = [x, y, r, 4, 10, 9]
    j1 = d.get('j1', [6, 13] if H >= 130 else [14, 5])
    return State(W, H, place, drv, j1)


def moves(st, rng, args):
    n = st.copy()
    r = rng.random()
    step = lambda: rng.choice([-1, 1]) * rng.choice([1, 1, 2, 3, 5, 8, 13, 21])
    movable = [k for k in n.place if not (k == 'M1' and args.m1fix)]
    if r < 0.09:
        x, y, rot, cols, px, py = n.drv
        k = rng.random()
        if k < 0.5:
            x += step(); y += step()
        elif k < 0.65:
            cols = rng.choice([1, 2, 3, 4, 5, 10])
        elif k < 0.8:
            if args.drvrot == 'any':
                rot = 90 - rot
        else:
            px = rng.choice([9, 10, 11, 12]); py = rng.choice([8, 9, 10, 11, 12])
        n.drv = [x, y, rot, cols, px, py]
    elif r < 0.12:
        n.j1 = [min(max(n.j1[0] + rng.choice([-1, 0, 0, 1]), 6), 24) if args.j1side == 'left' else n.j1[0], n.j1[1] + rng.choice([-1, 1])]
    elif r < 0.17:
        u = rng.choice(movable)
        if u == 'J2' or (u == 'M1' and args.m1rot is not None):
            pass
        else:
            n.place[u][2] = 90 - n.place[u][2]
    elif r < 0.20:
        u, v = rng.sample(movable, 2)
        n.place[u][0], n.place[v][0] = n.place[v][0], n.place[u][0]
        n.place[u][1], n.place[v][1] = n.place[v][1], n.place[u][1]
    elif r < 0.22:
        u = rng.choice(movable)
        n.place[u][0] = rng.randint(10, n.W - 10); n.place[u][1] = rng.randint(10, n.H - 10)
    else:
        u = rng.choice(movable)
        if u == 'J2':       # USB-C: the shell faces +x at rot 90 (right edge) or +y at rot 0 (bottom edge); flush with that edge
            n.place['J2'][1] += step()
            return n
        if rng.random() < 0.5:
            n.place[u][0] += step()
        else:
            n.place[u][1] += step()
        if rng.random() < 0.3:
            n.place[u][0] += step()
    j = n.place['J2']
    j[0], j[2] = n.W - 5, 90      # USB-C on the far (right) edge, shell facing out
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('W', type=int); ap.add_argument('H', type=int)
    ap.add_argument('--seed', type=int, default=1); ap.add_argument('--iters', type=int, default=3000)
    ap.add_argument('--out', required=True); ap.add_argument('--init', default=F + '/sa/A_2.json')
    ap.add_argument('--m1rot', type=int, default=None); ap.add_argument('--m1fix', action='store_true')
    ap.add_argument('--t0', type=float, default=8.0); ap.add_argument('--t1', type=float, default=0.15)
    ap.add_argument('--drvrot', default='any'); ap.add_argument('--layers', type=int, default=2)
    ap.add_argument('--eval-only', action='store_true'); ap.add_argument('--j1side', default='left')
    args = ap.parse_args()
    rng = random.Random(args.seed)
    st = load_plan(args.init, args.W, args.H)
    if args.m1rot is not None:
        st.place['M1'][2] = args.m1rot
    if args.j1side == 'right':     # mirror the initial layout, J1 on the right edge (rot 0, flange flush with the edge)
        for k, v in st.place.items():
            b = court(k, v[2]) if k in MEAS else (0, 0, 0, 0)
            v[0] = args.W - v[0] - b[0] - b[2]
            if k == 'J2':
                v[:] = [args.W - 5, v[1], 90]
        st.drv[0] = args.W - st.drv[0] - 2 * 0 - 0
        st.j1 = [args.W - 28, st.j1[1]]
    st.place['J2'][0], st.place['J2'][2] = args.W - 5, 90
    # clamp the initial positions into the board
    for k, v in st.place.items():
        v[0] = min(max(v[0], 5), args.W - 5); v[1] = min(max(v[1], 5), args.H - 5)
    st.drv[0] = min(st.drv[0], args.W - 30); st.drv[1] = min(st.drv[1], args.H - 25)
    if args.drvrot in ('0', '90'):
        st.drv[2] = int(args.drvrot)
    cost, s, pen, _ = evaluate(st, args.layers)
    print('init', round(cost, 1), s['hpwl_mm'], s['ratsnest_crossings'], s['overload_tracks'], s['edge_short_mm'], 'pen', round(pen, 2), flush=True)
    if args.eval_only:
        return
    best = (cost, st.copy(), s, pen)
    cur = (cost, st)
    t0 = time.time()
    for it in range(args.iters):
        T = args.t0 * (args.t1 / args.t0) ** (it / max(1, args.iters - 1))
        cand = moves(cur[1], rng, args)
        if args.drvrot in ('0', '90'):
            cand.drv[2] = int(args.drvrot)
        c, s, pen, _ = evaluate(cand, args.layers)
        if c < cur[0] or rng.random() < math.exp((cur[0] - c) / T):
            cur = (c, cand)
            if c < best[0]:
                best = (c, cand.copy(), s, pen)
                json.dump(plan_of(best[1], s, pen, c), open(args.out, 'w'), indent=1)
        if it % 100 == 0:
            b = best
            print(it, 'T=%.2f' % T, 'cur %.1f best %.1f' % (cur[0], b[0]), 'hpwl', b[2]['hpwl_mm'], 'x', b[2]['ratsnest_crossings'], 'over', b[2]['overload_tracks'], 'cuts', b[2]['overloaded_cuts'], 'edge', b[2]['edge_short_mm'], 'pen %.2f' % b[3], '%ds' % (time.time() - t0), flush=True)
    json.dump(plan_of(best[1], best[2], best[3], best[0]), open(args.out, 'w'), indent=1)
    print('final', round(best[0], 1), best[2], 'pen', best[3])


if __name__ == '__main__':
    main()
