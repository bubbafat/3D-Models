# Bambu Studio print files

Makes the monorail's print files for Bambu Studio, with no clicking in the
slicer:

- painted in the model's four colours;
- each part turned to its print orientation;
- supports painted on exactly where they are needed;
- laid out on six plates, in one project;
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
  changed. Over them the print files set the model's own: 15% gyroid infill
  and 4 walls (`MODEL` in `make_print_files.sh`). Supports come out on for the
  car bottom and the red halves, only where they are painted.
- **Optionally, a project of yours with a PETG filament.** Given one, its
  PETG profile becomes filament 6 and the supports' interface. Without, the
  supports are in each part's own filament.

## Run it

From this folder:

```bash
zsh make_print_files.sh "<output folder>" "<your four-filament project>.3mf" "<a project with PETG>.3mf"
```

Leave off the last one for supports without PETG.

It takes about a minute, most of it Fusion building the model. It leaves a
new document open in Fusion, built from
`Monorail Countdown.py`. Close that document without saving; the script never
closes any of your documents. The output folder gets `Monorail.3mf`, one
project with all five plates, and each plate on its own as well. Every file
has the same filaments, so a filament number means the same in each, and a
part imported into another file's project keeps its colours: your four AMS
filaments, 1 white, 2 black, 3 red, 4 gold, then 5 grey, a copy of your
filament 1, and 6 PETG, if you gave a PETG project. Of those, each plate uses:

| Plate | On its own | Parts | Uses |
|---|---|---|---|
| 1 Car Bottom | `Monorail - car bottom.3mf` | The car's bottom and all twenty-one pins | 1 white, 6 PETG |
| 2 Car Red | `Monorail - car red.3mf` | The two red halves | 3 red, 4 gold, 6 PETG |
| 3 Car Top White | `Monorail - car top white.3mf` | The pinstripe and the roof | 1 white |
| 4 Car Top Black | `Monorail - car top black.3mf` | The window band and the three frames | 2 black |
| 5 Beam Plate | `Monorail - beam plate.3mf` | Beam and foot | 5 grey |
| 6 Cubes | `Monorail - cubes.3mf` | The four cubes | 1 white, 2 black |

When you print a plate, map the filaments it uses to your AMS. Each plate is
one car. To print a batch, add copies of the part in Bambu Studio; the paint
and supports copy with it.

Each line it ends with is one plate of `Monorail.3mf`, sliced: filament
changes, hours, minutes of flushing, and grams by filament.

## How it works

1. `build_and_export.py` runs `Monorail Countdown.py` in a new Fusion document
   through ClaudeBridge. It exports the result as one 3MF, which carries the
   script's preview colour on every triangle.
2. `to_bambu.py` maps each colour to a filament. It also paints the letters'
   sides gold, because Fusion paints only their tops: painting thousands of
   glyph faces there takes minutes. It paints supports on the faces that
   need them -- the bottom's nose underside, the red halves' tail ends over
   the spare pocket -- then turns each part to its print orientation and
   writes one 3MF per plate.
3. `filaments.py` makes the one set of settings every plate gets: your
   project's, with grey and the PETG added as filaments 5 and 6.
4. Bambu Studio's command line turns each plate into a Bambu project.
5. `inject_paint.py` writes Bambu's paint onto every triangle of that project,
   checking vertex by vertex that the meshes still match, and swaps in those
   settings. A plate with painted supports gets tree supports in manual mode,
   which supports the painted faces and nothing else; with the PETG, its
   interface is PETG, with no gap, and that plate stops flushing into the
   parts' infill, so no PETG ends up inside a PLA part.
6. `one_project.py` merges the six into `Monorail.3mf`, and Bambu Studio's
   command line slices it, every plate, and reports.

## What Bambu Studio does that you need to know

This section is for changing these scripts, or doing the same for another
model. It was worked out by testing against Bambu Studio 2.07.

