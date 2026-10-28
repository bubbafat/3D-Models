# Countdown fonts

Two fonts drawn for this repository, so the models need no licensed font:

- **Countdown Digits** (`font.json`): 0–9, for the cube faces. The 9 is the 6
  turned upside down, so the two are interchangeable on a cube.
- **Countdown Lettering** (`lettering.json`): A–Z, a–z, 0–9 and `' ! ? . , - :`,
  for the words on the models. It is a little heavier than the digits,
  because the lettering is printed smaller than the cubes' digits.

The ship and monorail scripts use them, and fall back to Waltograph UI on a
machine that doesn't have them.

Each glyph is a few pen lines. `build_font.py` draws every line with the same
broad-nib brush, merges the strokes into clean outlines, spaces and kerns the
letters, and writes a TrueType font, the only kind Fusion builds text from.

## Build them

```bash
pip install -r requirements.txt
python3 build_font.py --specimen
python3 build_font.py lettering.json --specimen
```

They write `build/CountdownDigits-Regular.ttf` and
`build/CountdownLettering-Regular.ttf`, with sample sheets beside them:

- `specimen.png`: the digits on mock cube faces.
- `CountdownLettering-Regular-words.png`: each model's wording on a band of its
  colours, sized to the band the way the model scripts size it.
- `*-skeletons.png`: each glyph's pen lines over its outline.

Install both `.ttf` files with Font Book, then restart Fusion, which reads its
font list only at launch.

## Check they print

```bash
python3 check_print.py
python3 check_print.py build/CountdownLettering-Regular.ttf \
    --chars "DAYS'TILVCONG!" --text "DAYS 'TIL VACATION" \
    --text "VACATION IS CALLING!" --fit 88 9
```

This draws glyphs and whole phrases at their real size on the model and
measures what a 0.4 mm nozzle can't make cleanly: strokes narrower than two
printed lines (0.84 mm), and gaps between strokes that narrow.

Text is sized by its ink, the way the model scripts size it:

- `--ink` (11 mm unless you give it) makes all ten digits together that tall,
  which is how the cube scripts calibrate.
- `--fit RUN HEIGHT` sizes the phrases the way the model scripts fit their
  lettering. The monorail's car has an 88 x 9 mm band and the ship's hull
  88.2 x 16 mm.
- `--em` sets the font's em directly instead. It is not the text height a
  Fusion report prints: Fusion's height is a different measure (the cube
  digits are 11.7 mm there, a 14.7 mm em here).
- `--compare <font.ttf>` measures another font the same way.

`build/printability.png` marks the problem spots.

Raised lettering is more forgiving than the cube digits: a narrow gap there is
only air, while on a cube it has to be printed in white.

## Change them

- **A whole font:** its `.json`. Under `brush`, `thick` and `thin` are the
  widest and narrowest strokes in font units (capitals are 700 units tall).
  `nibAngle` is the angle the pen is held at, and `swell` thickens the middle
  of each open stroke. Each glyph also has a `tilt` in degrees.
- **Spacing:** `spacing.target` is the average white beside each letter, and
  `minSide` the least. `minSide` keeps any two letters at least `2 x minSide`
  apart even where kerning is ignored. A glyph's `lsbAdjust` and `rsbAdjust`
  nudge one side.
- **One glyph:** its SVG, in `glyphs/` for the digits and in
  `glyphs-lettering/` for the rest. Capitals are named `A_.svg` and so on,
  because macOS does not tell `A.svg` from `a.svg`. Each `<path>` is one pen
  line and each `<circle>` a ball terminal. Move their points in any vector
  editor and rebuild. Only what is inside the flipping group
  (`matrix(1 0 0 -1 0 800)`) is used. Keep the lines in that group, without
  transforms of their own, and use curves rather than arcs.
