# 2004 STI ECM: documents and pinout check

What the car's engine computer connects to, and whether this board's J1 connector matches it.

## What is in this folder

| File | What it is |
|---|---|
| `STI2004-pinout-check.xlsx` | **The cross-check.** All 135 J1 pins: the car's function, voltages and FSM page, your working label, the schematic net on each branch, what the net reaches, and a status. Built by `tools/pinout_check.py`; do not edit by hand. |
| `oem-ecm-pinout-2004-sti.csv` | The car side, transcribed from the FSM with the page for every row. This is the reference the check compares against. |
| `pinout-ECU.xlsx` | The original working sheet (design labels per pin). The check reads its labels into the "Your sheet" column. |
| `STI2004-pinout-findings.docx` | This page as a Word document (WordCraft). |
| `fsm/ecm-io-signal-table-EN-STi-18-22.pdf` | FSM *Engine Control Module I/O Signal*, pages EN(STi)-18 to 22: every ECM terminal with key-on and idle voltages. The main source. |
| `fsm/wiring-engine-electrical-WI-106.pdf` | FSM engine electrical wiring diagrams (WI-106, WI-107 and on). Used to settle the I/O table's misprints. Harness letters: A = B134, B = B135, C = B136, D = B137. |
| `fsm/wiring-cruise-control.pdf` | FSM cruise control wiring. |
| `fsm/wiring-combination-meter.pdf` | FSM combination meter wiring (tach, MIL, speed). |
| `fsm/select-monitor-led-mode-list.pdf` | Subaru Select Monitor LED-mode signal list. Not a pinout. |
| `ecm-connector-photo.jpeg` | Photo of the stock ECM's connector face. Not a pinout. |

J1 pin order: pins 1-31 are B137 (D1-D31), 32-66 are B136 (C1-C35), 67-101 are B135 (B1-B35), 102-135 are B134 (A1-A34).

## Schematic sheets

The schematic is split by function (root page `rusefiSTI2004.kicad_sch` shows the blocks). Every sheet starts with a note on what it holds and why. Signals between sheets are global net labels; power symbols are global.

| Sheet | File | Holds |
|---|---|---|
| Vehicle connector | `Connector.kicad_sch` | J1, all four ECM plugs (D=B137, C=B136, B=B135, A=B134), coil-line fuses, battery divider |
| Power | `Power.kicad_sch` | M14 main power module, M8 pedal-only 5 V |
| MCU and USB | `Mcu.kicad_sch` | M1 STM32F7 module, USB-C with ESD, BOOT0 and SWD |
| Sensors | `Sensors.kicad_sch` | crank VR (M5), knock (M13), cam pull-up options, sensor-ground selection |
| Switch inputs | `Inputs.kicad_sch` | dinput4 modules (M11, M12), pull-downs and pull-up options for every switch |
| Outputs | `Outputs.kicad_sch` | low-side driver sheets (INJ, LS1-LS4 in `INJ4.kicad_sch`), throttle (M2), TGV (M9), fuel pump options |
| Comms | `Comms.kicad_sch` | LSU 4.9 wideband (M3), K-line (M10), CAN |
| Aux and expansion | `Aux.kicad_sch` | J3 Mini-Fit Jr, its fuses, spare pins and rails on pads, prototype area |

Checks: `kicad-tidy-check` (house style on every sheet, netlist unchanged, 0 overlaps; shared tools in EmbeddedEra/KiCad `scripting/schematic`), `python3 tools/pinout_check.py` (car pinout), `python3 tools/options_table.py` (option list).

## Libraries, template and KiCad version

