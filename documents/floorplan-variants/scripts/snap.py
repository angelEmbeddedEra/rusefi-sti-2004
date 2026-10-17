import pcbnew, sys, json, re, math
# snap.py BOARD PLACE.json : whole-mm origins and 0/90 rotations for the parts the placer left on 0.25 mm,
# nearest free whole-mm point (courtyard + clearance), then refill zones. Prints what it moved / could not.
MM = pcbnew.ToMM; IU = pcbnew.FromMM
bp, cfgp = sys.argv[1], sys.argv[2]
cfg = json.load(open(cfgp)); b = pcbnew.LoadBoard(bp)
skip = set(cfg.get('fixed', {})) | set(cfg.get('centred', {}))
lockre = re.compile(cfg.get('locked', '^$'))
clear = cfg.get('snap_clear', 0.25)
edge = cfg.get('snap_edge', 0.75)
ob = b.GetBoardEdgesBoundingBox()
EX0, EY0, EX1, EY1 = MM(ob.GetX()) + edge, MM(ob.GetY()) + edge, MM(ob.GetRight()) - edge, MM(ob.GetBottom()) - edge


def box(fp):
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False)
    return [MM(bb.GetX()), MM(bb.GetY()), MM(bb.GetRight()), MM(bb.GetBottom())]


fps = {f.GetReference(): f for f in b.GetFootprints()}
arrays = []
for arr in cfg.get('arrays', []):
    arrays += [r for r in fps if re.match(arr['refs'], r)]
fixed_all = [r for r in fps if r in skip or r in arrays or lockre.match(r)]
snapme = [r for r in fps if r not in fixed_all]


def ov(a, c, m):
    return a[0] < c[2] + m and c[0] < a[2] + m and a[1] < c[3] + m and c[1] < a[3] + m


taken = {r: box(fps[r]) for r in fixed_all}
bad_rot = []
moved = 0
failed = []
rot_changed = []
snapme.sort(key=lambda r: -(lambda q: (q[2] - q[0]) * (q[3] - q[1]))(box(fps[r])))
for r in snapme:
    fp = fps[r]
    rot = fp.GetOrientationDegrees() % 360
    pos = fp.GetPosition()
    x0, y0 = MM(pos.x), MM(pos.y)
    two = len(list(fp.Pads())) <= 2
    q = round(rot) % 360
    nr = {0: 0, 90: 90, 180: 0, 270: 90}.get(q, 0)
    if q in (180, 270) and not two:
        nr = q
        bad_rot.append(r)
    if q != nr:
        rot_changed.append(r)
    fp.SetOrientationDegrees(nr)
    best = None
    for rad in range(0, 21):
        cands = []
        for dx in range(-rad, rad + 1):
            for dy in range(-rad, rad + 1):
                if max(abs(dx), abs(dy)) != rad:
                    continue
                x = round(x0) + dx
                y = round(y0) + dy
                cands.append((math.hypot(x - x0, y - y0), x, y))
        cands.sort()
        for _, x, y in cands:
            fp.SetPosition(pcbnew.VECTOR2I(IU(x), IU(y)))
            bx = box(fp)
            if bx[0] < EX0 or bx[1] < EY0 or bx[2] > EX1 or bx[3] > EY1:
                continue
            if any(ov(bx, t, clear) for t in taken.values()):
                continue
            best = (x, y, bx)
            break
        if best:
            break
    if best:
        fp.SetPosition(pcbnew.VECTOR2I(IU(best[0]), IU(best[1])))
        taken[r] = best[2]
        if abs(best[0] - x0) > 1e-6 or abs(best[1] - y0) > 1e-6:
            moved += 1
    else:
        fp.SetPosition(pos)
        fp.SetOrientationDegrees(rot)
        failed.append(r)
        taken[r] = box(fp)
print(f'snapped {len(snapme)} parts, moved {moved}, rotation changed {len(rot_changed)}, '
      f'180/270 left on non-2-pad parts {bad_rot}, FAILED {failed}')
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(bp, b)
