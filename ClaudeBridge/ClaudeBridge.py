"""ClaudeBridge -- lets a program outside Fusion drive Fusion through a folder.

Fusion has no command line and no network API for running scripts. This
add-in gives it a very small one: drop a JSON command into inbox/ beside this
file, and the add-in runs it inside Fusion and writes the answer to outbox/.
It was built so an AI coding assistant (Claude Code) could run a Fusion
modelling script, read its report, query the result and look at it -- the
loop a person otherwise does by hand -- but anything that can write a file can
use it. send.py, beside this file, is a ready-made client.

STARTING AND STOPPING
    Utilities -> Add-ins -> Scripts and Add-ins (Shift+S), Add-Ins tab,
    ClaudeBridge, Run. Stop it the same way. While it runs, status.json says
    {"running": true, ...}. It does not start with Fusion unless you tick
    "Run on Startup".

PROTOCOL
    A command is a JSON object written to inbox/<id>.json, where <id> is any
    file-name-safe string:

        {"id": "a1b2c3", "op": "ping"}

    Write it to inbox/<id>.tmp first and rename it to .json, so the add-in
    never reads a half-written file. The add-in claims a command by renaming
    it to <id>.json.claimed, runs it, deletes it, and writes the reply to
    outbox/<id>.json (also via a .tmp and a rename):

        {"id": "a1b2c3", "ok": true,  "result": {...}, "elapsed": 0.01}
        {"id": "a1b2c3", "ok": false, "error": "<Python traceback>", "elapsed": 0.2}

    Replies are left in outbox/ for the client to read and remove.

COMMANDS
    ping
        -> {"version", "document", "bridgeDocs"}: Fusion's version, the
        active document's name, and how many documents the bridge has open.

    run_script   path, new_document=true, close_previous=true
        Import the Python file at `path` and call its run({}), exactly as
        Fusion's Run button would, but in a fresh design document of its own.
        Message boxes the script shows are captured instead of displayed --
        a modal dialog would freeze Fusion until someone clicked it -- and
        returned as text.
        -> {"messages": [...], "captured": bool, "seconds", "document",
            "bodies": [...]}  (bodies as in exec's bodies() below)
        close_previous closes, without saving, the documents earlier
        run_script calls opened. It never touches any other document.

    exec   code
        Run Python source on Fusion's main thread. The code sees `adsk`,
        `app`, `ui`, `design` and `root` (the active design and its root
        component), plus the helpers snap() and bodies(). Whatever it leaves
        in a variable named `result` is sent back (as JSON, with str() for
        anything JSON cannot hold), together with anything it printed.
        -> {"result": ..., "stdout": "..."}

    snap   path, view="iso", width=1600, height=1000, target=null, distance=null
        Save the active viewport as an image. See snap() for the views.
        -> {"path", "saved", "view"}

UNITS
    Fusion's API works in centimetres. Everything this add-in takes or
    returns -- bounding boxes, volumes, snap targets and distances -- is in
    millimetres (volumes in mm3).

HOW IT RUNS
    A background thread polls inbox/ every 0.3 s. Fusion's API may only be
    used from Fusion's main thread, so the thread does nothing but claim the
    file and fire a custom event; Fusion then calls CommandHandler.notify on
    the main thread, which does the work. Commands therefore run one at a
    time, in the order they were claimed, and Fusion's own window is busy
    while one runs -- a 30 second modelling script means 30 seconds of a
    frozen Fusion, exactly as if you had pressed Run yourself.

SECURITY
    exec runs any Python it is given, with your user account's rights and
    inside your signed-in Fusion session. Nothing listens on the network:
    a command can only come from something that can already write files in
    this folder, which on a personal Mac means you and the programs you run.
    Even so, stop the add-in when you are not using it, and do not run it on
    a machine other people's programs share.

LIMITS
    - A modal dialog raised by anything other than a run_script script (a
      save prompt, an update notice) still blocks the main thread, and with
      it every command, until someone dismisses it.
    - status.json is written on start and stop only; it goes stale, not
      false, if Fusion crashes.
    - bodies() lists the root component's bodies, not those inside
      sub-component occurrences.
    - The named views assume a Z-up model.
"""

import adsk.core, adsk.fusion, traceback, threading, json, os, time, io, contextlib
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
INBOX = os.path.join(HERE, 'inbox')
OUTBOX = os.path.join(HERE, 'outbox')
EVENT_ID = 'ClaudeBridgeCommand'

app = None
customEvent = None
handlers = []             # kept referenced: Fusion drops handlers Python garbage-collects
stopFlag = threading.Event()
bridgeDocs = []           # documents this bridge created, newest last

