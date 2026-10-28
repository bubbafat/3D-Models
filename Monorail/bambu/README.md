# Bambu Studio print files

Makes the monorail's print files for Bambu Studio, with no clicking in the
slicer:

- painted in the model's four colours;
- each part turned to its print orientation;
- laid out on three plates;
- sliced, with time, filament changes and grams reported.

Without it you would paint every part by hand in Bambu Studio. Fusion's 3MF
export keeps the model's colours, but Bambu Studio ignores them.

## Needs

- **macOS.** The script uses the macOS paths to Fusion and Bambu Studio.
- **Fusion** with the [ClaudeBridge](../../ClaudeBridge) add-in running, and
  the two [Countdown fonts](../../Font) the model needs. If the add-in is not installed in
  Fusion's add-ins folder, set `CLAUDEBRIDGE` to the folder it is in.
- **Bambu Studio** in `/Applications`. Tested with 2.07 and a P1S; the plates
  are laid out for a 256 mm bed.
- **A Bambu Studio project of yours with four filaments set up.** Any `.3mf`
  you have printed from with your AMS will do. The print files take your
  printer, process and filament settings from it; nothing in that project is
  changed.

## Run it

From this folder:

```bash
zsh make_print_files.sh "<output folder>" "<your four-filament project>.3mf"
```

It takes about a minute, most of it Fusion building the model. It leaves a
new document open in Fusion, built from
`Monorail Countdown.py`. Close that document without saving; the script never
closes any of your documents. The output folder gets three files:

| File | Parts | Filaments |
|---|---|---|
| `Monorail - car plate.3mf` | Both car halves and the pins | 1 white, 2 black, 3 red, 4 gold |
| `Monorail - beam plate.3mf` | Beam and foot | 1 grey |
| `Monorail - cubes.3mf` | The four cubes | 1 white, 2 black |

Each line it ends with is one plate's slice: filament changes, hours, minutes
of flushing, and grams per filament.

## How it works

1. `build_and_export.py` runs `Monorail Countdown.py` in a new Fusion document
   through ClaudeBridge. It exports the result as one 3MF, which carries the
   script's preview colour on every triangle.
2. `to_bambu.py` maps each colour to a filament. It also paints the letters'
   sides gold, because Fusion paints only their tops: painting thousands of
   glyph faces there takes minutes. It then turns each part to its print
   orientation and writes one 3MF per plate.
3. Bambu Studio's command line turns each plate into a Bambu project.
4. `inject_paint.py` writes Bambu's paint onto every triangle of that project,
   checking vertex by vertex that the meshes still match, and swaps in your
   project's settings.
5. Bambu Studio's command line slices each finished project and reports.

## What Bambu Studio does that you need to know

This section is for changing these scripts, or doing the same for another
model. It was worked out by testing against Bambu Studio 2.07.

- **Paint format.** Bambu reads colour from a `paint_color` attribute on each
  `<triangle>` in a project's object files. A whole triangle in filament *s* is
  `4` for 1, `8` for 2, then `0C`, `1C`, `2C`… for 3, 4, 5…, so the code for
  *s* ≥ 3 is `{s-3:X}C`. A triangle with no attribute takes its object's
  filament. Painting in Bambu Studio itself can split a triangle and write
  longer codes; these are only the codes for whole triangles.
- **The command line comes out with one filament.** A project the command line
  writes, from presets it loads itself, has one filament however many you
  pass. Bambu then drops paint 2–4 *silently*: the file opens and slices with
  no error, in one colour. That is why the finished project takes its settings from
  a real four-filament project of yours.
- **Repaint every triangle.** The project Bambu writes keeps some of the paint
  from the file it imported. Match triangles by position and rewrite every one.
  If you skip the ones that already have paint, the paint after them lands on
  the wrong triangles; here it put gold on the windshield.
- **Absolute output folder.** `--outputdir` must be an absolute path. A
  relative one fails with `Unable to open the file … .tmp`.
- **Check by slicing.** `BambuStudio --slice 0 --outputdir <absolute folder>
  <project.3mf>` writes `result.json`, with `filament_change_times`,
  `total_predication` (seconds) and grams per filament. If the car plate shows
  0 filament changes, the paint was lost.
