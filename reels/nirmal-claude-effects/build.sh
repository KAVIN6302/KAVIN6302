#!/usr/bin/env bash
# Rebuild Nirmal's Claude /effects reel from his talking-head clip.
# usage: bash build.sh path/to/clip.mp4 [out.mp4]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SKILL="$HERE/../../.claude/skills/effects"
CLIP="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
OUT="${2:-$HERE/nirmal_claude_effects.mp4}"
bash "$SKILL/scripts/setup.sh"
PY="$SKILL/.venv/bin/python"
cd "$HERE"; mkdir -p renders grid
# effect renders the phone screen plays (run A and run B use separate stretches of the clip)
"$PY" myfx.py --plan plans/runA.json "$CLIP" renders/runA.mp4 &
"$PY" myfx.py --plan plans/runB.json "$CLIP" renders/runB.mp4 &
# stills for the 19 end-card tiles
"$PY" myfx.py --plan plans/g1.json "$CLIP" grid/g1.png --still 1.4,2.8,4.2,5.6,7.0,8.4,9.8 &
"$PY" myfx.py --plan plans/g2.json "$CLIP" grid/g2.png --still 1.4,2.8,4.2,5.6,7.0,8.4,9.8 &
"$PY" myfx.py --plan plans/g3.json "$CLIP" grid/g3.png --still 1.8,3.8,5.8,7.8,9.8 &
wait
"$PY" compose.py "$CLIP" "$OUT"
