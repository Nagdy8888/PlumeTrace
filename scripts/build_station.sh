#!/usr/bin/env bash
# Regenerate app/frontend/public/models/ks07.glb from the facility spec (approach B).
# Usage (repo root, Git Bash or Linux): scripts/build_station.sh [low|high]
set -euo pipefail
LEVEL="${1:-high}"
BLENDER="${BLENDER:-blender}"
"$BLENDER" --version | head -n 1 | grep -q "^Blender 4\.5\.16" || { echo "Blender 4.5.16 required"; exit 2; }
(cd app && uv run python ../scripts/export_contract.py)
"$BLENDER" --background --factory-startup --python scripts/blender/build_station.py -- \
  --spec app/frontend/src/shared/facility/ks07.json --out build/ks07_raw.glb --bake "$LEVEL"
npx --yes @gltf-transform/cli@4.5.1 optimize build/ks07_raw.glb app/frontend/public/models/ks07.glb \
  --compress meshopt --texture-compress webp --texture-size 512 \
  --join false --flatten false --simplify false --palette false --prune false
npx --yes @gltf-transform/cli@4.5.1 inspect app/frontend/public/models/ks07.glb > build/ks07_inspect.txt
(cd app && uv run python ../scripts/check_glb.py --glb frontend/public/models/ks07.glb \
  --spec frontend/src/shared/facility/ks07.json \
  --max-bytes 15000000 --max-triangles 1500000 --max-draw-calls 300)
