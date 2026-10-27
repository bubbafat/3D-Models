# Cruise Ship Countdown

*Photo to come.*

A Disney Cruise Line desk countdown. Three 20 mm cubes along the port side show
the days left, over **Days 'Til Disney**; the starboard side reads **Let's Book
a Cruise!** for when no trip is booked yet. Two raked funnels carry Mickey
emblems, lifeboats line the hull, and the fourth cube lives in a pocket in the
transom.

Like everything in this repository, it is generated entirely by a Fusion
Python script, starting from an empty document. Nothing is modelled by hand.

## Build it

1. Install the **Waltograph UI** font for all users (Font Book → *Install for:
   All Users*), then restart Fusion — it reads its font list at launch. The
   script tells you if it cannot find the font.
2. In Fusion, open a new, empty design.
3. **Utilities → Add-ins → Scripts and Add-ins** (Shift+S) → **+** → *Create
   script*, Python. Open its folder and replace the generated `.py` with
   `DCL Countdown Ship.py`.
4. Click **Run**. It takes 30–90 seconds and ends with a report of what it
   built and every check it passed.

Or, with the [ClaudeBridge](../ClaudeBridge) add-in running:

```bash
python3 send.py run "/path/to/DCL Countdown Ship.py"
```

## What it makes

Eight bodies; the hull is 152.4 mm long and 45 mm across.

| Body | What it is |
|---|---|
| `Hull` | The hull: the lettering, lifeboats and the transom pocket |
| `Body` | The superstructure decks, seated in a 0.4 mm locating recess on the hull |
| `Stack_1`, `Stack_2` | The funnels, each keyed onto two pins |
| `Cube_1`–`Cube_3` | The countdown cubes |
| `Cube_4_Spare` | The fourth cube, kept in the transom pocket |

The cubes stand 4 mm proud of their slots so they can be pulled out, and the
transom pocket has finger notches either side. Print the cubes with a digit
face down.

## The cubes

These are the same four cubes as the [Monorail](../Monorail)'s — same size,
same digits, same fit — so one set works in either model.

| Cube | Digits |
|---|---|
| `Cube_1` | 1 2 3 4 5 6 |
| `Cube_2` | 0 2 3 4 7 8 |
| `Cube_3` | 0 1 3 5 7 9 |
| `Cube_4_Spare` | 0 1 2 6 8 9 |

Four cubes, not three, because the arithmetic demands it: to show every count
from 000 to 365, the digits 0–3 each need three cubes (000, 111, 222, 333) and
4–9 each need two (344, 355, 266, ...). That is 24 faces, which four cubes
have exactly and three cannot — so no face is blank, and a small Mickey head
under the 6 and the 9 tells them apart. The script re-proves all 366 counts
every time it runs.

## Changing it

The settings are at the top of the script: the lettering (`HULL_TEXT`), hull
and deck proportions, funnel placement, and the fits (`cubeClearance`,
`spareClearance`). Layout rules are checked as it builds; if a change makes
features collide, it stops and says which.

## Status

Printed and in use. After the first prototype it went through a punch list:
lifeboats are now dropped wherever the hull falls away under them, the
transom pocket gained finger notches, the funnel sockets got relief at the
mouth, the lettering got bigger, and the second side got its own wording.

The cube digits are now recessed 0.84 mm (exactly two 0.42 mm walls) instead
of 0.6 mm, to fix ragged edges on the printed digits; that change has not been
checked in a print yet.
