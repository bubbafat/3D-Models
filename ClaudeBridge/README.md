# ClaudeBridge

A small Autodesk Fusion add-in that lets a program outside Fusion run scripts
in it, query the model and save pictures of it — through a folder, with no
network involved.

Fusion has no command line and no API you can reach from outside the
application. ClaudeBridge adds the smallest one that works: you drop a JSON
command into its `inbox/` folder, Fusion runs it, and the answer appears in
`outbox/`. It was built so an AI coding assistant (Claude Code) could do the
loop a person otherwise does by hand — run a modelling script, read its
report, check the result, look at it, fix the script, run it again — but any
program that can write a file can use it.

`send.py` is a ready-made command-line client.

## What you can do with it

- **Run a Fusion script** in a fresh document and get back the text of every
  message box it shows, plus every body it built with its size and volume. The
  message boxes are captured, not shown, so nothing waits for a click.
- **Run any Python inside Fusion** and get back whatever it leaves in a
  variable called `result` — measure a face, test whether a point is inside a
  body, change the camera, count faces.
- **Save the viewport as an image** from a named or exact angle, orthographic,
  fitted to the model or zoomed on a point.

## Requirements

- Autodesk Fusion on macOS or Windows.
- Python 3 for `send.py` (any recent version; it only uses the standard
  library). The add-in itself runs on Fusion's built-in Python.

## Install

Put this `ClaudeBridge` folder in Fusion's add-ins folder:

| | Add-ins folder |
|---|---|
| macOS | `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/` |
| Windows | `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\` |

Either copy it, or — so a `git pull` updates it — link it. On macOS, from a
clone of this repository:

```bash
ln -s "$PWD/ClaudeBridge" "$HOME/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/ClaudeBridge"
```

The add-in creates `inbox/`, `outbox/` and `status.json` beside itself when it
starts; `.gitignore` keeps them out of the repository.

## Start and stop

In Fusion: **Utilities → Add-ins → Scripts and Add-ins** (Shift+S), **Add-Ins**
tab, **ClaudeBridge**, **Run**. If it is not in the list, close and reopen that
dialog. Stop it the same way. It does not start with Fusion unless you tick
**Run on Startup** — and given what it can do (see Security), leaving that off
is the better default.

While it runs, `status.json` contains `"running": true`.

## Use it

From the add-in's folder:

```bash
python3 send.py ping                                  # is it running?
python3 send.py run  "/path/to/My Script.py"          # run a script in a new document
python3 send.py exec measure.py                       # run Python inside Fusion
python3 send.py snap /tmp/view.png iso 1600 1000      # save a picture of the model
```

Each prints the reply as JSON and exits 0 on success, 1 on failure or timeout.

`ping` replies within a second when the add-in is running:

```json
{"id": "d757465d4b", "ok": true,
 "result": {"version": "2705.1.25", "document": "Untitled", "bridgeDocs": 0},
 "elapsed": 0.0}
