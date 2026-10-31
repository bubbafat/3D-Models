"""Fusion 3MF (per-triangle colours) -> Bambu Studio 3MFs, painted and laid out.

Bambu keeps colour painting per triangle in a `paint_color` attribute: the
TriangleSelector bitstream for an unsplit triangle in state s, as hex --
s=1 "4", s=2 "8", s>=3 "{s-3:X}C". State s means filament s; unpainted
triangles take the object's own filament (1).
"""
import sys, os, math, zipfile, collections
import xml.etree.ElementTree as ET

src, outdir = sys.argv[1], sys.argv[2]
NS = {'c': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02',
      'm': 'http://schemas.microsoft.com/3dmanufacturing/material/2015/02'}

FILAMENT = {'#EEEEE8': 1, '#1C1C20': 2, '#30343A': 2, '#BE1C22': 3, '#EEB228': 4,
            '#96989E': 5, '#A0A0A0': 5}      # grey is filament 5: see filaments.py

def paint_code(s):
    return {1: '4', 2: '8'}.get(s) or '{:X}C'.format(s - 3)

# Print orientation, as a function on (x, y, z).
FLAT_ON_MINUS_Y = lambda x, y, z: (x, -z, y)    # +90 about x: the -y face goes down
FLAT_ON_PLUS_Y = lambda x, y, z: (x, z, -y)     # -90 about x: the +y face goes down
AS_IS = lambda x, y, z: (x, y, z)
ORIENT = {'Car_Bottom': AS_IS, 'Car_Pinstripe': AS_IS, 'Car_Band': AS_IS, 'Car_Roof': AS_IS,
          'Car_Red_Display': FLAT_ON_MINUS_Y, 'Car_Red_Back': FLAT_ON_PLUS_Y,
          # each frame is a cup, open to +y: on its back, open side up
          'Car_Frame_1': FLAT_ON_MINUS_Y, 'Car_Frame_2': FLAT_ON_MINUS_Y,
          'Car_Frame_3': FLAT_ON_MINUS_Y,
          'Beam': FLAT_ON_MINUS_Y, 'Foot': AS_IS,
          'Cube_1': AS_IS, 'Cube_2': AS_IS, 'Cube_3': AS_IS, 'Cube_4_Spare': AS_IS}
# The pins stand on end: the ones between the red halves lie across y in the
# model, the rest stand up already.
PIN_ORIENT = {'Pin_Red_': FLAT_ON_MINUS_Y}


def orient(name):
    if name.startswith('Pin_'):
        return next((f for k, f in PIN_ORIENT.items() if name.startswith(k)), AS_IS)
    return ORIENT[name]


# Plates: (file name, [(body, front-left corner x, y on a 256 mm bed)]). The car
# goes by colour: the white bottom with all the pins, the red halves, the top's
# white pinstripe and roof, and its black band and frames. 'Pin_*' is every
# pin, in a row from there.
PLATES = [
    ('Monorail - car bottom.3mf', [('Car_Bottom', 40, 60), ('Pin_*', 30, 140)]),
    ('Monorail - car red.3mf', [('Car_Red_Display', 40, 60), ('Car_Red_Back', 40, 110)]),
    ('Monorail - car top white.3mf', [('Car_Pinstripe', 40, 50), ('Car_Roof', 40, 130)]),
    ('Monorail - car top black.3mf', [('Car_Band', 40, 50), ('Car_Frame_1', 60, 130),
                                      ('Car_Frame_2', 100, 130), ('Car_Frame_3', 140, 130)]),
    ('Monorail - beam plate.3mf', [('Beam', 44, 30), ('Foot', 63, 90)]),
    ('Monorail - cubes.3mf', [('Cube_1', 70, 100), ('Cube_2', 100, 100),
                              ('Cube_3', 130, 100), ('Cube_4_Spare', 160, 100)]),
]