- **Paint format.** Bambu reads colour from a `paint_color` attribute on each
  `<triangle>` in a project's object files. A whole triangle in filament *s* is
  `4` for 1, `8` for 2, then `0C`, `1C`, `2C`… for 3, 4, 5…, so the code for
  *s* ≥ 3 is `{s-3:X}C`. A triangle with no attribute takes its object's
  filament. Painting in Bambu Studio itself can split a triangle and write
  longer codes; these are only the codes for whole triangles.
- **Support paint.** Painted supports are a `paint_supports` attribute on the
  same triangles, in the same code: `4` is an enforcer, `8` a blocker. With
  `support_type` set to `tree(manual)` or `normal(manual)`, Bambu supports the
  enforced faces and nothing else. In automatic mode it also filled bridges
  -- the beam channel, the cube slots -- and neither `bridge_no_support` nor
  `max_bridge_length` stopped it.
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
- **Layer heights by height.** A height range with its own layer height is
  stored in `Metadata/layer_config_ranges.xml`, as `<objects><object id="N">
  <range min_z max_z><option opt_key="layer_height">`. `N` counts objects in
  the order of their ids, not the order `model_settings.config` lists them in.
  The scripts no longer use one, but the car once had 0.08 mm layers on its
  nose this way.
- **One layer plan per plate with a prime tower.** With the prime tower on,
  Bambu slices only if every object has the same layer heights. Finer layers
  also make the tower deeper; at the usual spot by the back edge, the tower
  ran off the bed.
- **Settings are strings.** In `project_settings.config` every value is a
  string, even numbers and switches: `"enable_support": "1"`. Written as a JSON
  number, Bambu ignores it.
- **The command line packs the plate.** It re-arranges the parts itself, close
  together, and with supports on, even one pair of red halves came out too
  close: "G-code conflicts". `--arrange 0` keeps the layout you give it.
- **No-print corner.** The P1S keeps parts clear of an area at the front left
  of the bed; a part placed at x 10 failed with "too close to exclusion area".
- **Adding a filament touches four kinds of list.** A value per filament
  (temperatures, colours; the AMS drying lists have four each); a value per
  filament per nozzle variant (below); the purge volumes, a grid of every
  filament against every other; and two lists with an entry for the process
  first and the printer last. Some machine lists are as long as the filament
  list only by coincidence. A one-filament project from Bambu's command line
  tells most of them apart. The purges `filaments.py` gives a new filament are
  those of the filament it looks like, and 140 mm3 between two that look
  alike; Bambu Studio recalculates them when you change a swatch.
- **Some filament settings are per nozzle variant.** Lists such as
  `nozzle_temperature` hold a value per filament per variant, and a filament
  can have one variant or two, so a list's length is not a multiple of the
  filament count. `filament_self_index` says which filament each entry belongs
  to, and `filament_extruder_variant` which variant. Copying a filament from one
  project to another has to follow them, or it silently keeps the old values:
  PETG at PLA's 220 °C.
- **A project with several plates.** Plates sit in a grid, as many columns as
  the square root of the plate count rounded up, 307.2 mm apart (the bed and a
  fifth). Each `<plate>` in `model_settings.config` lists its parts as
  `<model_instance>`s, and `wipe_tower_x`/`wipe_tower_y` hold a place for each
  plate. Every other setting is the project's, but an object can override some,
  such as `flush_into_infill`, with its own `<metadata>`: that is how the PETG
  plates keep their purge out of the infill while the top's goes into it.
  Each single-plate project numbers its objects from 1, so merging means
  renumbering them and their mesh files.
- **Check by slicing.** `BambuStudio --slice 0 --outputdir <absolute folder>
  <project.3mf>` writes `result.json`, with `filament_change_times`,
  `total_predication` (seconds) and grams per filament. If the car red plate
  shows 0 filament changes, or the car top black plate uses any filament but
  2, the paint was lost.
