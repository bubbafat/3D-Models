#!/bin/zsh
# Monorail Countdown.py -> painted, oriented Bambu Studio projects -> slice stats.
# One run, no GUI. See README.md.
#
#   zsh make_print_files.sh <output folder> <a Bambu Studio project of yours with four filaments>
set -e
if (( $# != 2 )); then
  echo "usage: zsh make_print_files.sh <output folder> <your four-filament Bambu Studio project.3mf>" >&2
  exit 2
fi
OUT="${1:a}"; SETTINGS="${2:a}"
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
# plate name : filaments for the first pass : filament colours in the finished project
for spec in "car plate:4:#FFFFFF,#161616,#C12E1F,#FFF144" "cubes:2:#FFFFFF,#161616,#C12E1F,#FFF144" "beam plate:1:#8E9089,#161616,#C12E1F,#FFF144"; do
  name="${spec%%:*}"; rest="${spec#*:}"; n="${rest%%:*}"; cols="${rest#*:}"
  fils=$(python3 -c "print(';'.join(['$FI']*$n))")
  rm -rf "$WORK/proj"; mkdir -p "$WORK/proj"
  # --outputdir must be absolute: a relative one fails with "Unable to open the file proj.3mf.tmp".
  (cd "$WORK/proj" && "$B" --load-settings "$M;$PR" --load-filaments "$fils" --outputdir "$WORK/proj" \
      --export-3mf "proj.3mf" "$WORK/plates/Monorail - $name.3mf" > /dev/null 2>&1)
  python3 -I "$HERE/inject_paint.py" "$WORK/plates/Monorail - $name.3mf" "$WORK/proj/proj.3mf" \
      "$OUT/Monorail - $name.3mf" "$cols" "$SETTINGS" > /dev/null
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