- **KiCad 10.** Every sheet and the board are KiCad 10 files (KiCad 10.0.7). Older KiCad cannot open them.
- **EmbeddedEra libraries only** ([[kicad-own-libraries-only]], SOP-008 section 10): every symbol and footprint comes from the EmbeddedEra library (`EmbeddedEra`, `EmbeddedEra_Generic`, `EmbeddedEra_Resistors_*`, `EmbeddedEra_Library` footprints). The one exception is the nine Hellen-One modules (`hellen-one-<module>-<rev>`), which the Hellen board generator recognises by Value and builds from rusEFI's own module files.
- New library parts for this board are on the library branch `sti2004-parts` (EmbeddedEra/KiCad): NCV8401BDTRKG, JK-nSMD005, nSMD050-24V, TE_1-1376430-0, Molex_39281143, PROTO_AREA, TestPoint_THT, power symbols, 0R jumpers, and the TO-252-2, Fuse_1206, Mini-Fit Jr 2x7 and TH test-pad footprints. Until that branch is merged, KiCad on a design machine shows "library not found" warnings for them (the schematic carries its own copies, so it opens and exports fine).
- **Template** (`template/EmbeddedEra_Project`, SOP-021 steps 1-3): EmbeddedEra worksheet (copied into the project as `EmbeddedEraTemplate003.kicad_wks` so no library path is needed), text variables (Customer, Designer, Part_Number, Revision B), the six net classes with power classes assigned by expected load (review before routing), and `EmbeddedEra_JLCPCB.kicad_dru` as the design rules (USB-C and fine-pitch Hellen modules need JLCPCB geometry). Net names follow the template: `USB_D+`/`USB_D-`, `I2C_1_SCL`/`I2C_1_SDA`, `UART_8_TX`/`UART_8_RX`.

## Re-running the check

```sh
python3 tools/pinout_check.py                       # the current checkout
python3 tools/pinout_check.py --sch master=a.kicad_sch --sch rev-b=b.kicad_sch
```

Needs `kicad-cli` and `gridcraft-cli`. The status column is judged on the last schematic given.

## Rev b wiring (branch `rev-b-wiring`, 2026-10-13)

Status on this branch: **99 OK**, 3 not wired (EVAP: fuel temperature C12, tank pressure C21, tank sensor valve A24; rusEFI has no EVAP diagnostics), 33 unused by the car.

**Fixed:** MAF/MAP swap (C23 -> IN_MAF, C22 -> IN_MAP), injector ground D7 and A34 to GND, stray D22 removed from the crank, clutch renamed from IN_CLT.

**Cam sensors are Hall, not VR** (3-wire, 12 V from the harness, open collector; WI-114). M6 (VR module) is off the LH cam; both cams go straight to pulled-up MCU inputs. M6 has been removed.

**MCU (M1) assignments for the firmware config:**

| Car pin | Signal | M1 pin | Notes |
|---|---|---|---|
| B8 | Cam LH (Hall) | IN_CAM | 2.35k pull-up on module |
| B9 | Cam RH (Hall) | IN_AUX1 | 5k pull-up |
| D9 | Neutral switch | IN_AUX2 | closes to ground |
| D10 | Power steering switch | IN_AUX3 | closes to ground |
| D8 | Starter | IN_SENS2 | 12 V when cranking; R19 4.7k pull-down |
| D16 | A/C request | IN_SENS3 | 12 V = on; R20 pull-down |
| C8 | Brake switch 2 (stop lamp) | IN_SENS4 | 12 V when pressed; R21 pull-down |
| A1 | Clutch switch | IN_RES1 | 12 V released, 0 V pressed; R22 pull-down |
| C9 | Brake switch 1 | IN_O2S2 | 12 V released, 0 V pressed; R23 pull-down |
| C23 | MAF | IN_SENS1 | |
| C22 | MAP | IN_MAP1 | |
| C26 / C27 | TGV position LH / RH | IN_MAP2 / IN_MAP3 | |
| C20 | Fuel level | IN_AT1 | muxed input, slow signal |
| D25 | Rear O2 | IN_O2S | |
| B26 | Fuel pump control unit command | IGN5 | 5 V push-pull PWM; 0 V = pump off |
| A32 | Wastegate | OUT_PWM1 -> Q9 | low-side, 12 V from harness |
| A28 / A29 | AVCS RH / LH (-) | OUT_PWM4 / OUT_PWM5 -> Q10 / Q11 | ~300 Hz; (+) A18/A19 now fed from +12V_RAW (main relay) |
| A14 | Purge | OUT_PWM7 -> Q12 | |
| A17 | Check engine lamp | OUT_IO1 -> Q13 | |
| B2 | Rear O2 heater | OUT_IO2 -> Q14 | |
| B33 | A/C relay | OUT_IO3 -> Q15 | |
| A23 | Tach | OUT_IO4 -> Q16 | open drain; add a pull-up to 12 V if the needle is dead |
| A9+A11 / A8+A10 | TGV open / close (both banks in parallel) | M9 motor driver: PWM = OUT_IO12, DIR = IO3, DIS = IO4 | owner does not use TGVs; wired anyway |

