# Routing plan: rusefiSTI2004 rev B

Status 2026-10-13: placed, planes poured, stage 2 (high-current) routed. **320 connections to route**, DRC 0 errors, schematic parity 0.
Procedure: SOP-021 step 9 (routing order). This file is the board-specific part: which nets, which layer, which width, in which order.

## Ground rules

- **Stackup (4 layers):**
  - L1 (F.Cu): parts and signals.
  - L2 (In1.Cu): solid GND. **Never route on L2.**
  - L3 (In2.Cu): +12V_RAW plane. Short jogs are allowed, but never cut it into islands.
  - L4 (B.Cu): signals.
  - Pick the JLC04161H-7628 stackup (1.6 mm) in Board Setup before routing the USB pair; that sets its impedance.
- **45 degree corners only, never 90.**
  - Keep the router in its 45° posture (the default; `/` toggles posture and `Ctrl+/` the corner style), with free-angle mode off.
  - The design rule `45 degree corners only` (track_angle min 135) makes any bend sharper than 135° between connected segments a DRC error, so a 90° corner fails the gate.
- **Teardrops always.**
  - Every copper pad and via has curved teardrops switched on (Board Setup > Teardrops, plus the per-item flag `kicad-pcb-from-netlist` sets), including at track-width changes.
  - KiCad draws them as you route and refreshes them on zone refill. Before each stage's commit, run Edit > Edit Teardrops > Add teardrops on all.
- **Track widths come from the net classes.** Use the router's net-class width, not a hand-typed one:

  | Class | Width | Via | Typical nets |
  |---|---|---|---|
  | Default | 0.20 mm | 0.6/0.3 | on-board logic |
  | Signal_Robust | 0.25 mm | 0.6/0.3 | sensor, switch and harness signals |
  | Power_500mA | 0.40 mm | 0.7/0.35 | low-current rails |
  | Power_1A | 0.60 mm | 0.8/0.4 | injectors, solenoids |
  | Power_2A | 1.00 mm | 1.0/0.5 | heaters |
  | Power_3A | 1.25 mm | 1.0/0.5 | TGV motors |
  | Power_5A | 2.50 mm | 1.2/0.6 | ETB motor, main 12 V |
  | Ground | 0.50 mm stubs into the planes | 0.8/0.4 | GND |
  | USB2 | 0.20 mm | 0.6/0.3 | USB D+/D- |

- **Placement is frozen.** From now on, run `kicad-pcb-from-netlist --keep-placed` after any schematic change. It keeps the tracks, vias and pours.
- **Commit and push after every step below.** One commit per step, with a message naming the step and the DRC result, so a bad step can be reverted on its own.
- **Gate for every step:**
  - `kicad-cli pcb drc --refill-zones` shows 0 errors.
  - Schematic parity stays at 0.
  - Note the unconnected count in the commit message.

## Steps

Each step lists its nets, then its rules.

### 0. Before the first track

Not started.

**Nets and layers:** none; this step sets up the board.

**Rules:**
- **Enclosure:** confirm it. H1-H4 are a guess: the corners right of J1.
- **Stackup:** set JLC04161H-7628 in Board Setup > Physical Stackup.
- **Lock the anchors:** J1, J2, J3, H1-H4 and the Hellen modules, so they can't move.

### 1. Plane fan-out

Not started.

**Nets and layers:**
- Every GND pad gets a via to L2: the VNLD sources (pins 5 and 7), module GND pins, connector GND and passive GND ends.
- Every +12V_RAW pad gets a via to L3.

**Rules:**
- Put the via right at the pad, one per pad, two per power pad.
- Use the class via sizes (Ground 0.8/0.4, Power_5A 1.2/0.6).

### 2. High-current paths

Done 2026-10-13 with `kicad-autoroute` (93 segments, 8 vias, 0 bends under 135°, DRC 0 errors, unconnected 326 → 320).
To redo: `git checkout rusefiSTI2004.kicad_pcb && kicad-autoroute 'OUT_ETB+,OUT_ETB-,+12V_ETB,OUT_TGV_OPEN,OUT_TGV_CLOSE,WBO_HEATER,OUT_O2_HEATER_REAR' --width-max 1.0 --passes 20`.
Open items: tracks are narrowed to 1.0 mm where the 2.5 mm Power_5A width breaks clearance (mirror them on the other layer or widen by hand); run Edit > Edit Teardrops > Add teardrops on all in the GUI (the flag is set, the shapes are made only by the editor).

**Nets and layers:**

