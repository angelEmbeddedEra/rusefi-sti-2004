#!/usr/bin/env python3
"""Cross-check the schematic's J1 (135-pin vehicle connector) against the 2004 STI ECM pinout.

    python3 tools/pinout_check.py                                   # current checkout
    python3 tools/pinout_check.py --sch master=/path/a.kicad_sch --sch rev-b=/path/b.kicad_sch

Inputs:  documents/oem-ecm-pinout-2004-sti.csv  (the car, transcribed from the FSM, with page refs)
         documents/pinout-ECU.xlsx              (the working sheet: what each pin should be called)
         each --sch schematic, read with `kicad-cli sch export netlist`
Output:  documents/STI2004-pinout-check.xlsx, written by `gridcraft-cli run` (GridCraft).
Status is judged on the LAST --sch given; earlier ones are shown for comparison.
"""
import argparse, csv, json, re, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "documents"
PLUGS = (("D", "B137", 31), ("C", "B136", 35), ("B", "B135", 35), ("A", "B134", 34))  # J1 pin order

# What the rusEFI design should put on each car pin: a regex the J1 net name must match.
# Pins absent here are ones the car uses that the design has not assigned yet.
EXPECT = {
    "D1": "^GND$", "D2": "^GND$", "D3": "GND", "D4": "ETB-", "D5": r"ETB\+", "D6": r"F5|12V_ETB",
    "D7": "^GND$", "D8": "STARTER", "D9": "NEUTRAL", "D10": "PS_PRESSURE", "D15": "12V_IGN",
    "D17": "MAIN_RELAY", "D28": "FUEL_PUMP_SIGNAL2", "D31": "GND",
    "C3": "INJ4", "C4": "INJ3", "C5": "INJ2", "C6": "INJ1", "C13": "IAT", "C14": "ECT|CLT",
    "C15": "5V", "C16": "5V", "C17": "PPS_MAIN|APS_MAIN", "C18": "TPS_MAIN", "C20": "FUEL_LEVEL",
    "C22": "MAP", "C23": "MAF", "C25": "KNOCK", "C26": "TUMBLE_SENSOR_LH", "C27": "TUMBLE_SENSOR_RH",
    "C28": "PPS_SUB|APS_SUB", "C29": "TPS_SUB",
    "C31": "GND", "C32": "GND", "C33": "GND", "C34": "GND", "C35": "GND",
    "B1": "^GND$", "B4": "^GND$", "B5": "12V_RAW", "B6": "12V_RAW", "B8": "IN_CAM$|CAM.*LH", "B9": "CAM.*RH",
    "B10": r"CRANK\+", "B12": "^GND$", "B15": "IGN4", "B16": "IGN3", "B17": "IGN2", "B18": "IGN1",
    "B19": "BACK_UP", "B22": "CRANK-", "B24": "FAN_RELAY_2", "B25": "FAN_RELAY_1",
    "B26": "FUEL_PUMP_SIGNAL1", "B27": "VSS", "B31": "GND", "B35": "THROTT?L?E_RELAY|ETB_RELAY",
    "D16": "AC_REQUEST", "D25": "O2S", "C8": "BRAKE_SW2", "C9": "BRAKE_SW1", "B2": "O2_HEATER", "B33": "AC_RELAY",
    "A8": "TGV_CLOSE", "A10": "TGV_CLOSE", "A9": "TGV_OPEN", "A11": "TGV_OPEN", "A17": "MIL",
    "C7": "CRUISE_MAIN", "C10": "CRUISE_RESUME", "C11": "CRUISE_SET", "A15": "CRUISE_MAIN_LIGHT", "A16": "CRUISE_SET_LIGHT",
    "D20": "K_LINE", "A2": "WBO_HEATER", "A3": "WBO_HEATER", "A33": "WBO_UN", "A26": "WBO_VM", "A25": "WBO_IP",
    "A12": "EVAP_A12", "A13": "EVAP_A13", "D28": "FP_STATUS", "D29": "DLC6", "A22": "CHARGE_A22",
    "D11": "DEFOG", "D12": "SMALL_LIGHT", "D13": "BLOWER", "D14": "TEST_MODE", "D24": "BLOWBY",
    "A1": "CLUTCH", "A6": "^GND$", "A7": "^GND$", "A14": "PURGE", "A18": r"VVT_RH\+|12V_RAW", "A19": r"VVT_LH\+|12V_RAW",
    "A23": "TACH", "A28": "VVT_RH-", "A29": "VVT_LH-", "A32": "WG|WASTEGATE", "A34": "^GND$",
}
RAILS = {"GND", "GNDA", "+12V_RAW"}


def j1_order():
    return [(f"{l}{i}", plug, i) for l, plug, n in PLUGS for i in range(1, n + 1)]


