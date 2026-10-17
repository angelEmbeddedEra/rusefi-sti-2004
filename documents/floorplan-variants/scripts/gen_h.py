#!/usr/bin/env python3
"""gen_h.py PLAN.json OUT_pcb_place.json : hand plan (board mm, corner 80,30) -> pcb_place.json.
Plan: board [W,H], j1 [x,y,rot], place {REF:[x,y,rot]}, arrays [{refs,origin:[x,y],cols,pitch,rot}], hole_inset.
Template (libs, silk, clearances, planes) = the pcb_place.json of the repo next to this scripts folder."""
import json, sys, copy, pathlib
plan = json.load(open(sys.argv[1])); out = sys.argv[2]
cx, cy = 80, 30
base = json.load(open(pathlib.Path(__file__).resolve().parents[3] / 'pcb_place.json'))
W, H = plan['board']; hi = plan.get('hole_inset', 4)
cfg = {k: copy.deepcopy(v) for k, v in base.items() if k not in ('fixed', 'centred', 'arrays', 'zones')}
j = plan['j1']
fixed = {'J1': [cx + j[0], cy + j[1], j[2]],
         'H1': [cx + hi, cy + hi, 0], 'H2': [cx + W - hi, cy + hi, 0], 'H3': [cx + hi, cy + H - hi, 0], 'H4': [cx + W - hi, cy + H - hi, 0]}
for r, (x, y, rot) in plan['place'].items():
    fixed[r] = [cx + x, cy + y, rot]
cfg['fixed'] = fixed
cfg['arrays'] = [{"refs": a['refs'], "anchor": "J1", "origin": [cx + a['origin'][0], cy + a['origin'][1]],
                  "cols": a['cols'], "pitch": a['pitch'], "rot": a['rot']} for a in plan['arrays']]
cfg['zones'] = {"P": [cx + plan.get('p_zone', [W // 2, H - 5])[0], cy + plan.get('p_zone', [W // 2, H - 5])[1]]}
json.dump(cfg, open(out, 'w'), indent=1)