Q9-Q16 are two more copies of the 4-channel `INJ4` low-side sheet (LS2, LS3).

| C7 / C10 / C11 | Cruise main / resume / set (12 V when pressed) | IN_D1 / IN_D3 / IN_D4 | R35-R37 1k 1206 pull-downs |
| A15 / A16 | Cruise main lamp / set lamp | OUT_IO5 / OUT_IO6 -> Q17 / Q18 | sheet LS4 |
| D20 | K-line (SSM) | M10 LIN module, UART8 TX/RX | |
| A2+A3, A33, A26, A25 | LSU 4.9 (see below) | M3 WBO module, CAN to M1 CANH/CANL | |
| D11 / D12 / D13 / D14 | Defogger / small lights / blower (A/C) / test mode | M11 dinput4 -> IO5 / IO6 / IO7 / OUT_IO13 | close to ground; 680k pull-up to 5 V, R51-R53 10k options |
| D24 | Blow-by (PCV) diagnosis | M12 dinput4 ch4 -> OUT_INJ8 | |
| aux pads P29-P31 | AUX_IN1-3: launch / 2-step button, map switch, spare | M12 dinput4 ch1-3 -> OUT_IO9 / OUT_IO10 / OUT_IO11 | expect 12 V when pressed; 680k pull-down, R48-R50 4.7k options |
| USB J2 (USB-C) | TunerStudio | M1 USB D+/D-/VBUS | ESD U1 |

### Front O2: Bosch LSU 4.9 on the rusEFI WBO module (M3)

Wired like rusefi/hellen154hyundai: module LSU_H- to GND, LSU_H+ is the switched heater return, SEL1 tied to PULL_DOWN1, CAN to the MCU. Heater +12 V stays on the car harness (front sensor plug B18 pin 2, from the main relay).

The stock harness has four wires plus a shield to the front sensor, so the LSU needs an adapter pigtail at plug B18:

| Car harness | ECM pin | LSU 4.9 pin |
|---|---|---|
| B18 pin 2 (+12 V, main relay) | - | 4 H+ (grey) |
| B18 pin 1 (heater return) | A2 + A3 | 3 H- (white) |
| B18 pin 3 | A33 | 6 Un (black) |
| B18 pin 4 | A26 | 2 Vm (yellow) |
| shield drain | A25 | 1 Ip (red) |
| none | pad P4 only | 5 Rtrim (green) |

Before relying on it: confirm the A25 shield is not grounded at the sensor end (it becomes a signal wire), and whether the WBO firmware needs Rtrim. JP1-JP3 (fitted 0R) take Un/Vm/Ip to the harness; remove them and use pads P1-P5 for a direct LSU pigtail instead.

### Board-level fixes (2026-10-13)

