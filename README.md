# 3D-Models

3D-printable models generated entirely by Autodesk Fusion Python scripts. Run
a script in an empty design and it builds every part, checks its own geometry,
and finishes with a report of what it made — nothing is modelled by hand. Each
model's folder holds its script and a README with build and print details.

## Models

### [Cruise Ship](Cruise%20Ship)

<a href="Cruise%20Ship"><img src="Cruise%20Ship/photo-countdown.jpg" width="480" alt="The cruise ship countdown"></a>

A Disney Cruise Line ship that counts down the days to a trip.

- Three 20 mm cubes along the hull show the count over **Days 'Til We Sail**;
  the other side reads **Let's Book a Cruise!**
- Two raked funnels with Mickey emblems, a row of lifeboats, stepped decks.
- The spare cube lives in a pocket in the transom.
- 152.4 mm long, 8 printable parts.
- **Status:** printed and in use. The photo shows the first print, from
  before the switch to the [Countdown fonts](Font) and new wording.

Script: [`DCL Countdown Ship.py`](Cruise%20Ship/DCL%20Countdown%20Ship.py)

### [Monorail](Monorail)

<a href="Monorail"><img src="Monorail/render-nose.png" width="480" alt="The monorail countdown"></a>

A Disney monorail on its beam, counting down the same way.

- Three cubes in the window band over **DAYS 'TIL VACATION**; the other side
  reads **VACATION IS CALLING!**
- The car straddles a straight beam on two pylons; a bump on the beam centres
  it. The spare cube stows in the tail.
- 177 × 56 × 76 mm, 11 printable parts. The car prints in two halves, each
  flat on its cut face, in four colours; the beam and foot in grey.
- **Status:** the first test print of the car came out well; a second, with
  the beam and foot, is under way. The pictures are renders.

Script: [`Monorail Countdown.py`](Monorail/Monorail%20Countdown.py)

### The cubes

Both models use the same four countdown cubes — same size, same digits, same
fit — so one set works in either. Four cubes are the fewest that can show
every count from 000 to 365; each model's README explains why. Their digits
are in Countdown Digits, where the 9 is the 6 upside down.

## Tools

### [Countdown fonts](Font)

Two fonts drawn for this repository, so the models need no licensed font:
**Countdown Digits** for the cubes and **Countdown Lettering** for the words.
Each letter is a few pen lines in an SVG file, drawn with one broad-nib brush
by a Python script that writes a TrueType font. Edit a letter's lines in any
vector editor and rebuild. A second script measures how well each font will
print at the size the models use it.

### [ClaudeBridge](ClaudeBridge)

A small Fusion add-in that lets another program drive Fusion through a folder:
drop a JSON command in, get a JSON reply back. No network involved.

- **Run a script** in a new document and get its report back as text, plus
  every part it built with sizes and volumes.
- **Run Python inside Fusion** to measure or query the open model.
- **Save pictures** of the model from any angle.

Built so an AI coding assistant (Claude Code) could build, check and look at
these models without someone pressing Run and copying dialogs; any program can
use it. Install it by putting the folder in Fusion's add-ins folder; the
[README](ClaudeBridge/README.md) covers setup, every command and security
(it runs Python you send it, so only use it on your own machine), and
[CLAUDE.md](ClaudeBridge/CLAUDE.md) is the guide for an AI assistant.

## Requirements

| | Needs |
|---|---|
| The models | **Autodesk Fusion** (macOS or Windows), and the two [Countdown fonts](Font) installed, for their lettering and digits |
| The fonts, to change them | **Python 3** with the packages in [`Font/requirements.txt`](Font/requirements.txt) |
| ClaudeBridge | **Autodesk Fusion**, and **Python 3** for its `send.py` client |

## License

[MIT](LICENSE).
