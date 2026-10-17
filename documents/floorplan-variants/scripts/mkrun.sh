#!/usr/bin/env bash
# mkrun.sh NAME : scratch copy of the repo (hellen-one + kicad6-libraries hardlinked) under runs/NAME
set -euo pipefail
N=$1; R=~/eeroute/work/floorplan_v2/runs/$N; S=~/rusefi-sti-2004
mkdir -p "$R"
for f in "$S"/*.kicad_sch "$S"/*.kicad_pro "$S"/*.kicad_dru "$S"/*.kicad_wks "$S"/fp-lib-table "$S"/sym-lib-table; do cp -u "$f" "$R"/; done
cp "$S/rusefiSTI2004.kicad_pcb" "$R/rusefiSTI2004.kicad_pcb"
[ -d "$R/hellen-one" ] || cp -al "$S/hellen-one" "$R/hellen-one"
[ -d "$R/kicad6-libraries" ] || cp -al "$S/kicad6-libraries" "$R/kicad6-libraries"
echo "$R"
