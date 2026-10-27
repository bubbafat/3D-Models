"""Build Monorail Countdown.py in a new Fusion document through ClaudeBridge and
export it as one 3MF, with the script's preview colour on every triangle.

The new document is left open, and no other document is closed, so nothing
you have open in Fusion is lost; close the new one without saving.

    python3 build_and_export.py <ClaudeBridge add-in folder> <script.py> <out.3mf>
"""
import os, sys

bridge, script, out = sys.argv[1], os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3])
sys.path.insert(0, bridge)
from send import send

r = send({'op': 'run_script', 'path': script, 'close_previous': False})
if not r.get('ok'):
    sys.exit('ClaudeBridge could not run the script:\n' + r.get('error', ''))
messages = r['result']['messages']
report = '\n'.join(messages)
print('\n'.join(l for l in report.splitlines() if l.startswith(('Built', 'Bodies', 'Preview'))))
if not any(m.startswith('Built') for m in messages):
    sys.exit(report)

code = ('em = design.exportManager\n'
        'opts = em.createC3MFExportOptions(root, {!r})\n'
        'opts.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh\n'
        'result = em.execute(opts)\n').format(out)
r = send({'op': 'exec', 'code': code})
if not (r.get('ok') and r['result'].get('result') and os.path.exists(out)):
    sys.exit('Export failed: {}'.format(r))
print('Exported', out)
