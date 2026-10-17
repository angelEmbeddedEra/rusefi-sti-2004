# Floorplan variants: scorer table

Scorer: `floorplan_score.py BOARD --layers N` (branch floorplan-scorer of ~/kicad-lib). `--layers 2` = F.Cu + B.Cu signal layers = the owner's 4-layer stackup (GND and +12V_RAW are planes, left out). `--layers 4` = the old 6-layer model (4 signal layers), kept only because the brief's baseline was quoted at it. Overload is in 0.40 mm tracks. All boards are placement only (no tracks). Rows run through the real pipeline (tool, outline edit, stackup, snap) and are scored from the finished board.

| Row | Board | HPWL mm | Crossings | Overload, 4-layer plan (--layers 2) | Overload, 6-layer model (--layers 4) | Edge short | Origins off whole mm | Holes off whole mm |
|---|---|---|---|---|---|---|---|---|
| baseline (head 5dcc436) | 144.6 x 113.6 (old outline) | 14559.7 | 3701 | 93.7 tracks, 15 cuts | 4.3 tracks, 1 cut | 0 | 128 | 9 |
| A (CHOSEN) portrait, J1 on the long (left) edge, WBO in a corner | 130 x 170 | 11850.2 | 2084 | 35.5 tracks, 10 cuts | 17.5 tracks, 9 cuts | 0 | 0 | 5 |
| A0 landscape, J1 on the short edge, no WBO-corner rule | 170 x 130 | 14526.8 | 2310 | 33.4 tracks, 10 cuts | 14.3 tracks, 6 cuts | 0 | 0 | 5 |
| A-land-M3 landscape with the WBO-corner rule | 170 x 130 | 14559.3 | 2395 | 44.5 tracks, 10 cuts | 22.0 tracks, 8 cuts | 0 | 1 (R45 half mm) | 5 |
| A-portrait seed 21 (fresh start) | 130 x 170 | 14641.2 | 3035 | 55.8 tracks, 16 cuts | 15.6 tracks, 6 cuts | 0 | 0 | 5 |
| B (control) | 160 x 120 | 13696.7 | 2302 | 51.4 tracks, 16 cuts | 12.8 tracks, 5 cuts | 0 | 0 | 5 |
| C (own optimised plan with M1 rotated 90; not "A rotated") | 170 x 130 | 12720.4 | 2577 | 225.6 tracks, 18 cuts | 168.1 tracks, 12 cuts | 0 | 0 | 5 |

Why A and not A0: A0 is 2.1 tracks (6 %) better at the 4-layer plan, inside the optimiser noise, but its J1 sits on a 130 mm (short) edge, which breaks the owner's "J1 on one long edge", and its WBO module sits beside the driver bank. A keeps both rules and has 18 % less HPWL and 10 % fewer crossings. A is the same envelope as 170 x 130, turned portrait (130 wide, 170 tall).

Notes
- B and C were run before the WBO-corner and J1-long-edge rules were added to the optimiser; B and C are landscape and have J1 on the short edge too.
- The brief quoted the baseline as 15.9 tracks over 5 cuts and 1.35 mm edge short at `--layers 4`. That did not reproduce on head 5dcc436: measured 4.3 over 1 cut and edge short 0.
- Holes off whole mm = 5 in every variant: library peg holes of J1 and J2 (not ours to round).
- Numbers come from the real pipeline output (`score.json` of each run in ~/eeroute/work/floorplan_v2/runs), not from the optimiser's approximate model, which under-reports overload by roughly 1.5 to 2x (A: model 3.9 vs real 35.5).
- Files in this folder: `A0-170x130-landscape.pcb_place.json`, `A-portrait-s21.pcb_place.json`, `B-160x120.pcb_place.json`, `C-170x130-M1rot90.pcb_place.json`. The chosen A is the repo-root `pcb_place.json`. `plans/*.json` are optimiser plans (A.json = chosen, A0.json = landscape); `scripts/` reproduces them.
