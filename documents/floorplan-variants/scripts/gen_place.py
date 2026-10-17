#!/usr/bin/env python3
"""gen_place.py PLAN.json OUT_pcb_place.json [--corner 80 30] : plan (local mm, board corner = 0,0) -> pcb_place.json"""
import json, sys, copy
plan = json.load(open(sys.argv[1])); out = sys.argv[2]
cx, cy = 80, 30
if '--corner' in sys.argv: i = sys.argv.index('--corner'); cx, cy = int(sys.argv[i + 1]), int(sys.argv[i + 2])
base = json.load(open('/home/angel/rusefi-sti-2004/pcb_place.json'))   # head version (6 layer) as the template
W, H = plan['board']
cfg = {k: copy.deepcopy(v) for k, v in base.items() if k not in ('fixed', 'centred', 'arrays', 'zones', 'planes', 'copper_layers')}
cfg['copper_layers'] = 4
cfg['planes'] = [p for p in base['planes'] if p['layer'] != 'In4.Cu']
cfg['stitch']['pitch'] = 10
j1 = plan.get('j1', [6, 13]); hi = plan.get('hole_inset', 5)
fixed = {'J1': [cx + j1[0], cy + j1[1], 0],
         'H1': [cx + hi, cy + hi, 0], 'H2': [cx + W - hi, cy + hi, 0], 'H3': [cx + hi, cy + H - hi, 0], 'H4': [cx + W - hi, cy + H - hi, 0]}
for r, (x, y, rot) in plan['place'].items():
    if r == 'DRV': continue
    fixed[r] = [cx + x, cy + y, rot]
cfg['fixed'] = fixed
bx, by, brot, cols, px, py = plan['drv']
cfg['arrays'] = [{"refs": "^U1\\d$", "anchor": "J1", "origin": [cx + bx, cy + by], "cols": cols, "pitch": [px, py], "rot": brot}]
cfg['zones'] = {"P": [cx + W // 2, cy + H - 5]}
json.dump(cfg, open(out, 'w'), indent=1)
print('wrote', out)