def letter_sides(name, o, tris, counts):
    """Paint the letters' SIDES gold. Fusion paints only their tops (painting
    thousands of glyph-side faces there is far too slow), but the halves print
    lying on the split face, so a letter's height is all side wall.

    Self-calibrating from the mesh, in model coordinates (before turning the
    part for printing): the letters are where the gold tops are; their sides
    are the near-vertical triangles between the red stripe floor and those
    tops, inside the tops' own x/z extent. The stripe's edge walls sit on its
    top and bottom edges, outside that extent."""
    raw = [(float(v.get('x')), float(v.get('y')), float(v.get('z'))) for v in o.iter('{%s}vertex' % NS['c'])]
    def centre(t):
        return [sum(raw[t[k]][i] for k in range(3)) / 3.0 for i in range(3)]
    gold = [centre(t) for t in tris if t[3] == 4]
    red = [round(abs(centre(t)[1]), 2) for t in tris if t[3] == 3]
    if not gold or not red:
        return
    top = max(abs(c[1]) for c in gold)
    floor = collections.Counter(red).most_common(1)[0][0]
    x0, x1 = min(c[0] for c in gold) - 0.5, max(c[0] for c in gold) + 0.5
    z0, z1 = min(c[2] for c in gold) - 0.5, max(c[2] for c in gold) + 0.5
    n = 0
    for i, t in enumerate(tris):
        if t[3] == 4:
            continue
        x, y, z = centre(t)
        a, b, c = raw[t[0]], raw[t[1]], raw[t[2]]
        u = [b[k] - a[k] for k in range(3)]; v = [c[k] - a[k] for k in range(3)]
        ny = abs(u[2] * v[0] - u[0] * v[2])
        nl = sum(w * w for w in (u[1] * v[2] - u[2] * v[1], ny, u[0] * v[1] - u[1] * v[0])) ** 0.5
        vertical = nl > 0 and ny / nl < 0.2
        if vertical and floor + 0.02 < abs(y) < top - 0.02 and x0 < x < x1 and z0 < z < z1:
            counts[t[3]] -= 1
            tris[i] = t[:3] + (4,)
            counts[4] += 1
            n += 1
    print('  {}: letter sides painted gold on {} triangles (stripe floor {:.2f}, letter tops {:.2f})'.format(
        name, n, floor, top))

with zipfile.ZipFile(src) as z:
    root = ET.fromstring(z.read('3D/3dmodel.model'))
groups = {}
for g in root.iter('{%s}colorgroup' % NS['m']):
    groups[g.get('id')] = [c.get('color')[:7].upper() for c in g.findall('m:color', NS)]

# Supports are painted on too, per triangle (Bambu's paint_supports, the same
# code with 1 an enforcer), and the projects support only what is painted.
# Left to itself Bambu also filled the beam channel and the cube slots, bridges
# that print fine and that support would be hard to clear out of. In model mm,
# from Monorail Countdown.py:
#   Car_Bottom  the nose's underside, which lifts off the bed as it curves up
#               to the tip -- but not the beam channel down the middle
#   Car_Red_*   the tail end over the spare pocket, which overhangs the cut
#               face the half prints on
NOSE_FROM, CHANNEL_HALF = 37.0, 5.6
POCKET_TO, POCKET_HALF = -64.0, 11.5
FLATTER_THAN = 50.0             # degrees from the bed, facing down


def wants_support(name, x, y, z):
    if name == 'Car_Bottom':
        return x > NOSE_FROM and abs(y) > CHANNEL_HALF
    if name.startswith('Car_Red_'):
        return x < POCKET_TO and abs(y) < POCKET_HALF
    return False


def supported(name, raw, verts, tris):
    """Indices of the triangles to support: facing down in print, flatter than
    FLATTER_THAN, where wants_support says."""
    out = set()
    for i, (a, b, c, _) in enumerate(tris):
        p, q, r = verts[a], verts[b], verts[c]
        u = [q[k] - p[k] for k in range(3)]
        v = [r[k] - p[k] for k in range(3)]
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        length = sum(w * w for w in n) ** 0.5
        if length == 0 or -n[2] / length < math.cos(math.radians(FLATTER_THAN)):
            continue
        if wants_support(name, *[sum(raw[j][k] for j in (a, b, c)) / 3.0 for k in range(3)]):
            out.add(i)
    return out


