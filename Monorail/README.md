# Monorail Countdown

![The monorail countdown, display side](render-side.png)

![The monorail countdown from the nose](render-nose.png)

*Renders from Fusion, in the colours it prints in. A photo of the print will
replace them.*

A Disney monorail desk countdown. Three 20 mm cubes in the window band show the
days left, over **DAYS 'TIL VACATION**; the other side reads **VACATION IS
CALLING!** for when no trip is booked yet. The fourth cube lives in a pocket in
the tail. The car straddles a straight concrete-style beam on two pylons.

Like everything in this repository, it is generated entirely by a Fusion
Python script, starting from an empty document. Nothing is modelled by hand.

## Build it

1. Install this repository's two fonts, `CountdownDigits-Regular.ttf` and
   `CountdownLettering-Regular.ttf` from [`Font/build`](../Font/build), with
   Font Book, then restart Fusion — it reads its font list at launch. Without
   them the script falls back to Waltograph UI, and its report says so.
2. In Fusion, open a new, empty design.
3. **Utilities → Add-ins → Scripts and Add-ins** (Shift+S) → **+** → *Create
   script*, Python. Open its folder and replace the generated `.py` with
   `Monorail Countdown.py`.
4. Click **Run**. It takes from 20 seconds to a couple of minutes, and ends
   with a report of what it built and every check it passed.

Or, with the [ClaudeBridge](../ClaudeBridge) add-in running:

```bash
python3 send.py run "/path/to/Monorail Countdown.py"
```

## What it makes

Eleven bodies, 176.6 × 56 × 76 mm assembled.

| Body | What it is | Print it |
|---|---|---|
| `Car_Display` | The half of the car with the cube slots | Flat on its split face |
| `Car_Back` | The other half | Flat on its split face |
| `Pin_1`–`Pin_3` | Loose pins that line the halves up for gluing | Standing on end |
| `Beam` | The beam and both pylons, one piece | On its side |
| `Foot` | The plate the pylons plug into | Flat |
| `Cube_1`–`Cube_3` | The countdown cubes | A digit face down |
| `Cube_4_Spare` | The fourth cube, kept in the tail | A digit face down |

The car is split down the middle so each half lies flat on its cut face: the
cube slots open upward, the lettering is on the top surface, and nothing
needs support. The beam's top is a ridge that seats in a V in the belly, so the
belly has no ledge to overhang. The spare pocket's roof is a bridge, and its
finger notches are cut in its top and bottom walls, which stand upright in
print.

## Colours

| | Car (four AMS slots) |
|---|---|
| 1 white | The body |
| 2 black | Window band, cube frames, tail coupler, windshield |
| 3 red | Stripe, tail lights |
| 4 gold | Lettering |

The beam and foot are grey, printed on their own plate. The cubes are white
with black digits.

Every colour region is a real step in the surface — recessed 0.6–0.8 mm or
raised — never just a painted face, because the slicer's colour fill needs an
edge to stop at. The windshield is recessed one step deeper than the band, so
it still reads as glass in black.

The script also paints the model in Fusion in these colours
(`PREVIEW_COLOURS`). Fusion's 3MF export keeps those colours, but Bambu Studio
does not read them. [`bambu/`](bambu) converts them to Bambu's own painting
and makes ready-to-print files, with each part turned and laid out on its
plate. Otherwise, paint in the slicer.

## Printing

Sliced in Bambu Studio 2.07 for a P1S with a 0.4 mm nozzle, 0.2 mm layers and
PLA, 8% lightning infill, no supports, and 0.08 mm layers on the car's nose:

| Plate | Time | Filament changes | Filament |
|---|---|---|---|
| Car halves and pins | 13.9 h | 298 | ~204 g |
| Beam and foot | 0.9 h | 0 | 29 g |
| Cubes (optional) | 3.6 h | 70 | 60 g |

The car plate's changes come from the nose: lying flat, it stands upright, so
its windshield and red lip put three colours in almost every layer. With the
nose and tail plain white it would be about 7.4 h.

**The nose's layers.** Each half lies on its split face, so near the top of the
half the nose curves away from the flank as a shallow slope. There, 0.2 mm
layers print as steps up to 2 mm wide, and they showed on the first test print.
From 16 mm up the car plate uses 0.08 mm layers instead. Test pieces at 0.2,
0.12 and 0.08 mm all printed acceptably, but 0.08 mm looked and felt the best.
It costs about 40 g of filament and 4.5 h per car plate, almost all of it in
extra colour changes, since every colour on the car meets in that band.

**No supports.** Every face that looks down in print slopes at 40° or
steeper, apart from a few short flat spans that print fine unsupported: the
pin sockets' ends, the tail lights' 2 mm undersides, and the spare pocket's
roof. The roof is a 21.7 mm bridge held on three sides, like the ship's
transom pocket. The pocket's finger notches used to be in its side walls.
Lying on the split face, those walls are the roof, so the notches were holes
in the bridge, and they fell apart on a test print. They are now in the top
and bottom walls, rounded where the finger goes, with 45° flanks.

**Assembly.** Push the pins into one half's sockets, glue the halves together,
and glue the pylons into the foot. The car lifts on and off the beam. Its V seats
on the beam's ridge, and a bump on the ridge drops into a notch in the V, so
it always sits centred.

## The cubes

These are the same four cubes as the [Cruise Ship](../Cruise%20Ship)'s — same
size, same digits, same fit — so one set works in either model. You only need
to print them for a second set.

| Cube | Digits |
|---|---|
| `Cube_1` | 1 2 3 4 5 6 |
| `Cube_2` | 0 2 3 4 7 8 |
| `Cube_3` | 0 1 3 5 7 9 |
| `Cube_4_Spare` | 0 1 2 6 8 9 |

Four cubes, not three, because the arithmetic demands it: to show every count
from 000 to 365, the digits 0–3 each need three cubes (000, 111, 222, 333) and
4–9 each need two (344, 355, 266, ...). That is 24 faces, which four cubes
have exactly and three cannot — so no face is blank. The digits are in
[Countdown Digits](../Font), where the 9 is the 6 upside down: there is nothing
to tell apart, since either face reads as a 6 one way up and a 9 the other.
(`MARK_6_AND_9` puts back the small Mickey head that used to mark them.) The
script re-proves all 366 counts every time it runs.

## Changing it

The settings are at the top of the script: the lettering (`CAR_TEXT`), the
fonts (`DIGIT_FONTS`, `TEXT_FONTS`), the fits (`cubeClearance`, `spareClearance`, `grooveFit`, `pinFit`, `socketFit`),
`PREVIEW_COLOURS`, and `SPLIT_CAR` to build the car as one piece. Every layout
rule is checked before anything is built, and again with measurements after:
if a change makes two features collide, the script stops and says which, rather
than quietly building something that will not print.

## Status

Built and checked in Fusion and in the slicer. The first test print of the
car came out well; a second, with the beam and foot, is under way. Since then
the lettering and digits have moved to this repository's own
[fonts](../Font) and the wording has changed; that version has not been
printed yet.
