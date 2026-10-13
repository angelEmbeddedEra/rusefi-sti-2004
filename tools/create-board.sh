#!/usr/bin/env bash
# Build the Hellen board package on this machine (replaces GitHub's create-board workflow).
#
#   tools/create-board.sh
#
# 1. KiCad 10 container: schematic PDF, netlist, BOM, Gerbers, drill, positions, VRML -> gerber/
# 2. hellen-one container: merge with the module frames -> boards/<prefix><suffix>-<rev>/
# Needs docker. KICAD_IMAGE picks the KiCad image (default kicad/kicad:10.0.5).
# Nothing is committed or pushed; review the boards/ diff and commit it yourself.
set -euo pipefail
cd "$(dirname "$0")/.."
. revision.txt
IMAGE="${KICAD_IMAGE:-kicad/kicad:10.0.5}"
BOM_REPLACE="bom_replace_${BOARD_PREFIX}${BOARD_SUFFIX}-${BOARD_REVISION}.csv"
[[ -f "$BOM_REPLACE" ]] || { echo "missing $BOM_REPLACE (revision.txt says rev $BOARD_REVISION)"; exit 1; }
[[ -e hellen-one/git_scripts ]] || git submodule update --init --recursive

# kicad-cli in the container rewrites the .kicad_pro with its defaults; keep ours.
PRO="${BOARD_PREFIX}${BOARD_SUFFIX}.kicad_pro"
cp "$PRO" "$PRO.bak"; trap 'mv "$PRO.bak" "$PRO"' EXIT

docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -e PYTHONPATH=/usr/share/kicad/plugins \
  -v "$PWD:$PWD" -w "$PWD" --entrypoint bash "$IMAGE" hellen-one/kicad/bin/export.sh
bash hellen-one/bin/step1_build_hellen-one_docker.sh
bash hellen-one/bin/step2_copy_with_docker.sh
bash hellen-one/bin/step3_create_board_with_docker.sh
echo "Board package: boards/${BOARD_PREFIX}${BOARD_SUFFIX}-${BOARD_REVISION}/"