# Named views, as (direction from the target to the eye, up vector), in model
# coordinates with z up -- set explicitly, because Fusion's named views follow
# the document's Y-up or Z-up preference. 'display' looks at the +y side,
# 'nose' at the +x end.
VIEWS = {
    'display': ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    'back':    ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
    'nose':    ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    'tail':    ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    'top':     ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),
    'bottom':  ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
    'iso':     ((0.8, 1.0, 0.6), (0.0, 0.0, 1.0)),
    'iso_nose': ((1.0, 0.7, 0.45), (0.0, 0.0, 1.0)),
    'iso_tail': ((-1.0, 0.7, 0.45), (0.0, 0.0, 1.0)),
    'iso_back': ((-0.8, -1.0, 0.6), (0.0, 0.0, 1.0)),
}


def snap(path, view='iso', width=1600, height=1000, target=None, distance=None):
    """Save the active viewport, orthographic, from a named view or an
    explicit (direction, up) pair. Fits to the whole model unless a target
    point (mm) and distance (mm) are given.

    view is a key of VIEWS, or a pair of 3-vectors: the direction from the
    target towards the eye, and the up vector. With a target, the camera is
    aimed there and not fitted -- set the camera's viewExtents afterwards
    (from exec) to zoom. Leaves the camera where it put it."""
    vp = app.activeViewport
    direction, up = VIEWS[view] if isinstance(view, str) else view
    n = sum(c * c for c in direction) ** 0.5
    direction = [c / n for c in direction]
    cam = vp.camera
    cam.isSmoothTransition = False
    cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
    tgt = [c / 10.0 for c in target] if target else [0.0, 0.0, 0.0]
    dist = (distance / 10.0) if distance else 100.0
    cam.target = adsk.core.Point3D.create(*tgt)
    cam.eye = adsk.core.Point3D.create(*[t + d * dist for t, d in zip(tgt, direction)])
    cam.upVector = adsk.core.Vector3D.create(*up)
    cam.isFitView = target is None
    vp.camera = cam
    if target is None:
        vp.fit()
    # Let Fusion redraw before capturing, or the image can show the old view.
    adsk.doEvents()
    vp.refresh()
    adsk.doEvents()
    ok = vp.saveAsImageFile(path, width, height)
    return {'path': path, 'saved': bool(ok), 'view': view if isinstance(view, str) else 'custom'}


def bodies():
    """Every body in the active design's root component: name, bounding box
    (mm), volume (mm3) and visibility. Empty when no design is active."""
    design = adsk.fusion.Design.cast(app.activeProduct)
    out = []
    if not design:
        return out
    for b in design.rootComponent.bRepBodies:
        bb = b.boundingBox
        out.append({
            'name': b.name,
            'min': [round(v * 10.0, 3) for v in (bb.minPoint.x, bb.minPoint.y, bb.minPoint.z)],
            'max': [round(v * 10.0, 3) for v in (bb.maxPoint.x, bb.maxPoint.y, bb.maxPoint.z)],
            'volume': round(b.physicalProperties.volume * 1000.0, 2),
            'visible': b.isVisible,
        })
    return out


def op_ping(cmd):
    """Is the bridge alive, and what is Fusion looking at?"""
    doc = app.activeDocument
    return {'version': app.version, 'document': doc.name if doc else None,
            'bridgeDocs': len(bridgeDocs)}


def op_run_script(cmd):
    """Run a Fusion script file as the Run button would, in a new document,
    returning the text of its message boxes and the bodies it left behind.

    The script is loaded fresh from disk every time (under a fixed module
    name, so an edited file is always picked up) and its run() is called
    with an empty context. If run() raises past its own error handling, the
    exception propagates and the reply is ok: false with the traceback."""
    path = cmd['path']
    if not os.path.isfile(path):
        raise RuntimeError('No script at ' + path)
    if cmd.get('close_previous', True):
        # Only documents this bridge opened, and without saving: they are
        # scratch builds, and the user's own documents are never touched.
        while bridgeDocs:
            doc = bridgeDocs.pop()
            try:
                if doc.isValid:
                    doc.close(False)
            except:
                pass
    if cmd.get('new_document', True):
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        bridgeDocs.append(doc)

    # Capture the script's message boxes instead of showing them: a modal
    # dialog would sit on the main thread until someone clicked it. The patch
    # is on the UserInterface class, so it is in force only for the duration
    # of this call and is always put back; if the class refuses the patch,
    # the boxes are shown as usual and 'captured' says so.
    messages = []
    original = adsk.core.UserInterface.messageBox
    patched = False

    def capture(self, text, title='', buttons=0, icon=0):
        messages.append(text)
        return adsk.core.DialogResults.DialogOK
    try:
        adsk.core.UserInterface.messageBox = capture
        patched = True
    except Exception:
        pass

    spec = importlib.util.spec_from_file_location('claude_bridge_target', path)
    module = importlib.util.module_from_spec(spec)
    started = time.time()
    try:
        spec.loader.exec_module(module)
        module.run({})
    finally:
        if patched:
            adsk.core.UserInterface.messageBox = original
    return {'messages': messages, 'captured': patched,
            'seconds': round(time.time() - started, 1),
            'document': app.activeDocument.name if app.activeDocument else None,
            'bodies': bodies()}


