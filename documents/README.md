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

## Re-running the check

```sh
python3 tools/pinout_check.py                       # the current checkout
python3 tools/pinout_check.py --sch master=a.kicad_sch --sch rev-b=b.kicad_sch
```

Needs `kicad-cli` and `gridcraft-cli`. The status column is judged on the last schematic given.

## Rev b wiring (branch `rev-b-wiring`, 2026-10-13)

Status on this branch: **78 OK**, 21 not wired (optional loads, plus the front A/F sensor awaiting a decision), 33 unused by the car, 2 to check (D29, A22, both left open on purpose), 1 label only (D28 fuel pump control unit status, not needed to run).

**Fixed:** MAF/MAP swap (C23 -> IN_MAF, C22 -> IN_MAP), injector ground D7 and A34 to GND, stray D22 removed from the crank, clutch renamed from IN_CLT.

**Cam sensors are Hall, not VR** (3-wire, 12 V from the harness, open collector; WI-114). M6 (VR module) is off the LH cam; both cams go straight to pulled-up MCU inputs. M6 is now unused.

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

**Next:** in KiCad, *Update PCB from Schematic*, then place and route the new parts (Q9-Q16, R11-R23).

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