def netlist(sch: Path):
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "x.net"
        subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr", "-o", str(out), str(sch)],
                       cwd=sch.parent, check=True, capture_output=True)
        t = out.read_text()
    nets = {}
    for m in re.finditer(r'\(net\s*\(code "[^"]*"\)\s*\(name "([^"]*)"\)(.*?)\n\t\t\)', t, re.S):
        nets[m.group(1)] = re.findall(r'\(node\s*\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)(?:\s*\(pinfunction "([^"]*)"\))?', m.group(2))
    return nets


def j1_view(nets):
    """J1 pin number -> (net name, where it ends up), following 2-pin fuses (F*) one hop."""
    pin_net = {int(p): n for n, nodes in nets.items() for r, p, _ in nodes if r == "J1"}
    by_pad = {(r, p): n for n, nodes in nets.items() for r, p, _ in nodes}
    view = {}
    for pin, net in pin_net.items():
        if net.startswith("unconnected"):
            view[pin] = ("", "")
            continue
        if net in RAILS:
            view[pin] = (net, "rail")
            continue
        others = [(r, p, f) for r, p, f in nets[net] if r != "J1"]
        hops = []
        for r, p, f in others:
            if r.startswith("F"):  # series fuse pad: report the net on its other pad
                far = by_pad.get((r, "2" if p == "1" else "1"), "")
                ends = [f"{r2}.{f2 or p2}" for r2, p2, f2 in nets.get(far, []) if r2 != r]
                hops.append(f"{r} -> {far.lstrip('/')}" + (f" -> {', '.join(ends)}" if ends else " (dead end)"))
            else:
                hops.append(f"{r}.{f or p}")
        view[pin] = (net.lstrip("/") if not net.startswith("Net-") else net, "; ".join(hops))
    return view


def working_sheet():
    """Labels from documents/pinout-ECU.xlsx, keyed by harness code (column D)."""
    src = DOCS / "pinout-ECU.xlsx"
    if not src.exists():
        return {}
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "s.csv"
        subprocess.run(["gridcraft-cli", "convert", str(src), str(out), "--sheet", "Sheet1"], check=True, capture_output=True)
        rows = list(csv.reader(out.open(encoding="utf-8-sig")))
    labels = {}
    for r in rows[1:]:
        r = (r + [""] * 8)[:8]
        code = r[3].strip()
        if code:
            labels[code] = " | ".join(x.replace("\n", " ").strip() for x in r[5:8] if x.strip())
    return labels


def status(code, used, net, ends, unlisted=False):
    if unlisted and not EXPECT.get(code):
        return "CHECK", "Not in the FSM I/O table; see note"
    if not used:
        return ("unused", "") if not net else ("CHECK", "Car does not use this pin, but the schematic connects it")
    if not net:
        return "NOT WIRED", ""
    want = EXPECT.get(code)
    if want and not (re.search(want, net) or re.search(want, ends)):
        return "MISMATCH", f"Expected a net matching {want!r}"
    if not ends or "(dead end)" in ends:
        return "LABEL ONLY", "Net is named but reaches no module or rail"
    sig = [e for e in re.findall(r"\b(M\d+)\.([^,;\s]+)", ends) if not re.search("12V|GND|5V|VCC|VIGN|PERM|VBAT", e[1])]
    if len(sig) > 1:
        return "MISMATCH", "Joins several module signal pins: " + ", ".join(".".join(e) for e in sig)
    if not want:
        return "CHECK", "Wired, but no expected net is defined for this pin"
    return "OK", ""