- **M1 module ground (`GND_G`) was not connected.** Now on GND.
- **F5 (JK-nSMD005, a 50 mA PTC) was in series with the throttle motor supply** (D6 -> M2). It would have tripped as soon as the motor moved. Removed; D6 feeds +12V_ETB directly. The car fuses the throttle relay feed upstream.
- **No USB.** J2 USB-C (HRO TYPE-C-31-M-12, C165948, the EmbeddedEra library part we already build with) to the MCU USB pins, 5.1k CC pull-downs (device), USBLC6-2SC6 ESD (U1, C7519), shield to GND through a fitted 0R link. BOOT0 pad P23 with open link JP11 to 3.3 V for DFU recovery; SWD pads P24-P26 (SWDIO, SWCLK, NRST).
- **Removed unused modules:** M6 (VR, the cams are Hall) and M4 (CAN; M1 has its own transceiver). Their MCU pins OUT_PWM3 and IN_RES2 are on pads P27/P28.
- **More inputs:** two Hellen dinput4 modules (M11, M12) on spare 5 V-tolerant GPIOs. An I2C expander was considered: rusEFI has no driver for I2C input expanders, and its one supported switch-input chip (MC33972, SPI) is obsolete. I2C SCL/SDA are on pads in case an expander is added later.
- Spare 5 V push-pull outputs IGN6-8 on pads.
- **Pedal 5 V is now its own rail.** The pedal supply C15 (net APS_PS_5V) comes from the second power module M8's protected 5 V; the throttle/MAP/TGV sensor supply C16 stays on M14 (+5VAS). A shared rail would let one short take out both pedal and throttle sensors and defeat their plausibility check. JP12 (open) puts the pedal back on +5VAS if M8 is not fitted; M8's power-good is on pad P32.
- **CAN termination:** M1 already has 120R across CANH/CANL (R100 on mega-mcu144 sheet 15); the WBO module has none. R54 (120R, DNP) at the aux connector terminates the far end if an external device on the aux CAN does not.
- **Low-side drivers Q1-Q20 are onsemi NCV8401BDTRKG** (was ST VND14NV04-E, obsolete: Digi-Key 0, LCSC 1 left). Same DPAK pinout (1 IN, 2/tab drain, 3 source) and footprint; protected like the VND14: 42-50 V active clamp for inductive loads, current limit 25-35 A, thermal shutdown with auto-restart, AEC-Q101. RDS(on) about 28 mOhm at 5 V and about 37 mOhm at 3.3 V drive. The current limit is higher than the VND14's (12-24 A), so a shorted harness wire draws more before it trips. Not stocked at LCSC/JLC: buy from Digi-Key/Mouser and consign. Bench-check one channel driven from the 3.3 V MCU before trusting all 20.
- **PCB (2026-10-13): 4 layers, every part on top, placed, not routed.** 4 layers because the Hellen modules carry inner copper (the MCU module has In1/In2) and the Hellen build assumes 4: Planes: In1 solid GND; In2 solid +12V_RAW (the highest-current rail: J1 to both power modules, TGV driver, WBO, fuses); top and bottom GND pours with 41 stitching vias; every DPAK has a drain-net heat spreader on top and bottom joined by 6 thermal vias. Hellen module rule areas keep all pours out of the modules. J1, J3 and the test pads drop their unused inner pad rings so the planes flow between the dense J1 pins. The 5 V / 3.3 V rails (< 0.5 A, spread out) and +12V_ETB stay as tracks. All parts on top: one stencil, one reflow pass at JLC, bottom free for probing; there is room to space everything out. Floorplan: J1 left; the 20 low-side drivers in a 4x5 bank beside it ordered by the J1 pin they drive (13.5 x 10 mm pitch, routing channels between); power modules top right; MCU right with a 5 mm channel to the bank; USB-C right edge; J3 top edge; sensor/input modules lower left; proto area and test pads lower right. References are JLC-size (1.0 mm / 0.15 mm) on silk with no overlaps; values on the fab layer; three option jumpers (JP4, JP9, JP11) have no free spot and carry their reference on Fab only. DRC: 0 errors (scoped exceptions in rusefiSTI2004.kicad_dru for the J2 USB-C pitch, the Hellen knock module and J1 GND spokes), schematic parity 0. Regenerate with `kicad-pcb-from-netlist` (layout in `pcb_place.json`; use `--keep-placed` once routing starts).
- **Mounting:** H1-H4, M3 plated holes with no net, in the four corners of the area right of J1. J1's own three screws hold the connector only. Move them if the case needs other positions.
- Removed M7 (second knock module): the STI has one knock sensor (C25), read by M13.

### Aux connector J3: Molex Mini-Fit Jr 2x7 (5566-14A vertical, Molex 39281143)

