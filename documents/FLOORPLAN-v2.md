# Floorplan v2 (placement only, no routing)

Branch layout-v2. Chosen: variant A, 170 x 130 mm, corner (80,30) in sheet coordinates (a multiple of 10). Numbers and the other variants: `floorplan-variants/TABLE.md`. Picture: `floorplan-variants/A-170x130.png`.

## Result in one paragraph
Against the head board at the owner's 4-layer plan (scorer `--layers 2`), A cuts overload from 93.7 to 33.4 tracks (15 to 10 cuts), crossings from 3701 to 2310 and HPWL from 14559.7 to 14526.8 mm; edge short stays 0; 0 of 130 part origins are off whole mm (was 128). **Overload did not go to ~0**: with only two signal layers the Hellen modules (which block both) around M1 leave the J1-to-M1 channel short of tracks. The same floorplan scores 14.3 at the old 6-layer model (head: 4.3), so the stackup is the limiter, not just the plan. Decision for the owner: accept 4 layers and expect routing trouble in the channel at sheet x 125..145, or spend two layers.

## Rules used
- Outline 170 x 130, corner (80,30). Tool cannot set the outline: `scripts/run.sh` rewrites the Edge.Cuts gr_rect with one regex before `kicad-pcb-from-netlist` runs.
- Origins on whole mm, rotations 0 or 90, same-kind parts on one pitch (driver block 9 x 10 mm, 5 columns x 2 rows), grid origin = board corner.
- H1-H4 at inset 4 mm (not 5): at 5 the H3 courtyard overlaps the J1 courtyard by 0.15 mm.
- J1 (TE 1-1376430-0, footprint unchanged) on the left, origin board (7,13). J2 (USB-C, rot 90) flush on the right edge, J3 (Mini-Fit, CAN/aux) within 6 mm of the right edge.
- M3 is `hellen-one-wbo-0.6:wbo` (verified in the board file). No module or connector is within 8 mm of M1 (measured on the board with pcbnew: nearest non-passive is 10.6 mm; margins to the board edge 48.75 / 78.7 / 25.9 / 63.75 mm left, right, top, bottom). Its own test points (P*), jumpers and R/C parts sit 1.0 to 1.8 mm away on purpose; they are what the signals leave through.
- Stackup: F.Cu signal, In1.Cu GND (power), In2.Cu +12V_RAW (mixed), B.Cu signal, set with `kicad-stackup JLC04161H-7628` and checked in the board file. `copper_layers 4` in pcb_place.json.
- Passives: placed by the tool next to their anchor, then `scripts/snap.py` moves them to the nearest free whole mm (clearance 0.25, edge 0.75). None is left on a half mm in A. The tool only snaps to 0.25 mm by itself, hence the post-step.
- `kicad-pcb-from-netlist` run without `--keep-placed`, with `KICAD_LIB=$HOME/kicad-lib-sti` (branch sti2004-parts holds the fuse footprint the board needs).

## Zone map (board coordinates, mm; sheet = board + (80,30))
J1 left (7,13). M2 (38,11) top-left. M1 (49,66) centre-left, 8 mm free all round. Inputs and analog (M5 (85,103), M8 (94,101), U20 (68,86)) below and right of M1. G1 proto area (109,68). M14 (power) is at (103,22), not near J1's power pins: the power-near-J1 rule was not met and has not been checked. Q16 (146,83) and driver block U10-U19 (origin (106,114), bottom right) feed J1's outputs; M3 WBO (123,105) bottom middle-right; J3 (157,105) and J2 (165,35) on the right edge.

## Checks (board in repo root)
- Stock `kicad-cli pcb drc --all-track-errors --severity-all --schematic-parity` with project files beside the board: no courtyard, hole or edge violations. Types present: padstack 199, silk_overlap 199, silk_over_copper 99, text_height 1 (all also on head, silk 87 on head), lib_footprint_issues 119 ("library EmbeddedEra_Library not in the configuration": the docker kicad-cli has no global fp-lib-table; head showed 42 as it was run with the library; UNVERIFIED that this is the only cause), unconnected 327 (no routing yet; head 123 after routing).
- Parity: 61 `footprint_symbol_field_mismatch` (IPN fields, the same 61 as on head); head's 2 footprint_symbol_mismatch and 1 net_conflict are gone. No other parity items.
- Multi-pad footprints without nets: none. `.kicad_pro` md5 unchanged.
- The previous routing is discarded (placement moved); it stays in git at 5dcc436.

## Caveats
- The optimiser (`scripts/opt.py`, simulated annealing over the real scorer's cost on an in-memory board) is approximate; the pipeline score is the truth.
- J1 face direction is UNVERIFIED: with J1 on the left at rotation 0 the mating face probably points into the board. The owner must confirm against the TE drawing and the enclosure.
- Drivers sit in a block at the bottom right, not beside the J1 pins they drive; this scored better than any beside-J1 plan I tried at 4 layers, but their outputs run a long way to J1.
- Needs the owner: enclosure envelope (170 x 130 assumed), J1 replacement (obsolete part), J1 face direction, 4 vs 6 layers.

## Reproduce
`documents/floorplan-variants/scripts/`: `opt.py W H --init plans/A.json`, `gen_place.py`, `run.sh NAME plan.json` (outline edit, tool, stackup, `snap.py` in docker kicad/kicad:10.0.5, score). The scripts expect the scratch layout under ~/eeroute/work/floorplan_v2.
