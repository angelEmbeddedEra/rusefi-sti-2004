# Floorplan variants: scorer table

Scorer: `floorplan_score.py BOARD --layers N` (branch floorplan-scorer of ~/kicad-lib). `--layers 2` = F.Cu + B.Cu signal layers = the owner's 4-layer stackup (GND and +12V_RAW are planes, left out). `--layers 4` = the old 6-layer model (4 signal layers), kept only because the brief's baseline was quoted at it. Overload is in 0.40 mm tracks. All boards are placement only (no tracks).

| Row | Board | HPWL mm | Crossings | Overload, 4-layer plan (--layers 2) | Overload, 6-layer model (--layers 4) | Edge short | Origins off whole mm | Holes off whole mm |
|---|---|---|---|---|---|---|---|---|
| baseline (head 5dcc436, 6-layer era) | 144.6 x 113.6 (old outline) | 14559.7 | 3701 | 93.7 tracks, 15 cuts | 4.3 tracks, 1 cut | 0 | 128 | 9 |
| A (CHOSEN) | 170 x 130 | 14526.8 | 2310 | 33.4 tracks, 10 cuts | 14.3 tracks, 6 cuts | 0 | 0 | 5 |
| B (control) | 160 x 120 | 13696.7 | 2302 | 51.4 tracks, 16 cuts | 12.8 tracks, 5 cuts | 0 | 0 | 5 |
| C (A with M1 rotated 90) | 170 x 130 | 12720.4 | 2577 | 225.6 tracks, 18 cuts | 168.1 tracks, 12 cuts | 0 | 0 | 5 |

Notes
- The brief quoted the baseline as 15.9 tracks over 5 cuts and 1.35 mm edge short at `--layers 4`. That did not reproduce on head 5dcc436: measured 4.3 over 1 cut and edge short 0.
- Holes off whole mm = 5 in every variant: library peg holes of J1 and J2 (not ours to round).
- The numbers in the table come from the real pipeline output (`runs/<name>/score.json` in the scratch dir ~/eeroute/work/floorplan_v2), not from the optimiser's own approximate model, which under-reports overload by about 1.5 to 2x.
- Variant pcb_place.json files in this folder: `B-160x120.pcb_place.json`, `C-170x130-M1rot90.pcb_place.json`. The chosen A is the repo-root `pcb_place.json`. `plans/*.json` are the optimiser plans they were generated from; `scripts/` reproduces everything (see FLOORPLAN-v2.md).