Mating plug: Molex 39-01-2140 (5557-14R housing) with 39-00-0038 crimp terminals (5556, 18-24 AWG). Footprint `STI:Molex_Mini-Fit_Jr_5566-14A_2x07_P4.20mm_Vertical` (copied from the KiCad 8.0.7 library). Through-hole, no LCSC number: hand-solder or order THT assembly; a right-angle 5569-14A footprint can be swapped in if the case needs it.

| Pin | Signal | Pin | Signal |
|---|---|---|---|
| 1 | +12 V out (main relay, F6 0.5 A PTC) | 2 | GND |
| 3 | +5 V sensor out (+5VAS, F7 50 mA PTC) | 4 | Sensor ground (GND_SENSOR) |
| 5 | AUX_IN1 digital (launch / 2-step) | 6 | AUX_IN2 digital (map switch) |
| 7 | AUX_IN3 digital (spare, flex fuel frequency OK) | 8 | AUX_AN1 analog 0-5 V (IN_RES2, 340k) |
| 9 | AUX_AN2 analog (IN_AT2, 2.35k pull-up: thermistor-ready) | 10 | AUX_OUT1 low-side (LS4 ch3) |
| 11 | AUX_OUT2 low-side (LS4 ch4) | 12 | CAN H |
| 13 | CAN L | 14 | GND |

AUX_IN1-3 expect a switch to 12 V (680k pull-down on the dinput4, R48-R50 4.7k options). AUX_AN2 shares IN_AT2 with the FPCU status option JP7: fit only one. AUX_OUT1/2 also reach EVAP A12/A13 through open JP5/JP6.

### Option parts (footprints on the board)

Generated from the schematic by `python3 tools/options_table.py` (re-run after any change). "Not fitted" parts are marked DNP in KiCad and listed in `bom_replace_rusefiSTI2004-a.csv`, Hellen's removal list: delete a part's line there to have it assembled.

| Sheet | Ref | Value | Joins | Default | When to fit / remove |
|---|---|---|---|---|---|
| Aux | JP7 | 0 | AUX_AN2 / FP_STATUS | not fitted | read the FPCU status on IN_AT2 (then do not use AUX_AN2) |
| Aux | R48 | 4.7K | AUX_IN1 / GND | not fitted | aux input 1 floats: stronger pull-down |
| Aux | R49 | 4.7K | AUX_IN2 / GND | not fitted | aux input 2 floats: stronger pull-down |
| Aux | R50 | 4.7K | AUX_IN3 / GND | not fitted | aux input 3 floats: stronger pull-down |
| Comms | JP1 | 0 | WBO_UN / WBO_UN_J1 | fitted | FITTED: LSU Un through the harness (remove for a pigtail on the pads) |
| Comms | JP2 | 0 | WBO_VM / WBO_VM_J1 | fitted | FITTED: LSU Vm through the harness |
| Comms | JP3 | 0 | WBO_IP / WBO_IP_J1 | fitted | FITTED: LSU Ip through the harness (A25 shield wire) |
| Comms | JP4 | 0 | DLC6_D29 / K_LINE | not fitted | D29 turns out to be a second K-line |
| Comms | R54 | 120 | CAN_H / CAN_L | not fitted | external CAN device that does not terminate the bus |
| Inputs | R44 | 4.7K | GND / IN_NEUTRAL_SWITCH | not fitted | neutral switch turns out to be 12 V-active |
| Inputs | R45 | 1K | +5VA / IN_FUEL_LEVEL | not fitted | tune the fuel gauge reading |
| Inputs | R51 | 10K | +5V / IN_DEFOG | not fitted | defogger line floats when off: stronger pull-up |
| Inputs | R52 | 10K | +5V / IN_SMALL_LIGHT | not fitted | lights line floats when off: stronger pull-up |
| Inputs | R53 | 10K | +5V / IN_BLOWER | not fitted | blower line floats when off: stronger pull-up |
| Mcu | JP10 | 0 | GND / USB_SHIELD | fitted | FITTED: USB shell to GND (remove to float the shell) |
| Mcu | JP11 | 0 | +3.3V / BOOT0 | not fitted | bridge to force the USB DFU bootloader |
| Outputs | JP5 | 0 | EVAP_A12 / OUT_SPARE_LS1 | not fitted | drive EVAP A12 from spare low-side 1 |
| Outputs | JP6 | 0 | EVAP_A13 / OUT_SPARE_LS2 | not fitted | drive EVAP A13 from spare low-side 2 |
| Outputs | R38 | 2.2k | +12V_RAW / OUT_TACH | not fitted | tach needle dead: pull-up to 12 V |
| Outputs | R39 | 100 | FP_CMD / FUEL_PUMP_SIGNAL1 | fitted | FITTED: series protection on the FPCU command |
| Outputs | R40 | 1K | +5V / FUEL_PUMP_SIGNAL1 | not fitted | FPCU input needs a pull-up (scope the stock ECM first) |
| Outputs | R41 | 10K | FUEL_PUMP_SIGNAL1 / GND | not fitted | FPCU input needs a pull-down |
| Power | JP12 | 0 | +5VAS / APS_PS_5V | not fitted | only if M8 is not fitted: pedal back on the shared sensor 5 V |
| Sensors | JP8 | 0 | GND / GND_SENSOR | fitted | FITTED: sensor returns to GND (remove to move them to GNDA) |
| Sensors | JP9 | 0 | GNDA / GND_SENSOR | not fitted | sensor returns on analog ground instead of GND |
| Sensors | R42 | 1K | +5VA / IN_CAM | not fitted | stronger pull-up, LH cam (weak or noisy signal) |
| Sensors | R43 | 1K | +5VA / IN_CAM_RH | not fitted | stronger pull-up, RH cam |

