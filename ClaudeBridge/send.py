"""Client for the ClaudeBridge add-in. Runs outside Fusion, with any Python 3.

    python3 send.py ping
    python3 send.py run  <script.py>
    python3 send.py exec <code.py>
    python3 send.py snap <out.png> [view] [width] [height]

Prints the reply as JSON and exits 0 if the command succeeded, 1 if it failed
or timed out. It talks to the add-in through the inbox/ and outbox/ folders
beside this file, so it must stay in the add-in's folder (or import send()
from it). Paths are made absolute before sending: the add-in does not share
this process's working directory.

ping waits 30 s for a reply; everything else waits 10 minutes, long enough for
a heavy modelling script. A timeout does not cancel anything -- Fusion keeps
working, and the reply still lands in outbox/<id>.json when it finishes.
"""

import json, os, sys, time, uuid

HERE = os.path.dirname(os.path.abspath(__file__))


def send(cmd, timeout=600.0):
    """Send one command dict and wait for its reply dict.

    Gives the command a random id unless it has one, writes it atomically
    into inbox/, and polls outbox/ for the answer. On a timeout the reply
    says whether Fusion ever picked the command up, which tells a stopped
    add-in apart from a long-running command."""
    cid = cmd.setdefault('id', uuid.uuid4().hex[:10])
    inbox, outbox = os.path.join(HERE, 'inbox'), os.path.join(HERE, 'outbox')
    os.makedirs(inbox, exist_ok=True)
    tmp = os.path.join(inbox, cid + '.tmp')
    with open(tmp, 'w') as f:
        json.dump(cmd, f)
    os.replace(tmp, os.path.join(inbox, cid + '.json'))
    reply = os.path.join(outbox, cid + '.json')
    started = time.time()
    while time.time() - started < timeout:
        if os.path.exists(reply):
            with open(reply) as f:
                return json.load(f)
        time.sleep(0.25)
    pending = os.path.exists(os.path.join(inbox, cid + '.json'))
    return {'id': cid, 'ok': False,
            'error': 'No reply after {:.0f} s. {}'.format(
                timeout, 'Nobody picked the command up -- is ClaudeBridge running in Fusion?'
                if pending else 'Fusion took the command but has not finished it.')}


def main(argv):
    op = argv[1] if len(argv) > 1 else 'ping'
    if op == 'ping':
        cmd = {'op': 'ping'}
    elif op == 'run':
        cmd = {'op': 'run_script', 'path': os.path.abspath(argv[2])}
    elif op == 'exec':
        with open(argv[2]) as f:
            cmd = {'op': 'exec', 'code': f.read()}
    elif op == 'snap':
        cmd = {'op': 'snap', 'path': os.path.abspath(argv[2]),
               'view': argv[3] if len(argv) > 3 else 'iso',
               'width': int(argv[4]) if len(argv) > 4 else 1600,
               'height': int(argv[5]) if len(argv) > 5 else 1000}
    else:
        sys.exit('Unknown command ' + op)
    timeout = 30.0 if op == 'ping' else 600.0
    reply = send(cmd, timeout)
    print(json.dumps(reply, indent=1))
    sys.exit(0 if reply.get('ok') else 1)


if __name__ == '__main__':
    main(sys.argv)
