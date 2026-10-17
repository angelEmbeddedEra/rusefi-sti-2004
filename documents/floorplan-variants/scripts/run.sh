#!/usr/bin/env bash
# run.sh NAME PLAN.json  : scratch run (outline edit, fresh placement, stackup, snap, score)
set -euo pipefail
N=$1; PLAN=$2; F=~/eeroute/work/floorplan_v2; R=$F/runs/$N
$F/scripts/mkrun.sh $N >/dev/null; cd $R
python3 $F/scripts/gen_place.py $PLAN pcb_place.json
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
docker run --rm --user $(id -u):$(id -g) -e HOME=/tmp -v $PWD:$PWD -v $F:/w -w $PWD --entrypoint python3 kicad/kicad:10.0.5 /w/scripts/snap.py rusefiSTI2004.kicad_pcb pcb_place.json | tee snap.log
md5sum -c .pro.md5 >/dev/null && echo "kicad_pro unchanged"
python3 ~/kicad-lib/scripting/pcb/floorplan_score.py rusefiSTI2004.kicad_pcb --layers 2 --json score.json > score.txt 2>&1 || true
sed -n 1,12p score.txt | cut -c1-200; grep -E "^[3-6] " score.txt | cut -c1-260
