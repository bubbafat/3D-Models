#!/bin/zsh
# Monorail Countdown.py -> painted, oriented Bambu Studio projects -> slice stats.
# One run, no GUI. See README.md.
#
#   zsh make_print_files.sh <output folder> <a Bambu Studio project of yours with four filaments> \
#       [<a project of yours with a PETG filament, for the supports' interface>]
set -e
if (( $# != 2 && $# != 3 )); then
  echo "usage: zsh make_print_files.sh <output folder> <your four-filament Bambu Studio project.3mf> [<a project with PETG>.3mf]" >&2
  exit 2
fi
OUT="${1:a}"; SETTINGS="${2:a}"
PETG=(); (( $# == 3 )) && PETG=("${3:a}")
# The model's own print settings, over yours: the dry fit's 8% lightning infill
# left the car flexible and see-through.
MODEL=(--set sparse_infill_density=15% --set sparse_infill_pattern=gyroid --set wall_loops=4)
HERE="${0:a:h}"
BRIDGE="${CLAUDEBRIDGE:-$HOME/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/ClaudeBridge}"
B=/Applications/BambuStudio.app/Contents/MacOS/BambuStudio
P=/Applications/BambuStudio.app/Contents/Resources/profiles/BBL
# Only for the Bambu command line's first pass; the finished projects get SETTINGS instead.
M="$P/machine/Bambu Lab P1S 0.4 nozzle.json"; PR="$P/process/0.20mm Standard @BBL X1C.json"; FI="$P/filament/Bambu PLA Basic @BBL X1C.json"
WORK=$(mktemp -d -t monorail-bambu)
mkdir -p "$OUT"
echo "== working in $WORK"

echo "== build and export in Fusion"
python3 "$HERE/build_and_export.py" "$BRIDGE" "$HERE/../Monorail Countdown.py" "$WORK/monorail.3mf"
echo "== convert"
python3 -I "$HERE/to_bambu.py" "$WORK/monorail.3mf" "$WORK/plates" | grep -E "letter sides|\.3mf"
# One filament list for every plate, so a filament number means the same in
# each file: your four, then grey and PETG. filaments.py sorts Bambu's lists by
# comparing with a one-filament project of Bambu's own.
mkdir -p "$WORK/ref"
(cd "$WORK/ref" && "$B" --arrange 0 --load-settings "$M;$PR" --load-filaments "$FI" --outputdir "$WORK/ref" \
    --export-3mf "ref.3mf" "$WORK/plates/Monorail - beam plate.3mf" > /dev/null 2>&1)
python3 -I "$HERE/filaments.py" "$SETTINGS" "$WORK/ref/ref.3mf" "$WORK/settings.3mf" $PETG
# plate name : filaments for the first pass : your four filaments' colours in
# the finished project. The car is in three plates by colour: the white bottom
# with the pins, the red halves with their gold lettering, and the white and
# black top.
CAR="#FFFFFF,#161616,#C12E1F,#FFF144"
for spec in "car bottom:1:$CAR" "car red:4:$CAR" "car top:2:$CAR" "cubes:2:$CAR" "beam plate:1:$CAR"; do
  name="${spec%%:*}"; rest="${spec#*:}"; n="${rest%%:*}"; cols="${rest#*:}"
  fils=$(python3 -c "print(';'.join(['$FI']*$n))")
  rm -rf "$WORK/proj"; mkdir -p "$WORK/proj"
  # --outputdir must be absolute: a relative one fails with "Unable to open the file proj.3mf.tmp".
  # --arrange 0 keeps to_bambu.py's layout: packed close, supports collided.
  (cd "$WORK/proj" && "$B" --arrange 0 --load-settings "$M;$PR" --load-filaments "$fils" --outputdir "$WORK/proj" \
      --export-3mf "proj.3mf" "$WORK/plates/Monorail - $name.3mf" > /dev/null 2>&1)
  python3 -I "$HERE/inject_paint.py" "$WORK/plates/Monorail - $name.3mf" "$WORK/proj/proj.3mf" \
      "$OUT/Monorail - $name.3mf" "$cols" "$WORK/settings.3mf" $MODEL | grep "supports:" || true
  D="$WORK/slice_${name// /_}"; mkdir -p "$D"
  (cd "$D" && "$B" --slice 0 --outputdir "$D" "$OUT/Monorail - $name.3mf" > cli.log 2>&1)
  python3 - "$D/result.json" "$name" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
for p in r.get('sliced_plates', []):
    t = p.get('feature_type_times', {})
    fil = p.get('filaments', [])
    print('== {:10s} {}  changes {:3d}  {:4.1f} h (flush {:.0f} min)  g: {}  total {:.0f} g'.format(
        sys.argv[2], r.get('error_string'), p.get('filament_change_times'), p.get('total_predication', 0) / 3600,
        t.get('Flush', 0) / 60, [round(f.get('total_used_g', 0)) for f in fil], sum(f.get('total_used_g', 0) for f in fil)))
PY
done
rm -rf "$WORK"
echo "== print files in $OUT"