```

An `exec` file is plain Python. It can use `adsk`, `app`, `ui`, `design` and
`root` (the active design and its root component) without importing them, and
two helpers, `bodies()` and `snap()`:

```python
# measure.py -- the largest body, and whether the point 10 mm above the origin is inside it
b = max(root.bRepBodies, key=lambda b: b.physicalProperties.volume)
p = adsk.core.Point3D.create(0, 0, 1.0)            # cm: the API's own unit
inside = b.pointContainment(p) == adsk.fusion.PointContainment.PointInsidePointContainment
result = {'largest': b.name, 'point_inside': inside, 'all': bodies()}
```

## Commands

Write commands yourself if you would rather not use `send.py`; the protocol is
just files.

A command is a JSON object saved as `inbox/<id>.json`. Write it to
`inbox/<id>.tmp` first and rename it, so the add-in never reads half a file.
The reply arrives as `outbox/<id>.json`:

```json
{"id": "<id>", "ok": true,  "result": { ... }, "elapsed": 1.23}
{"id": "<id>", "ok": false, "error": "<Python traceback>", "elapsed": 0.2}
```

| `op` | Arguments | Does | `result` |
|---|---|---|---|
| `ping` | — | Checks the bridge is alive | `version`, `document`, `bridgeDocs` |
| `run_script` | `path`; `new_document` (default true); `close_previous` (default true) | Loads the script fresh from disk and calls its `run()`, in a new design document | `messages` (each message box's text), `captured`, `seconds`, `document`, `bodies` |
| `exec` | `code` | Runs the Python on Fusion's main thread | `result` (the variable), `stdout` (anything printed) |
| `snap` | `path`; `view` (default `iso`); `width`, `height`; `target`, `distance` (mm) | Saves the viewport as an image | `path`, `saved`, `view` |

`bodies()` and `run_script` describe each body as
`{"name", "min": [x, y, z], "max": [x, y, z], "volume", "visible"}`, in mm and
mm³.

**Views.** `snap` takes `display`, `back`, `nose`, `tail`, `top`, `bottom`,
`iso`, `iso_nose`, `iso_tail` or `iso_back` — looking at the +y side, the −y
side, the +x end, the −x end, from above, from below, and four corners. They
assume the model is Z-up, whatever Fusion's own view preference is. From
`exec`, `snap()` also takes an exact `(direction, up)` pair, and a `target`
point and `distance` to aim at one spot; then set the camera's `viewExtents`
to zoom.

**Documents.** `run_script` opens a new design document for each run and, by
default, closes the ones its earlier runs opened — without saving. It never
closes a document it did not open. If you save one of its documents to keep
it, the next run still closes it (your saved version is safe; unsaved edits are
not), so pass `"close_previous": false` or switch documents first.

**Units.** Fusion's API works in centimetres. Everything ClaudeBridge takes or
returns is millimetres. Inside `exec` code you are using the API directly, so
it is centimetres there.

## How it works

A background thread polls `inbox/` every 0.3 s. Fusion only allows its API on
its main thread, so the thread just claims each file (renaming it to
`<id>.json.claimed`) and fires a Fusion custom event; Fusion then runs the
command on the main thread and the reply is written. Commands run one at a
time, in order, and Fusion is busy while one runs — a script that takes 30
seconds freezes Fusion's window for 30 seconds, just as pressing Run would.

## Security

`exec` runs **any Python it is given**, with your user account's permissions,
inside your signed-in Fusion session. Nothing listens on the network: a command
can only come from something that can already write files in the add-in's
folder — on a personal computer, you and the programs you run. Even so:

- stop the add-in when you are not using it;
- do not run it on a computer whose other users or programs you do not trust;
- read commands from sources you do not control before you send them.

## Troubleshooting

| Symptom | Meaning |
|---|---|
| `No reply ... Nobody picked the command up` | The add-in is not running. Start it (Shift+S → Add-Ins → ClaudeBridge → Run). |
| `No reply ... Fusion took the command but has not finished it` | It is still working (check Fusion's CPU use), or a dialog is open in Fusion waiting for a click. The reply still appears in `outbox/` when it finishes; a timeout cancels nothing. |
| `ClaudeBridge failed to start` in Fusion | The message includes the traceback. Usually a permissions problem creating `inbox/` or `outbox/`. |
| Edits to `ClaudeBridge.py` have no effect | Fusion loaded the add-in when it started. Stop it and run it again. |
| Message boxes still pop up during `run_script` | `captured` is `false` in the reply: this Fusion version would not let the add-in intercept them. |

## Files

| File | |
|---|---|
| `ClaudeBridge.py` | The add-in. Its docstring is the full reference. |
| `ClaudeBridge.manifest` | Tells Fusion this folder is an add-in. |
| `send.py` | Command-line client; `send()` can be imported. |
| `CLAUDE.md` | Working notes for an AI assistant using the bridge. |
