#!/usr/bin/env bash
# hrun.sh NAME PLAN.json : scratch run of a hand plan (outline edit, fresh placement, stackup, snap, score)
set -euo pipefail
N=$1; PLAN=$(readlink -f $2); REPO=$(cd "$(dirname "$0")/../../.." && pwd); S=$REPO/documents/floorplan-variants/scripts
R=${RUNS:-$HOME/eeroute/work/plan_H_runs}/$N; mkdir -p $R
for f in "$REPO"/*.kicad_sch "$REPO"/*.kicad_pro "$REPO"/*.kicad_dru "$REPO"/*.kicad_wks "$REPO"/fp-lib-table "$REPO"/sym-lib-table "$REPO"/rusefiSTI2004.kicad_pcb; do cp "$f" "$R"/; done
rmdir "$R/hellen-one" "$R/kicad6-libraries" 2>/dev/null || true
[ -d "$R/hellen-one" ] || cp -al "${SUB:-$HOME/rusefi-sti-2004}/hellen-one" "$R/hellen-one"
[ -d "$R/kicad6-libraries" ] || cp -al "${SUB:-$HOME/rusefi-sti-2004}/kicad6-libraries" "$R/kicad6-libraries"
cd $R
python3 $S/gen_h.py $PLAN pcb_place.json
read W H < <(python3 -c "import json;d=json.load(open('$PLAN'));print(*d['board'])")
python3 - "$W" "$H" <<'PY'
import re, sys
W, H = int(sys.argv[1]), int(sys.argv[2]); t = open('rusefiSTI2004.kicad_pcb').read()
t, n = re.subn(r'\(gr_rect\n(\s*)\(start [\d.]+ [\d.]+\)\n(\s*)\(end [\d.]+ [\d.]+\)(?=(?:(?!\(gr_).)*\(layer "Edge.Cuts"\))',
               lambda m: f'(gr_rect\n{m.group(1)}(start 80 30)\n{m.group(2)}(end {80+W} {30+H})', t, count=1, flags=re.S)
assert n == 1, 'outline not edited'
open('rusefiSTI2004.kicad_pcb', 'w').write(t)
PY
md5sum rusefiSTI2004.kicad_pro > .pro.md5
KICAD_LIB=$HOME/kicad-lib-sti kicad-pcb-from-netlist > tool.log 2>&1 || { tail -20 tool.log; exit 1; }
kicad-stackup JLC04161H-7628 >> tool.log 2>&1
docker run --rm --user $(id -u):$(id -g) -e HOME=/tmp -v $PWD:$PWD -v $S:/w -w $PWD --entrypoint python3 kicad/kicad:10.0.5 /w/snap.py rusefiSTI2004.kicad_pcb pcb_place.json | tee snap.log
md5sum -c .pro.md5 >/dev/null && echo "kicad_pro unchanged"
grep -i "warning" tool.log | head -20 || true
for L in 2 4; do python3 ~/kicad-lib/scripting/pcb/floorplan_score.py rusefiSTI2004.kicad_pcb --layers $L --json score$L.json > score$L.txt 2>&1 || true; done
sed -n 1,14p score2.txt | cut -c1-200
