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

## Findings (2026-10-13, master vs `rev-b-schematic-fixes`)

Status counts on rev-b: 47 OK, 3 mismatch, 16 label only, 34 not wired, 2 to check, 33 unused by the car.

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

- **Needed to run:** front A/F sensor (A33 signal +, A26 signal -, A25 shield, heaters A2/A3, heater grounds already on GND). The stock sensor is a **Denso 5-wire A/F**, not a Bosch LSU, so the Hellen WBO module cannot read it as is: either fit an LSU 4.9 or add a Denso A/F interface. Decision needed.
- **Needed for a clean dash and emissions:** MIL A17, rear O2 signal D25 and heater B2, brake switches C8/C9, TGV motors A8-A11 (or a TGV delete), A/C request D16 and A/C relay B33.
- **Optional:** SSM/K-line D20, cruise (C7, C10, C11, A15, A16), EVAP (A12, A13, A24, C12, C21), test mode D14, defogger/lights/blower load inputs D11-D13, blow-by diagnosis D24.
- **Ground:** A34 is joined to the D1/D2 grounds on WI-107; tie it to GND.

### Check

- D29 is not in the I/O table, but WI-107 draws a line from it toward the data link connector. Confirm on the car before using it.
- Sensor returns (C31, C34, C35, D3) are on the power GND. rusEFI boards usually return sensors to an analog ground; worth a look before layout.

### Errors in the sources

- The FSM I/O table prints ignition #3 and #4 both as B135 16. The wiring diagram (WI-107) shows B15 to coil 4; the check uses B15.
- The FSM I/O table prints A/C relay control as "B133 33". There is no B133 on this ECM; WI-106 shows B33 to the auto A/C module, so it is B135 33.
- The working sheet `pinout-ECU.xlsx` notes "A/C relay control" on the B22 row (crank signal -); it belongs on B33. It also leaves A34 (ground) blank.