def op_exec(cmd):
    """Run arbitrary Python on the main thread; see the module docstring for
    what the code can see. Anything it prints is captured, not lost."""
    design = adsk.fusion.Design.cast(app.activeProduct)
    ns = {'adsk': adsk, 'app': app, 'ui': app.userInterface, 'design': design,
          'root': design.rootComponent if design else None,
          'snap': snap, 'bodies': bodies, 'result': None}
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(cmd['code'], ns)
    return {'result': ns.get('result'), 'stdout': out.getvalue()}


def op_snap(cmd):
    """Save the viewport as an image; arguments as for snap()."""
    return snap(cmd['path'], cmd.get('view', 'iso'), cmd.get('width', 1600),
                cmd.get('height', 1000), cmd.get('target'), cmd.get('distance'))


OPS = {'ping': op_ping, 'run_script': op_run_script, 'exec': op_exec, 'snap': op_snap}


def write_reply(cid, reply):
    """Write a reply to outbox/<cid>.json atomically: a client polling for the
    file never sees it half-written. default=str keeps an exec result that
    JSON cannot hold from losing the whole reply."""
    tmp = os.path.join(OUTBOX, cid + '.tmp')
    with open(tmp, 'w') as f:
        json.dump(reply, f, indent=1, default=str)
    os.replace(tmp, os.path.join(OUTBOX, cid + '.json'))


class CommandHandler(adsk.core.CustomEventHandler):
    """Runs on Fusion's main thread, once per claimed command file. Whatever
    happens, a reply is written and the claimed file removed, so a client is
    never left waiting on a command that failed."""

    def notify(self, args):
        claimed = args.additionalInfo
        cid = os.path.basename(claimed).split('.')[0]
        started = time.time()
        try:
            with open(claimed) as f:
                cmd = json.load(f)
            cid = cmd.get('id', cid)
            op = OPS.get(cmd.get('op'))
            if op is None:
                raise RuntimeError('Unknown op {!r}; known: {}'.format(cmd.get('op'), sorted(OPS)))
            reply = {'id': cid, 'ok': True, 'result': op(cmd)}
        except Exception:
            reply = {'id': cid, 'ok': False, 'error': traceback.format_exc()}
        reply['elapsed'] = round(time.time() - started, 2)
        try:
            write_reply(cid, reply)
        finally:
            try:
                os.remove(claimed)
            except OSError:
                pass


class Poller(threading.Thread):
    """Watches inbox/ and hands each new command to the main thread. It never
    touches the Fusion API itself beyond fireCustomEvent, which is the one
    call documented as safe from another thread."""

    def __init__(self):
        super().__init__(daemon=True)

    def run(self):
        while not stopFlag.wait(0.3):
            try:
                names = sorted(n for n in os.listdir(INBOX) if n.endswith('.json'))
            except OSError:
                continue
            for name in names:
                path = os.path.join(INBOX, name)
                claimed = path + '.claimed'
                try:
                    os.rename(path, claimed)     # claim it, so it fires once
                except OSError:
                    continue
                app.fireCustomEvent(EVENT_ID, claimed)


def run(context):
    """Fusion calls this when the add-in is started."""
    global app, customEvent
    try:
        app = adsk.core.Application.get()
        os.makedirs(INBOX, exist_ok=True)
        os.makedirs(OUTBOX, exist_ok=True)
        # A previous run that was not stopped cleanly may have left the event
        # registered; registering the same id twice fails.
        try:
            app.unregisterCustomEvent(EVENT_ID)
        except:
            pass
        customEvent = app.registerCustomEvent(EVENT_ID)
        handler = CommandHandler()
        customEvent.add(handler)
        handlers.append(handler)
        stopFlag.clear()
        Poller().start()
        with open(os.path.join(HERE, 'status.json'), 'w') as f:
            json.dump({'running': True, 'started': time.strftime('%Y-%m-%d %H:%M:%S'),
                       'version': app.version}, f)
    except:
        adsk.core.Application.get().userInterface.messageBox(
            'ClaudeBridge failed to start:\n{}'.format(traceback.format_exc()))


def stop(context):
    """Fusion calls this when the add-in is stopped, or when Fusion quits.
    Commands still sitting in inbox/ stay there for the next start."""
    try:
        stopFlag.set()
        if customEvent:
            for h in handlers:
                customEvent.remove(h)
        handlers.clear()
        app.unregisterCustomEvent(EVENT_ID)
        with open(os.path.join(HERE, 'status.json'), 'w') as f:
            json.dump({'running': False, 'stopped': time.strftime('%Y-%m-%d %H:%M:%S')}, f)
    except:
        pass
