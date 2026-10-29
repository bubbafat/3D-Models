# Bambu Studio print files

Makes the monorail's print files for Bambu Studio, with no clicking in the
slicer:

- painted in the model's four colours;
- each part turned to its print orientation;
- supports painted on exactly where they are needed;
- laid out on five plates;
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
  changed. Supports come out on for the car bottom and the red halves, in each
  part's own filament, and only where they are painted.

## Run it

From this folder:

```bash
zsh make_print_files.sh "<output folder>" "<your four-filament project>.3mf"
```

It takes about a minute, most of it Fusion building the model. It leaves a
new document open in Fusion, built from
`Monorail Countdown.py`. Close that document without saving; the script never
closes any of your documents. The output folder gets five files, each with your
four AMS filaments, 1 white, 2 black, 3 red, 4 gold, of which it uses:

| File | Parts | Uses |
|---|---|---|
| `Monorail - car bottom.3mf` | The car's bottom and the four pins | 1 white |
| `Monorail - car red.3mf` | The two red halves | 3 red, 4 gold |
| `Monorail - car top.3mf` | The car's top | 1 white, 2 black |
| `Monorail - beam plate.3mf` | Beam and foot | 1, in grey |
| `Monorail - cubes.3mf` | The four cubes | 1 white, 2 black |

Each is one car. To print a batch, add copies of the part in Bambu Studio; the
paint and supports copy with it.

Each line it ends with is one plate's slice: filament changes, hours, minutes
of flushing, and grams per filament.

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
3. Bambu Studio's command line turns each plate into a Bambu project.
4. `inject_paint.py` writes Bambu's paint onto every triangle of that project,
   checking vertex by vertex that the meshes still match, and swaps in your
   project's settings. A plate with painted supports gets tree supports in
   manual mode, which supports the painted faces and nothing else.
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
  together. With supports on, five pairs of red halves came out too close and
  the slice failed with "G-code conflicts"; in Bambu Studio, space them out by
  hand.
- **Check by slicing.** `BambuStudio --slice 0 --outputdir <absolute folder>
  <project.3mf>` writes `result.json`, with `filament_change_times`,
  `total_predication` (seconds) and grams per filament. If the car red or car
  top plate shows 0 filament changes, the paint was lost.
