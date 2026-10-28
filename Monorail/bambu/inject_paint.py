"""Copy per-triangle paint from to_bambu.py's plate 3MF into the project Bambu
Studio wrote for that plate, matching triangles one for one and checking every
vertex, and give the project the settings of a project you already print with.

    python3 inject_paint.py <plate.3mf> <Bambu's project.3mf> <out.3mf> <colour,colour,...> <settings project.3mf>
"""
import sys, re, json, zipfile
import xml.etree.ElementTree as ET

mine, bambu, out, colours, borrowed = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(','), sys.argv[5]
C = '{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'

with zipfile.ZipFile(mine) as z:
    mroot = ET.fromstring(z.read('3D/3dmodel.model'))
my_objects = []
for o in mroot.iter(C + 'object'):
    verts = [(float(v.get('x')), float(v.get('y')), float(v.get('z'))) for v in o.iter(C + 'vertex')]
    tris = [(int(t.get('v1')), int(t.get('v2')), int(t.get('v3')), t.get('paint_color'))
            for t in o.iter(C + 'triangle')]
    my_objects.append((o.get('name'), verts, tris))

zin = zipfile.ZipFile(bambu)
files = {n: zin.read(n) for n in zin.namelist()}
settings = ET.fromstring(files['Metadata/model_settings.config'])
main = ET.fromstring(files['3D/3dmodel.model'])
P = '{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}'
part_path = {}
for o in main.iter(C + 'object'):
    for comp in o.iter(C + 'component'):
        part_path[comp.get('objectid')] = comp.get(P + 'path').lstrip('/')

report = []
for obj in settings.findall('object'):
    for part in obj.findall('part'):
        meta = {m.get('key'): m.get('value') for m in part.findall('metadata')}
        name, verts, tris = my_objects[int(meta['source_object_id'])]
        assert name == meta['name'], (name, meta['name'])
        off = [float(meta['source_offset_' + a]) for a in 'xyz']
        path = part_path[part.get('id')]
        text = files[path].decode()
        bverts = [tuple(float(x) for x in m) for m in
                  re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', text)]
        btris = re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"', text)
        assert len(bverts) == len(verts) and len(btris) == len(tris), \
            '{}: {} / {} vertices, {} / {} triangles'.format(name, len(bverts), len(verts), len(btris), len(tris))
        worst = max(abs(a - (b - o)) for bv, v in zip(bverts, verts) for a, b, o in zip(bv, v, off))
        assert worst < 1e-3, '{}: vertices off by {:.4f} mm'.format(name, worst)
        assert all(tuple(int(i) for i in bt) == t[:3] for bt, t in zip(btris, tris)), name + ': triangle order differs'
        # Rewrite EVERY triangle, whatever attributes Bambu already gave it --
        # it may have kept paint from the source file, and skipping those
        # triangles would shift every later one onto the wrong paint.
        it = iter(tris)
        def add(m):
            a, b, c, paint = next(it)
            assert (int(m.group(1)), int(m.group(2)), int(m.group(3))) == (a, b, c)
            return '<triangle v1="{}" v2="{}" v3="{}"{}/>'.format(
                a, b, c, ' paint_color="{}"'.format(paint) if paint else '')
        text, n = re.subn(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"[^>]*/>', add, text)
        assert n == len(tris), '{}: rewrote {} of {} triangles'.format(name, n, len(tris))
        files[path] = text.encode()
        painted = sum(1 for t in tris if t[3])
        report.append('  {:13s} {} triangles, {} painted, vertices within {:.5f} mm'.format(
            name, len(tris), painted, worst))

# Settings from a project you already print with: your printer, process and
# four AMS filaments. The settings the Bambu command line loads for itself come
# out as ONE filament, and with one filament Bambu silently drops paint 2-4.
ps = json.loads(zipfile.ZipFile(borrowed).read('Metadata/project_settings.config'))
have = len(ps.get('filament_settings_id', []))
assert have >= len(colours), '{} has {} filaments; the paint needs {}'.format(borrowed, have, len(colours))
ps['filament_colour'] = colours
# Nothing in the monorail needs support: the V in the belly, the beam's ridge
# and the spare pocket's finger notches all print at 40 degrees or steeper, and
# the pocket's roof is a bridge. Supports would only add scars and a filament.
ps['enable_support'] = '0'
files['Metadata/project_settings.config'] = json.dumps(ps, indent=4).encode()

with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    for n in zin.namelist():
        z.writestr(n, files[n])
print(out)
print('\n'.join(report))
