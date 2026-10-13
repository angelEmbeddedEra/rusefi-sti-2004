#!/usr/bin/env bash
# Tidy every sheet to the house style (tools/sch_tidy.py), then prove nothing electrical changed:
# the netlist before and after must hold the same nets with the same pins, and every sheet must
# pass the overlap check. Leaves the tidied sheets in place; `git diff` / `git checkout` to review.
#
#   tools/tidy-check.sh            # all sheets
#   tools/tidy-check.sh Aux.kicad_sch Inputs.kicad_sch
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$(grep -l '(sheet_instances' *.kicad_sch | head -1)
SHEETS=("$@"); [[ ${#SHEETS[@]} -gt 0 ]] || SHEETS=(*.kicad_sch)
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
kicad-cli sch export netlist --format kicadsexpr -o "$TMP/before.net" "$ROOT" >/dev/null
for f in "${SHEETS[@]}"; do python3 tools/sch_tidy.py "$f" & done; wait
kicad-cli sch export netlist --format kicadsexpr -o "$TMP/after.net" "$ROOT" >/dev/null
python3 - "$TMP/before.net" "$TMP/after.net" <<'EOF'
import re, sys
def nets(p):
    t = open(p).read(); out = {}
    for m in re.finditer(r'\(net\s*\(code "?[^")]*"?\)\s*\(name "([^"]*)"\)(.*?)(?=\n\s*\(net\s|\Z)', t, re.S):
        nodes = frozenset(re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', m.group(2)))
        if nodes:
            out[nodes] = m.group(1)
    return out
a, b = nets(sys.argv[1]), nets(sys.argv[2])
bad = [(a.get(k), b.get(k)) for k in set(a) | set(b) if a.get(k) != b.get(k)]
for x in bad[:20]:
    print('NET CHANGED', x)
print(f'netlist: {len(a)} nets, {len(bad)} changed')
sys.exit(1 if bad else 0)
EOF
fail=0
for f in *.kicad_sch; do python3 tools/sch_overlap_check.py "$f" >/dev/null || { python3 tools/sch_overlap_check.py "$f"; fail=1; }; done
[[ $fail == 0 ]] && echo "overlaps: 0 on every sheet"
exit $fail