| Path | From → to | Class |
|---|---|---|
| OUT_ETB+, OUT_ETB-, +12V_ETB | J1 pins 4/5/6 → M2 (motor driver) | Power_5A |
| OUT_TGV_OPEN, OUT_TGV_CLOSE | J1 pins 109-112 → M9 | Power_3A |
| WBO_HEATER | J1 pins 103/104 → M3 | Power_2A |
| OUT_O2_HEATER_REAR | J1 pin 68 → Q16 drain and its spreader | Power_2A |

**Rules:**
- Keep these short and straight, on L1, mirrored on L4 where width runs out.
- Use several vias at every layer change.
- Neck down only at the pad.

### 3. Low-side outputs

Not started.

**Nets and layers:**
- The 19 OUT_* nets (injectors, relays, solenoids, lamps, tach, spares): J1 pin to its VNLD5160 drain (pins 6 or 8).
- The driver inputs (INJ1-4, MAIN_RELAY …): from the 4.7k pull-down at the driver to the M1 module pin.

**Rules:**
- Drains go on L1, short, in Power_1A or Power_500mA width.
- Each VNLD source pair (5/7) is stitched straight down to L2.
- Inputs are Default width, on L4 under the bank.

### 4. Sensitive analog

Not started.

**Nets and layers:**

| Signal | From → to | Notes |
|---|---|---|
| Crank VR IN_CRANK+ / IN_CRANK- | J1 pins 76/88 → M5 | route as a pair; shield B31 to GND at the J1 end only |
| Knock IN_KNOCK_RAW | J1 pin 56 → M13 | keep away from the injector and coil traces |
| Wideband WBO_IP / WBO_UN / WBO_VM / WBO_RTRIM | J1 pins 126/127/134 → M3 | through the fitted option links |
| Sensors IN_MAF, IN_MAP, IN_IAT, IN_ECT, IN_TPS_*, IN_PPS_* | J1 → M1 | Signal_Robust |
| GND_SENSOR | J1 → JP8 | Power_500mA |
| Sensor 5 V supplies +5VAS, APS_PS_5V | J1 → power modules | |

**Rules:**
- Keep this whole group over unbroken L2 ground.
- No vias through the +12V_RAW plane next to the VR or knock traces.
- Keep it 2 mm or more from the step 2 and step 3 copper.

### 5. Differential and comms

Not started.

**Nets and layers:**
- USB_D+ / USB_D-: J2 → U1 (ESD) → M1.
- CAN_H / CAN_L: M1 → J1, J3 and M3.
- K_LINE: M10 → J1 pin 20.

**Rules:**
- **USB:** route as a 90 Ω differential pair, sized from the JLC calculator for the chosen stackup. Keep it on L1 over L2 with no vias, and match the lengths to 0.15 mm.
- **CAN:** route as a loosely coupled pair, 0.25 mm wide.
- **K-line:** Signal_Robust.

### 6. Switch and digital inputs

Not started.

**Nets and layers:**
- The IN_* switch inputs: from the J1 pin, past its pull resistor in the column beside J1, to the M1 / M11 / M12 module pin.
- The DIN_* lines from the dinput4 modules to M1.

**Rules:**
- Signal_Robust from J1 to the pull resistor, then Default on to the module.
- Run them on L4 as a bus wherever possible.

### 7. Low-current rails

Not started.

**Nets and layers:** +5V, +5VA, +3.3V, +3.3VA, +12V, +12V_IGN, +12V_BACK_UP, AUX_12V, AUX_5V, PWR_EN and PG_5VP.

**Rules:**
- Power_500mA / Power_1A width.
- Tree from the power modules (M14, M8) to each load.
- No daisy chains through dense areas.

### 8. Everything left

Not started.

**Nets and layers:** about 100 Default connections: test pads, option links, spare pads, BOOT0 and so on.

**Rules:**
- Route them by hand.
- Or use Freerouting, the KiCad community autorouter: export Specctra DSN with steps 1-7 locked, route only the unrouted nets, import the SES, then clean up.
- Never let it touch the locked tracks.

### 9. Finish

Not started.

**Nets and layers:** all pours and the whole board.

**Rules:**
- Refill all zones and add stitching vias along the board edge and around the driver bank.
- Gates:
  - unconnected must be 0
  - DRC must have 0 errors
  - `hellen-create-board` builds the package
- Then review the Gerbers and the 3D view.
- Then SOP-021 steps 10-13: second-person review, `fab.yml`, tag `hw/rusefi-sti-2004/B`.

## Connections left by class (2026-10-13)

| Class | Connections | Nets |
|---|---|---|
| Default | 100 | 69 |
| Signal_Robust | 90 | 55 |
| Power_500mA | 51 | 18 |
| Ground | 43 | 1 (most GND pads already reach a plane) |
| Power_1A | 19 | 14 |
| USB2 | 8 | 2 |
| Power_5A | 7 | 4 |
| Power_2A | 4 | 2 |
| Power_3A | 4 | 2 |
