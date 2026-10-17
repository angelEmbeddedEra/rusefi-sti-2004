# Floorplan v2 (placement only, no routing)

Branch layout-v2. Chosen: variant A, 130 wide x 170 tall (the owner's 170 x 130 envelope turned portrait so J1 sits on a long edge), corner (80,30) in sheet coordinates. Numbers and all variants: `floorplan-variants/TABLE.md`. Picture: `floorplan-variants/A-130x170.png`.

## Result
At the owner's 4-layer plan (scorer `--layers 2`) A cuts overload from 93.7 to 35.5 tracks (15 to 10 cuts), crossings from 3701 to 2084, HPWL from 14559.7 to 11850.2 mm; edge short 0; 0 of 130 part origins off whole mm (head: 128). **Overload did not go to ~0.** With two signal layers and Hellen modules that block both, the channels stay short of tracks. The same floorplan scores 17.5 at the old 6-layer model (head 4.3), so the stackup is the limiter. Decision for the owner: accept 4 layers and expect a hard route, or add two layers.

## Rules used
- Outline 130 x 170, corner (80,30). The tool cannot set the outline: `scripts/run.sh` rewrites the Edge.Cuts gr_rect with one regex before `kicad-pcb-from-netlist`.
- Origins whole mm, rotations 0 or 90, grid origin = board corner. Driver block U10-U19: 2 columns x 5 rows, pitch 9 x 9. H1-H4 at inset 4 (at 5 the H3 courtyard overlaps J1's by 0.15 mm).
- J1 (TE 1-1376430-0, footprint unchanged) on the left long edge, origin board (7,37). J2 (USB-C, rot 90) flush on the right edge at board (125,32), J3 (Mini-Fit) at (118,88) within 6 mm of the right edge.
- M3 is `hellen-one-wbo-0.6:wbo` (board file; library table `fp-lib-table` line 29 points to hellen-one/modules/wbo/0.6), at board (13,165): bottom-left corner, 20 mm or more from the driver bank (enforced in the optimiser).
- M1 at (44,66): no module or connector within 8 mm (nearest M2 10.6, M10 10.6, J1 9.9 mm, measured with pcbnew on the board). Its own test points, jumpers and R/C parts (P14-P27, R1/R2, C1, JP8/JP9...) sit 1.2 to 1.4 mm from it, put there by the tool's passive rule, not by design; the 8 mm rule holds for modules and connectors only.
- Stackup: F.Cu signal, In1.Cu GND, In2.Cu +12V_RAW (mixed), B.Cu signal via `kicad-stackup JLC04161H-7628`, read back from the board file. `copper_layers 4` in pcb_place.json.
- Passives: placed by the tool, then `scripts/snap.py` moves them to the nearest free whole mm (clearance 0.25, edge 0.75), since the tool alone snaps to 0.25 mm. No half-mm passive remains in A.
- `kicad-pcb-from-netlist` run without `--keep-placed`, with `KICAD_LIB=$HOME/kicad-lib-sti` (branch sti2004-parts holds the fuse footprint the board needs).

## Zone map (board mm; sheet = board + (80,30))
J1 left. M2 (48,15), M8 (15,23), M10 (79,15), M14 (100,23), M9 (114,50), M11 (124,21) along the top and upper right. M1 centre (44,66). Inputs: M13 (43,89), M5 (86,107), U20 (69,84). Driver bank (origin (93,87)) and Q16 (117,102) on the right middle by J3. G1 proto (114,130). WBO M3 bottom-left corner. J2 and J3 on the right (far) edge.

## Not met or not checked
- Drivers are not beside the J1 pins they drive; they sit on the far side of M1's lower right. The optimiser preferred this at 4 layers; I have no run that proves a beside-J1 bank is worse on this outline.
- Power input and regulators are not near J1's power pins (M14 at board (100,23)); not checked against the schematic.
- J1 face direction: UNVERIFIED (with J1 on the left at rotation 0 the mating face probably points into the board).

## Checks (board in repo root)
Stock `kicad-cli pcb drc --all-track-errors --severity-all --schematic-parity` (docker kicad/kicad:10.0.5, project files beside the board), run on head 5dcc436 with the same command for comparison:

| | head 5dcc436 | A |
|---|---|---|
| courtyard / hole / edge violations | none | none |
| padstack, silk_overlap, text_height | 199, 199, 1 | 199, 199, 1 |
| silk_over_copper | 87 | 105 |
| lib_footprint_issues | 130 (119 "not in the configuration" + 11 library not enabled) | 119 (same 119) |
| unconnected | 123 (routed) | 327 (unrouted) |
| parity | 64: 61 IPN field + 2 footprint_symbol_mismatch + 1 net_conflict | 61 IPN field only |

No multi-pad footprint lacks nets; `.kicad_pro` md5 unchanged. The previous routing is discarded; it stays in git at 5dcc436.

## Caveats
- The optimiser (`scripts/opt.py`, simulated annealing with the real scorer on an in-memory board) is approximate; the pipeline score is the truth.
- Needs the owner: enclosure envelope (130 x 170 assumed), J1 replacement (obsolete), J1 face direction, 4 vs 6 layers.

## Reproduce
`documents/floorplan-variants/scripts/`: `opt.py 130 170 --init plans/A.json`, `gen_place.py`, `run.sh NAME plan.json` (outline edit, tool, stackup, `snap.py` in docker, score). They expect the scratch layout under ~/eeroute/work/floorplan_v2.
