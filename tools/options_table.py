#!/usr/bin/env python3
"""Print the option-parts table (markdown) straight from the schematic, so references never go stale.

    python3 tools/options_table.py

An option is a part marked DNP, or a fitted 0R link / pull resistor listed in WHY below. For each it shows
the sheet, value, the two nets it joins and when to fit (or remove) it.
"""
import re, subprocess, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# When to fit / remove, keyed by the pair of nets a part joins (order-free). Unknown pairs print "-".
WHY = {
    frozenset({'OUT_TACH', '+12V_RAW'}): 'tach needle dead: pull-up to 12 V',
    frozenset({'FUEL_PUMP_SIGNAL1', '+5V'}): 'FPCU input needs a pull-up (scope the stock ECM first)',
    frozenset({'FUEL_PUMP_SIGNAL1', 'GND'}): 'FPCU input needs a pull-down',
    frozenset({'FP_STATUS', 'AUX_AN2'}): 'read the FPCU status on IN_AT2 (then do not use AUX_AN2)',
    frozenset({'IN_CAM', '+5VA'}): 'stronger pull-up, LH cam (weak or noisy signal)',
    frozenset({'IN_CAM_RH', '+5VA'}): 'stronger pull-up, RH cam',
    frozenset({'IN_NEUTRAL_SWITCH', 'GND'}): 'neutral switch turns out to be 12 V-active',
    frozenset({'IN_FUEL_LEVEL', '+5VA'}): 'tune the fuel gauge reading',
    frozenset({'DLC6_D29', 'K_LINE'}): 'D29 turns out to be a second K-line',
    frozenset({'OUT_SPARE_LS1', 'EVAP_A12'}): 'drive EVAP A12 from spare low-side 1',
    frozenset({'OUT_SPARE_LS2', 'EVAP_A13'}): 'drive EVAP A13 from spare low-side 2',
    frozenset({'GND_SENSOR', 'GND'}): 'FITTED: sensor returns to GND (remove to move them to GNDA)',
    frozenset({'GND_SENSOR', 'GNDA'}): 'sensor returns on analog ground instead of GND',
    frozenset({'BOOT0', '+3.3V'}): 'bridge to force the USB DFU bootloader',
    frozenset({'APS_PS_5V', '+5VAS'}): 'only if M8 is not fitted: pedal back on the shared sensor 5 V',
    frozenset({'CAN_H', 'CAN_L'}): 'external CAN device that does not terminate the bus',
    frozenset({'USB_SHIELD', 'GND'}): 'FITTED: USB shell to GND (remove to float the shell)',
    frozenset({'AUX_IN1', 'GND'}): 'aux input 1 floats: stronger pull-down',
    frozenset({'AUX_IN2', 'GND'}): 'aux input 2 floats: stronger pull-down',
    frozenset({'AUX_IN3', 'GND'}): 'aux input 3 floats: stronger pull-down',
    frozenset({'IN_DEFOG', '+5V'}): 'defogger line floats when off: stronger pull-up',
    frozenset({'IN_SMALL_LIGHT', '+5V'}): 'lights line floats when off: stronger pull-up',
    frozenset({'IN_BLOWER', '+5V'}): 'blower line floats when off: stronger pull-up',
    frozenset({'WBO_UN', 'WBO_UN_J1'}): 'FITTED: LSU Un through the harness (remove for a pigtail on the pads)',
    frozenset({'WBO_VM', 'WBO_VM_J1'}): 'FITTED: LSU Vm through the harness',
    frozenset({'WBO_IP', 'WBO_IP_J1'}): 'FITTED: LSU Ip through the harness (A25 shield wire)',
    frozenset({'FP_CMD', 'FUEL_PUMP_SIGNAL1'}): 'FITTED: series protection on the FPCU command',
}


def main():
    sheets = sorted(REPO.glob('*.kicad_sch'))
    parts = {}   # ref -> (sheet, value, dnp)
    for s in sheets:
        t = s.read_text()
        for m in re.finditer(r'\n\t\(symbol\n\t\t\(lib_id "[^"]+"\)(.*?)\n\t\)', t, re.S):
            b = m.group(1)
            ref = re.search(r'\(property "Reference" "([^"]*)"', b)
            if not ref or ref.group(1).startswith('#'):
                continue
            val = re.search(r'\(property "Value" "([^"]*)"', b).group(1)
            dnp = '(dnp yes)' in b
            parts[ref.group(1)] = (s.stem, val, dnp)
    with tempfile.TemporaryDirectory() as d:
        net = Path(d) / 'n.net'
        subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', str(net), str(REPO / 'rusefiSTI2004.kicad_sch')],
                       check=True, capture_output=True, cwd=REPO)
        nt = net.read_text()
    nets = {}
    for m in re.finditer(r'\(net\s*\(code "?[^")\s]*"?\)\s*\(name "([^"]*)"\)(.*?)(?=\n\s*\(net\s|\n\s*\)\s*\n\s*\)\s*$)', nt, re.S):
        for r, p in re.findall(r'\(node\s*\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', m.group(2)):
            nets.setdefault(r, {})[p] = m.group(1).split('/')[-1]
    rows = []
    for ref, (sheet, val, dnp) in parts.items():
        pn = nets.get(ref, {})
        if len(pn) != 2 or not re.match(r'^(R|JP)\d+$', ref):
            continue
        pair = frozenset(pn.values())
        why = WHY.get(pair)
        if not dnp and not why:
            continue          # an ordinary fitted part, not an option
        rows.append((sheet, int(re.sub(r'\D', '', ref)), ref, val, ' / '.join(sorted(pair)), 'not fitted' if dnp else 'fitted', why or '-'))
    rows.sort()
    print('| Sheet | Ref | Value | Joins | Default | When to fit / remove |')
    print('|---|---|---|---|---|---|')
    for sheet, _, ref, val, pair, state, why in rows:
        print(f'| {sheet} | {ref} | {val} | {pair} | {state} | {why} |')


if __name__ == '__main__':
    main()
