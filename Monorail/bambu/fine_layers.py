"""Give every object in a Bambu Studio project finer layers from one height up,
and move the prime tower to where it still fits on the bed.

    python3 fine_layers.py <project.3mf> <from mm> <layer height mm> <tower x> <tower y>

The car halves print lying on the split face, so the nose curves away from the
flank as a shallow slope near the top of each half. From 16 mm up, 0.2 mm
layers show there as steps up to 2 mm wide.

Bambu keeps per-height layer heights in Metadata/layer_config_ranges.xml. It
numbers objects 1, 2, 3... in the order of their ids, not the order of
model_settings.config. With the prime tower on, it slices only if every
object has the same ranges, so every object gets this one. Thinner layers make
the tower deeper; at the tower's usual place by the back edge it runs off the
bed.
"""
import sys, json, zipfile

path, z0, h, tx, ty = sys.argv[1:6]
zin = zipfile.ZipFile(path)
files = {n: zin.read(n) for n in zin.namelist()}
zin.close()
n_obj = files['Metadata/model_settings.config'].decode().count('<object id=')
xml = ['<?xml version="1.0" encoding="utf-8"?>', '<objects>']
for i in range(1, n_obj + 1):
    xml += [' <object id="{}">'.format(i),
            '  <range min_z="{}" max_z="1000">'.format(z0),
            '   <option opt_key="layer_height">{}</option>'.format(h),
            '  </range>', ' </object>']
files['Metadata/layer_config_ranges.xml'] = ('\n'.join(xml + ['</objects>']) + '\n').encode()
ps = json.loads(files['Metadata/project_settings.config'])
ps['wipe_tower_x'][0], ps['wipe_tower_y'][0] = tx, ty
files['Metadata/project_settings.config'] = json.dumps(ps, indent=4).encode()
with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
    for n, data in files.items():
        z.writestr(n, data)
print('{}: {} objects get {} mm layers from {} mm; prime tower at ({}, {})'.format(path, n_obj, h, z0, tx, ty))