def build(schs, out_path):
    oem = {r["code"]: r for r in csv.DictReader((DOCS / "oem-ecm-pinout-2004-sti.csv").open())}
    views = [(label, j1_view(netlist(path))) for label, path in schs]
    mine = working_sheet()
    head = ["J1 pin", "Car plug", "Term.", "Code", "Function (FSM)", "Signal type", "Key on (V)", "Idle (V)",
            "Source", "Your sheet"] + [f"Net: {l}" for l, _ in views] + [f"Reaches ({views[-1][0]})", "Status", "Notes"]
    rows, counts = [head], {}
    for pin, (code, plug, term) in enumerate(j1_order(), 1):
        o = oem[code]
        used = not o["function"].startswith("(not used")
        net, ends = views[-1][1][pin]
        st, why = status(code, used, net, ends, o["function"].startswith("(not in I/O table") and not o["type"])
        counts[st] = counts.get(st, 0) + 1
        notes = "; ".join(x for x in (why, o["note"]) if x)
        rows.append([pin, plug, term, code, o["function"], o["type"], o["volts_key_on"], o["volts_idle"], o["source"],
                     mine.get(code, "")] + [v[pin][0] for _, v in views] + [ends, st, notes])
    ncol = len(head)
    colL = lambda i: chr(ord("A") + i)  # ponytail: single letters, fine up to 26 columns
    st_col = colL(ncol - 2)
    cmds = [
        ("sheet.rename", {"name": "Pinout check"}),
        ("range.setValues", {"range": "A1", "values": rows}),
        ("home.cellStyle", {"range": f"A1:{colL(ncol-1)}1", "name": "Heading 3"}),
        ("home.wrapText", {"range": f"A1:{colL(ncol-1)}{len(rows)}", "on": True}),
        ("view.freezePanes", {"cell": "E2"}),
        ("selection.set", {"range": f"A1:{colL(ncol-1)}{len(rows)}"}),
        ("data.filter", {}),
    ]
    widths = [6, 7, 5, 6, 34, 22, 16, 16, 11, 26] + [26] * len(views) + [34, 12, 44]
    cmds += [("home.columnWidth", {"cols": f"{colL(i)}:{colL(i)}", "chars": w}) for i, w in enumerate(widths)]
    rng = f"{st_col}2:{st_col}{len(rows)}"
    for text, preset in (("NOT WIRED", "lightRedFillDarkRedText"), ("MISMATCH", "lightRedFillDarkRedText"),
                         ("LABEL ONLY", "yellowFill"), ("CHECK", "yellowFill"), ("OK", "greenFill")):
        cmds.append(("home.conditionalFormat", {"range": rng, "rule": {"type": "beginsWith", "text": text, "preset": preset}}))

    summary = [["Status", "Pins", "Meaning"],
               ["OK", counts.get("OK", 0), "Car pin is wired to the expected net and reaches a module or rail"],
               ["MISMATCH", counts.get("MISMATCH", 0), "Wired, but to the wrong signal"],
               ["LABEL ONLY", counts.get("LABEL ONLY", 0), "Net has the right name but stops at J1: not connected to the MCU"],
               ["NOT WIRED", counts.get("NOT WIRED", 0), "Car uses the pin; the schematic leaves it unconnected"],
               ["CHECK", counts.get("CHECK", 0), "Needs a look (unused car pin connected, or no expectation defined)"],
               ["unused", counts.get("unused", 0), "Car does not use the pin and the schematic leaves it open"],
               [], ["Built by", "tools/pinout_check.py", "Re-run after any schematic change"],
               ["Car data", "documents/oem-ecm-pinout-2004-sti.csv", "Transcribed from the FSM pages in Source"],
               ["Schematics", ", ".join(l for l, _ in views), "Status judged on the last one"]]
    cmds += [("home.insertSheet", {"name": "Summary", "before": 0}),
             ("range.setValues", {"range": "A1", "values": summary}),
             ("home.cellStyle", {"range": "A1:C1", "name": "Heading 3"}),
             ("home.columnWidth", {"cols": "A:A", "chars": 14}), ("home.columnWidth", {"cols": "B:B", "chars": 36}),
             ("home.columnWidth", {"cols": "C:C", "chars": 70})]
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
        for c, p in cmds:
            f.write(json.dumps({"command": c, "params": p}) + "\n")
    subprocess.run(["gridcraft-cli", "run", "--script", f.name, "--out", str(out_path), "--quiet"], check=True)
    return counts


def selftest():
    assert len(j1_order()) == 135 and j1_order()[31] == ("C1", "B136", 1) and j1_order()[134][0] == "A34"
    assert status("C23", True, "IN_MAP", "M1.IN_MAP1") == ("MISMATCH", "Expected a net matching 'MAF'")
    assert status("C22", True, "", "")[0] == "NOT WIRED"
    assert status("D1", True, "GND", "rail")[0] == "OK"
    assert status("D8", True, "IN_STARTER_SWITCH", "")[0] == "LABEL ONLY"
    assert status("D22", False, "IN_CRANK-", "M5.VR-")[0] == "CHECK"
    assert status("B15", True, "Net-(F1-Pad1)", "F1 -> OUT_IGN4 -> M1.IGN4_W8")[0] == "OK"
    assert status("B18", True, "Net-(F4-Pad1)", "F4 -> OUT_IGN1 -> M1.IGN1_W11, M1.IGN4_W8")[0] == "MISMATCH"
    assert status("B10", True, "IN_CRANK+", "M5.VR+_W2, M6.VR+_W2")[0] == "MISMATCH"
    assert status("D6", True, "Net-(F5-Pad1)", "F5 -> +12V_ETB -> M2.12V_IN_N2, M2.12V_IN_S1")[0] == "OK"
    assert status("B15", True, "OUT_IGN4", "M1.IGN4")[0] == "OK"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sch", action="append", metavar="LABEL=PATH", help="schematic to check (repeatable)")
    ap.add_argument("--out", default=str(DOCS / "STI2004-pinout-check.xlsx"))
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    selftest()
    if a.selftest:
        sys.exit(print("selftest ok"))
    schs = [tuple(s.split("=", 1)) for s in (a.sch or [f"current={REPO / 'rusefiSTI2004.kicad_sch'}"])]
    counts = build([(l, Path(p)) for l, p in schs], Path(a.out))
    print(a.out, counts)