Pads (no assembly cost): LSU 4.9 and CAN on the Comms sheet; K-line, D29 and A22 charging wire; spare low-side outputs and FPCU status on Outputs; BOOT0 and SWD on MCU and USB; spare MCU pins (IGN6-8, I2C, OUT_PWM3, IN_RES2), aux inputs, M8 power-good and every rail on the Aux sheet, next to the prototype area G1.

**Next:** in KiCad, *Update PCB from Schematic* with **Re-link footprints to schematic symbols based on their references** ticked (the sheet split changed every symbol's sheet path), then place and route the new parts (everything not yet on the board: Q9-Q20 and R11-R22 in the low-side sheets, R30-R54, JP1-JP12, F6-F7, P1-P32, M10-M12, J2, U1, J3, G1; M8 now wired).

## Findings (2026-10-13, master vs `rev-b-schematic-fixes`)

Status counts on rev-b: 47 OK, 3 mismatch, 16 label only, 34 not wired, 3 to check, 32 unused by the car.

### Wrong today (fix in the schematic)

1. **MAF and MAP are swapped.** J1 pin 54 is C23, the *mass air flow* signal, but carries `IN_MAP` into the MCU's MAP input. The MAP sensor is C22 (pin 53), which is not connected. The 2004 STI meters by MAF (C23) and also has a MAP sensor (C22): wire C23 to a MAF analog input and C22 to `IN_MAP`.
2. **Injector ground is floating.** D7 (pin 7), *GND (injectors)*, is the net `GND_INJECTORS`, which connects to nothing else. Tie it to GND.
3. **Pin 22 is tied to the crank sensor.** Pin 22 is D22, which the car does not use, yet it is on `IN_CRANK-` with the real crank (-) at B22 (pin 88). Looks like a pin-number slip; remove it.
4. **The clutch switch is called `IN_CLT`.** A1 (pin 102). In rusEFI `CLT` means coolant temperature, so this will be wired to the wrong input. Rename it `IN_CLUTCH` and give it a digital input. Your working sheet has the same label.

### Fixed by rev-b (still true on master)

Ignition coils 1, 3 and 4 shorted together; second VR channel paralleled on the crank (now reads the LH cam, B8); sensor 5 V (C15, C16) floating; vehicle speed (B27) not reaching the MCU.

### Named but not connected to the MCU (16 pins)

The net has the right name at J1 and stops there: starter switch D8, neutral D9, power-steering switch D10, fuel pump control unit D28 and B26, fuel level C20, TGV position sensors C26 and C27, RH cam B9, purge A14, AVCS (VVT) solenoids A18/A28 and A19/A29, tach A23, wastegate A32. Each needs a module input or output.

### The car uses these, the schematic does not (34 pins)

- **Needed to run:** front A/F sensor (A33 signal +, A26 signal -, A25 shield, heaters A2/A3, heater grounds already on GND). The stock sensor is a **Denso 4-wire A/F** (plug B18: heater +12 V from the main relay, heater return to A2 and A3 joined in the harness, signal A33/A26), not a Bosch LSU, so the Hellen WBO module cannot read it as is: either fit an LSU 4.9 or add a Denso A/F interface. Decision needed.
- **Needed for a clean dash and emissions:** MIL A17, rear O2 signal D25 and heater B2, brake switches C8/C9, TGV motors A8-A11 (or a TGV delete), A/C request D16 and A/C relay B33.
- **Optional:** SSM/K-line D20, cruise (C7, C10, C11, A15, A16), EVAP (A12, A13, A24, C12, C21), test mode D14, defogger/lights/blower load inputs D11-D13, blow-by diagnosis D24.
- **Ground:** A34 is joined to the D1/D2 grounds on WI-107; tie it to GND.

### Check

- D29 is not in the I/O table; WI-112 shows a red/white wire to data link connector pin 6. Leave it unconnected.
- A22 is not in the I/O table, but WI-111 shows a blue wire to the charging system (CHG-01). It is not a spare pin: do not ground or drive it, and measure it on the car.
- Sensor returns (C31, C34, C35, D3) are on the power GND. rusEFI boards usually return sensors to an analog ground; worth a look before layout.

### Errors in the sources

- The FSM I/O table prints ignition #3 and #4 both as B135 16. The wiring diagram (WI-107) shows B15 to coil 4; the check uses B15.
- The FSM I/O table prints A/C relay control as "B133 33". There is no B133 on this ECM; WI-106 shows B33 to the auto A/C module, so it is B135 33.
- The working sheet `pinout-ECU.xlsx` notes "A/C relay control" on the B22 row (crank signal -); it belongs on B33. It also leaves A34 (ground) blank.

## Independent verification (2026-10-13)

A second agent (Claude Fable, read-only) rebuilt all 135 terminals from the FSM pages without seeing this table, then compared. 134 of 135 rows agreed; the one difference was A22 (wired to the charging system, now recorded), plus the A/F sensor wire count (4, not 5, now fixed).

- **Model year:** consistent with the 2004 USDM STI: four ECM plugs (135 terminals), drive-by-wire with ETC relay, dual AVCS, TGVs, MAF plus MAP, fuel pump control unit, USDM EVAP, Denso 4-wire A/F, no immobilizer line. The I/O table PDF is dated 2003-05-12. rusEFI's documentation files the byte-identical table as "2005-2007 GDA/GDB"; the community and plug-in ECU makers treat 2004-2006 USDM STI pinouts as the same.
- **Plug letters** A = B134, B = B135, C = B136, D = B137 are printed on WI-108, WI-111 and WI-113 and match the pin-grid drawings.
- **Community disagreement:** rusEFI's [2005 STI EJ257 pinout](https://github.com/rusefi/rusefi_documentation/blob/master/OEM-Docs/Subaru/2005-Subaru-Impreza-WRX-STi-EJ257-ECM-pinout.md) (from a Mitchell diagram) swaps D14/D15 and B26/B27, and flags them itself for on-car checking. The FSM table and wire colours on WI-108/109/112 support this table (D14 test mode, D15 ignition switch, B26 fuel pump control unit, B27 vehicle speed). Confirm these four with a meter before power-up.
- **Not usable:** the allpinouts.org "2004 STI ECU" page is a 2002-03 WRX layout (five connectors, wrong pin counts).
- **Could not verify from documents:** the function of A22 and D29, and the physical polarity of the throttle motor pins D4/D5.