objects = {}
for o in root.iter('{%s}object' % NS['c']):
    name = o.get('name')
    cols = groups[o.get('pid')]
    default = cols[int(o.get('pindex'))]
    f = orient(name)
    raw = [(float(v.get('x')), float(v.get('y')), float(v.get('z')))
           for v in o.iter('{%s}vertex' % NS['c'])]
    verts = [f(*p) for p in raw]
    tris, counts, unknown = [], collections.Counter(), collections.Counter()
    for t in o.iter('{%s}triangle' % NS['c']):
        hexc = cols[int(t.get('p1'))] if t.get('p1') is not None else default
        if hexc not in FILAMENT:
            unknown[hexc] += 1
        fil = FILAMENT.get(hexc, 1)
        counts[fil] += 1
        tris.append((int(t.get('v1')), int(t.get('v2')), int(t.get('v3')), fil))
    if name.startswith('Car_'):
        letter_sides(name, o, tris, counts)
    objects[name] = (verts, tris, counts, unknown, supported(name, raw, verts, tris))

os.makedirs(outdir, exist_ok=True)
CT = ('<?xml version="1.0" encoding="UTF-8"?>\n'
      '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
      '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
      '</Types>')
RELS = ('<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Target="/3D/3dmodel.model" Id="rel-1" '
        'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')

pins = sorted(n for n in objects if n.startswith('Pin_'))
for fname, parts in PLATES:
    parts = [p for name, x, y in parts for p in (
        [(pin, x + 10 * i, y) for i, pin in enumerate(pins)] if name == 'Pin_*' else [(name, x, y)])]
    out = ['<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
           'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">\n<resources>\n']
    build = []
    report = []
    for oid, (name, px, py) in enumerate(parts, start=1):
        verts, tris, counts, unknown, support = objects[name]
        lo = [min(v[i] for v in verts) for i in range(3)]
        hi = [max(v[i] for v in verts) for i in range(3)]
        dx, dy, dz = px - lo[0], py - lo[1], -lo[2]
        out.append('<object id="{}" name="{}" type="model"><mesh><vertices>\n'.format(oid, name))
        out.extend('<vertex x="{:.5f}" y="{:.5f}" z="{:.5f}"/>\n'.format(x + dx, y + dy, z + dz)
                   for x, y, z in verts)
        out.append('</vertices><triangles>\n')
        for i, (a, b, c, fil) in enumerate(tris):
            paint = '' if fil == 1 else ' paint_color="{}"'.format(paint_code(fil))
            if i in support:
                paint += ' paint_supports="{}"'.format(paint_code(1))
            out.append('<triangle v1="{}" v2="{}" v3="{}"{}/>\n'.format(a, b, c, paint))
        out.append('</triangles></mesh></object>\n')
        build.append('<item objectid="{}"/>'.format(oid))
        report.append('  {:13s} {:6.1f} x {:5.1f} x {:5.1f} mm, at ({:.0f}, {:.0f})  '
                      'triangles by filament {}{}{}'.format(
                          name, hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], px, py,
                          dict(sorted(counts.items())),
                          ', {} to support'.format(len(support)) if support else '',
                          '  UNMAPPED {}'.format(dict(unknown)) if unknown else ''))
        assert px + hi[0] - lo[0] <= 246 and py + hi[1] - lo[1] <= 246, name + ' runs off the bed'
    out.append('</resources>\n<build>' + ''.join(build) + '</build>\n</model>\n')
    path = os.path.join(outdir, fname)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', CT)
        z.writestr('_rels/.rels', RELS)
        z.writestr('3D/3dmodel.model', ''.join(out))
    print(fname, '{:.0f} kB'.format(os.path.getsize(path) / 1024))
    print('\n'.join(report))
