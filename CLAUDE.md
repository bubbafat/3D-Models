# 3D-Models

Fusion 360 Python scripts that generate printable models from an empty
document, one folder per model: `Cruise Ship/DCL Countdown Ship.py` and
`Monorail/Monorail Countdown.py`. Each folder's README says what the model is
and how it prints. The two models share the same four countdown cubes.

To run a script in the user's Fusion, read its report, measure the result or
look at it, use the ClaudeBridge add-in — see `ClaudeBridge/CLAUDE.md` before
your first command. The user starts the add-in in Fusion; you cannot.

To make the monorail's print files for Bambu Studio, painted and laid out,
use `Monorail/bambu/make_print_files.sh`. Its README explains Bambu's paint
format, the two ways Bambu's command line silently loses the colours, and how
to check the result by slicing from the command line.
