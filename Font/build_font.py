#!/usr/bin/env python3
"""Builds a Countdown font from its pen-line skeletons.

Every glyph is drawn in an SVG file as pen lines: each <path> is one stroke
of the brush and each <circle> a ball terminal, in font units with y up (the
SVG's flipping group shows them the right way up). This script strokes every
line with the broad-nib brush set in the config, merges the strokes into clean
outlines, spaces and kerns them, and writes a TrueType font -- the only kind
Fusion builds text from.

    python3 build_font.py [config.json] [--specimen]

font.json (the default) is Countdown Digits, for the cubes; lettering.json is
Countdown Lettering, for the words on the models. Each writes
build/<Family>-Regular.ttf, and --specimen adds sample sheets beside it.

Needs fonttools and pyclipper; the specimen also needs Pillow.
"""

import argparse
import json
import math
import os
import re
import xml.etree.ElementTree as ET

import pyclipper
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import newTable
from fontTools.ttLib.tables._k_e_r_n import KernTable_format_0

HERE = os.path.dirname(os.path.abspath(__file__))
SVG = '{http://www.w3.org/2000/svg}'
FLIP = 'matrix(1 0 0 -1 0 800)'   # the group that turns font units (y up) into SVG (y down)
CLIP_SCALE = 100.0                # pyclipper works in integers: hundredths of a unit
NUMBER = r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'


# ------------------------------------------------------------- geometry

def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def reflect(p, about):
    return (2.0 * about[0] - p[0], 2.0 * about[1] - p[1])


def line(a, b):
    return (a, lerp(a, b, 1.0 / 3.0), lerp(a, b, 2.0 / 3.0), b)


def quad(a, q, b):
    return (a, lerp(a, q, 2.0 / 3.0), lerp(b, q, 2.0 / 3.0), b)


def bezier(seg, t):
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = seg
    m = 1.0 - t
    a, b, c, d = m * m * m, 3.0 * m * m * t, 3.0 * m * t * t, t * t * t
    return (a * x0 + b * x1 + c * x2 + d * x3, a * y0 + b * y1 + c * y2 + d * y3)


def area(pts):
    return 0.5 * sum(pts[k][0] * pts[k - 1][1] - pts[k - 1][0] * pts[k][1]
                     for k in range(len(pts)))


def circle(c, r, n=72):
    return [(c[0] + r * math.cos(2.0 * math.pi * k / n),
             c[1] + r * math.sin(2.0 * math.pi * k / n)) for k in range(n)]


def rotate(pts, degrees, centre):
    a = math.radians(degrees)
    ca, sa = math.cos(a), math.sin(a)
    return [(centre[0] + (x - centre[0]) * ca - (y - centre[1]) * sa,
             centre[1] + (x - centre[0]) * sa + (y - centre[1]) * ca) for x, y in pts]


# ------------------------------------------------------------ reading SVG

def parse_path(d):
    """SVG path data -> [(cubic segments, closed)], one entry per subpath.
    Lines and quadratics come back as cubics; arcs are refused."""
    tokens = re.findall(r'[A-Za-z]|' + NUMBER, d)
    subpaths, segs = [], []
    cur = start = (0.0, 0.0)
    cmd, prev, ctrl = None, None, None
    i = 0

    def take():
        nonlocal i
        i += 1
        return float(tokens[i - 1])

    def end_subpath(closed):
        nonlocal segs
        if segs:
            subpaths.append((segs, closed))
        segs = []

    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
            if cmd in 'Zz':
                if math.dist(cur, start) > 1e-9:
                    segs.append(line(cur, start))
                cur = start
                end_subpath(True)
                prev = 'Z'
                continue
        if cmd is None:
            raise ValueError('path data starts with a number: ' + d[:40])
        c = cmd.upper()
        ox, oy = cur if cmd.islower() else (0.0, 0.0)
        if c == 'M':
            end_subpath(False)
            cur = start = (ox + take(), oy + take())
            cmd = 'l' if cmd == 'm' else 'L'      # further pairs after M are lines
        elif c == 'L':
            p = (ox + take(), oy + take())
            segs.append(line(cur, p))
            cur = p
        elif c == 'H':
            p = ((cur[0] if cmd == 'h' else 0.0) + take(), cur[1])
            segs.append(line(cur, p))
            cur = p
        elif c == 'V':
            p = (cur[0], (cur[1] if cmd == 'v' else 0.0) + take())
            segs.append(line(cur, p))
            cur = p
        elif c in 'CS':
            c1 = (ox + take(), oy + take()) if c == 'C' else (
                reflect(ctrl, cur) if prev in ('C', 'S') else cur)
            c2 = (ox + take(), oy + take())
            p = (ox + take(), oy + take())
            segs.append((cur, c1, c2, p))
            cur, ctrl = p, c2
        elif c in 'QT':
            q = (ox + take(), oy + take()) if c == 'Q' else (
                reflect(ctrl, cur) if prev in ('Q', 'T') else cur)
            p = (ox + take(), oy + take())
            segs.append(quad(cur, q, p))
            cur, ctrl = p, q
        else:
            raise ValueError('path command {!r} is not supported; convert arcs to curves'.format(cmd))
        prev = c
    end_subpath(False)
    return subpaths


def read_glyph(path):
    """The pen lines and ball terminals of one glyph SVG. Only what is inside
    the flipping group counts; guides outside it are ignored."""
    root = ET.parse(path).getroot()
    groups = [g for g in root.iter(SVG + 'g')
              if re.sub(r'[\s,]+', ' ', g.get('transform', '')).strip() == FLIP]
    if len(groups) != 1:
        raise ValueError('{}: expected one <g transform="{}"> holding the pen lines'
                         .format(os.path.basename(path), FLIP))
    strokes = [sp for p in groups[0].iter(SVG + 'path') for sp in parse_path(p.get('d', ''))]
    balls = [((float(c.get('cx', 0)), float(c.get('cy', 0))), float(c.get('r')))
             for c in groups[0].iter(SVG + 'circle')]
    return strokes, balls


def glyph_file(cfg, spec):
    if 'src' in spec:
        return os.path.join(HERE, spec['src'])
    return os.path.join(HERE, cfg.get('glyphDir', 'glyphs'), spec.get('file', spec['name']) + '.svg')


# -------------------------------------------------------------- the brush

def flatten(segs, step):
    pts = [segs[0][0]]
    for seg in segs:
        hull = sum(math.dist(seg[k], seg[k + 1]) for k in range(3))
        n = max(2, math.ceil(hull / step))
        pts += [bezier(seg, k / n) for k in range(1, n + 1)]
    out = [pts[0]]
    for p in pts[1:]:
        if math.dist(p, out[-1]) > 1e-6:
            out.append(p)
    return out


def stroke(segs, closed, brush):
    """Polygons covering one pen line drawn with the brush: thin triangles
    between neighbouring cross-sections, and round caps on open ends.

    The width comes from a broad nib held at nibAngle: thick moving across
    the nib, thin moving along it, so upright strokes come out heavy and
    flat ones light. Open lines also swell a little in the middle."""
    pts = flatten(segs, brush['step'])
    if closed and math.dist(pts[0], pts[-1]) < 1e-6:
        pts.pop()
    n = len(pts)
    run = [0.0]
    for k in range(1, n):
        run.append(run[-1] + math.dist(pts[k - 1], pts[k]))
    total = run[-1] or 1.0
    nib = math.radians(brush['nibAngle'])
    left, right, widths = [], [], []
    for k in range(n):
        a = pts[(k - 1) % n] if closed or k > 0 else pts[k]
        b = pts[(k + 1) % n] if closed or k < n - 1 else pts[k]
        theta = math.atan2(b[1] - a[1], b[0] - a[0])
        w = brush['thin'] + (brush['thick'] - brush['thin']) * abs(math.sin(theta - nib))
        if not closed:
            w *= 1.0 + brush['swell'] * math.sin(math.pi * run[k] / total)
        nx, ny = -math.sin(theta), math.cos(theta)
        left.append((pts[k][0] + nx * w / 2.0, pts[k][1] + ny * w / 2.0))
        right.append((pts[k][0] - nx * w / 2.0, pts[k][1] - ny * w / 2.0))
        widths.append(w)
    polys = []
    for k in range(n if closed else n - 1):
        j = (k + 1) % n
        polys.append([left[k], left[j], right[j]])
        polys.append([left[k], right[j], right[k]])
    if not closed:
        polys.append(circle(pts[0], widths[0] / 2.0))
        polys.append(circle(pts[-1], widths[-1] / 2.0))
    return polys


def union(polys):
    """One clean outline from overlapping polygons. Each is turned the same
    way first, so overlaps add up instead of cancelling. The contours come
    back turned the TrueType way: outlines clockwise, holes anticlockwise."""
    pc = pyclipper.Pyclipper()
    for poly in polys:
        pts = [(round(x * CLIP_SCALE), round(y * CLIP_SCALE)) for x, y in poly]
        if area(pts) < 0:
            pts.reverse()
        if abs(area(pts)) > 1.0:
            pc.AddPath(pts, pyclipper.PT_SUBJECT, True)
    tree = pc.Execute2(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)
    contours, todo = [], list(tree.Childs)
    while todo:
        node = todo.pop()
        todo += node.Childs
        pts = [(x / CLIP_SCALE, y / CLIP_SCALE) for x, y in node.Contour]
        if (area(pts) > 0) != node.IsHole:
            pts.reverse()
        contours.append(pts)
    return contours


def simplify(contour, tol):
    """Drops points that sit within tol of the line through their neighbours
    (Douglas-Peucker), splitting the loop at its two farthest points."""
    def dist_to_segment(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        if dx == dy == 0:
            return math.dist(p, a)
        t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
        return math.dist(p, (a[0] + t * dx, a[1] + t * dy))

    def chain(pts):
        keep = [False] * len(pts)
        keep[0] = keep[-1] = True
        todo = [(0, len(pts) - 1)]
        while todo:
            i, j = todo.pop()
            best, at = 0.0, None
            for k in range(i + 1, j):
                d = dist_to_segment(pts[k], pts[i], pts[j])
                if d > best:
                    best, at = d, k
            if at is not None and best > tol:
                keep[at] = True
                todo += [(i, at), (at, j)]
        return [p for p, k in zip(pts, keep) if k]

    if len(contour) < 4:
        return contour
    far = max(range(len(contour)), key=lambda k: math.dist(contour[0], contour[k]))
    return chain(contour[:far + 1])[:-1] + chain(contour[far:] + [contour[0]])[:-1]


# ------------------------------------------------------------- the glyphs

def glyph_outline(strokes, balls, brush, tol):
    polys = []
    for segs, closed in strokes:
        polys += stroke(segs, closed, brush)
    polys += [circle(c, r) for c, r in balls]
    return [simplify(c, tol) for c in union(polys)]


def bounds(contours):
    xs = [p[0] for c in contours for p in c]
    ys = [p[1] for c in contours for p in c]
    return min(xs), min(ys), max(xs), max(ys)


def build_outlines(cfg):
    """Every glyph's contours, tilted and finished, keyed by character.

    A font with a defaultAdvance is tabular, like the digits: each glyph is
    drawn in place on its advance and tilts about the advance's middle.
    Otherwise each glyph tilts about the middle of its own ink and is spaced
    afterwards."""
    brush, tol, h = cfg['brush'], cfg['simplify'], cfg['figureHeight']
    outlines = {}
    for ch, spec in cfg['glyphs'].items():
        if 'rotate180Of' in spec:
            continue
        strokes, balls = read_glyph(glyph_file(cfg, spec))
        contours = glyph_outline(strokes, balls, brush, tol)
        if 'defaultAdvance' in cfg:
            cx = spec.get('advance', cfg['defaultAdvance']) / 2.0
        else:
            x0, _, x1, _ = bounds(contours)
            cx = (x0 + x1) / 2.0
        outlines[ch] = [rotate(c, spec.get('tilt', 0.0), (cx, h / 2.0)) for c in contours]
    for ch, spec in cfg['glyphs'].items():
        if 'rotate180Of' in spec:
            src = spec['rotate180Of']
            if 'defaultAdvance' in cfg:
                cx = cfg['glyphs'][src].get('advance', cfg['defaultAdvance']) / 2.0
            else:
                x0, _, x1, _ = bounds(outlines[src])
                cx = (x0 + x1) / 2.0
            outlines[ch] = [rotate(c, 180.0, (cx, h / 2.0)) for c in outlines[src]]
    return outlines


# --------------------------------------------------------------- spacing

def profile(contours, ys):
    """The leftmost and rightmost ink at each height (None where there is none)."""
    left, right = [], []
    for y in ys:
        xs = []
        for c in contours:
            for k in range(len(c)):
                (xa, ya), (xb, yb) = c[k - 1], c[k]
                if (ya <= y < yb) or (yb <= y < ya):
                    xs.append(xa + (y - ya) * (xb - xa) / (yb - ya))
        left.append(min(xs) if xs else None)
        right.append(max(xs) if xs else None)
    return left, right


def solve_side(dists, target, depth):
    """The sidebearing that puts the average white beside the glyph, over its
    zone, at target units. White deeper than depth counts only as depth, so a
    wide-open side (an L, a T) is not pushed far out."""
    def mean_white(s):
        return sum(min(s + d, depth) if d is not None else depth for d in dists) / len(dists)
    lo, hi = -depth, target
    for _ in range(50):
        mid = (lo + hi) / 2.0
        if mean_white(mid) > target:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2.0


def space_glyphs(cfg, outlines):
    """Advance and left sidebearing for every glyph, shifting its outline so
    the ink starts at the sidebearing. Returns {char: advance}."""
    sp = cfg['spacing']
    zones = {'cap': (0, cfg['figureHeight']), 'x': (0, cfg['xHeight'])}
    advances = {}
    for ch, spec in cfg['glyphs'].items():
        contours = outlines[ch]
        x0, y0, x1, y1 = bounds(contours)
        if 'sides' in spec:
            lsb, rsb = spec['sides']
        else:
            z0, z1 = zones[spec.get('zone', 'cap')]
            ys = [z0 + (z1 - z0) * (k + 0.5) / 60 for k in range(60)]
            left, right = profile(contours, ys)
            lsb = solve_side([None if l is None else l - x0 for l in left], sp['target'], sp['depth'])
            rsb = solve_side([None if r is None else x1 - r for r in right], sp['target'], sp['depth'])
        lsb += spec.get('lsbAdjust', 0)
        rsb += spec.get('rsbAdjust', 0)
        # Never closer to the edge than half the gap the printer can keep
        # open, so no two neighbours can touch even where kerning is ignored.
        lsb, rsb = max(lsb, sp.get('minSide', 0)), max(rsb, sp.get('minSide', 0))
        dx = lsb - x0
        outlines[ch] = [[(x + dx, y) for x, y in c] for c in contours]
        advances[ch] = int(round(lsb + (x1 - x0) + rsb))
    return advances


def kern_pairs(cfg, outlines, advances):
    """Kerning that tightens pairs with a lot of white between them (an A
    beside a V, a T over an o), and the pairs that end up closer than the
    printer can keep apart. Returns ({(left, right): value}, [too-close pairs])."""
    import numpy as np
    kc = cfg['kerning']
    gap, strength, ceiling = kc['minGap'], kc['strength'], kc['maxKern']
    step = 8.0
    lo, hi = cfg['descender'], cfg['ascender']
    ys = np.arange(lo, hi, step)
    prof = {}
    for ch in outlines:
        left, right = profile(outlines[ch], list(ys))
        prof[ch] = (np.array([np.nan if v is None else v for v in left]),
                    np.array([np.nan if v is None else v for v in right]))
    zones = {'cap': cfg['figureHeight'], 'x': cfg['xHeight']}
    chars = [ch for ch in cfg['glyphs'] if 'sides' not in cfg['glyphs'][ch] or kc.get('punctuation', True)]
    dy = ys[:, None] - ys[None, :]
    clear = np.where(np.abs(dy) < gap, np.sqrt(np.maximum(gap * gap - dy * dy, 0.0)), np.nan)
    kerns, close = {}, []
    for a in chars:
        ra = prof[a][1]
        for b in chars:
            lb = prof[b][0]
            # Smallest kern that keeps every point of b at least gap from a.
            need = ra[:, None] - lb[None, :] + clear - advances[a]
            k_min = np.nanmax(need) if np.isfinite(need).any() else -1e9
            # The average white across the shorter of the two zones.
            top = min(zones.get(cfg['glyphs'][a].get('zone', 'cap'), cfg['figureHeight']),
                      zones.get(cfg['glyphs'][b].get('zone', 'cap'), cfg['figureHeight']))
            band = (ys >= 0) & (ys <= top)
            white = advances[a] - ra[band] + lb[band]
            white = white[np.isfinite(white)]
            k = 0.0
            if white.size and 'sides' not in cfg['glyphs'][a] and 'sides' not in cfg['glyphs'][b]:
                excess = np.mean(np.minimum(white, 2 * cfg['spacing']['depth'])) - 2 * cfg['spacing']['target']
                k = -min(ceiling, max(0.0, strength * excess))
            if k < k_min:
                k = k_min
            if k_min > 0.5:
                close.append((a, b, int(round(k_min))))
            if abs(k) >= kc.get('threshold', 10):
                kerns[(a, b)] = int(round(k))
    return kerns, close


# --------------------------------------------------------------- the font

def font_points(contour):
    """Integer points, with repeats dropped."""
    pts = []
    for x, y in contour:
        p = (int(round(x)), int(round(y)))
        if not pts or p != pts[-1]:
            pts.append(p)
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts.pop()
    return pts


def build_font(cfg, outlines, advances, kerns, path):
    upm, asc, desc = cfg['unitsPerEm'], cfg['ascender'], cfg['descender']
    names = {ch: spec['name'] for ch, spec in cfg['glyphs'].items()}
    fb = FontBuilder(upm, isTTF=True)
    fb.setupGlyphOrder(['.notdef', 'space'] + list(names.values()))
    cmap = {0x20: 'space'}
    for ch, nm in names.items():
        cmap[ord(ch)] = nm
        for extra in cfg['glyphs'][ch].get('also', []):
            cmap[ord(extra)] = nm
    fb.setupCharacterMap(cmap)

    glyphs, metrics = {}, {}
    pen = TTGlyphPen(None)                      # .notdef: a hollow box
    for box in (((50, 0), (50, 700), (450, 700), (450, 0)),
                ((100, 50), (400, 50), (400, 650), (100, 650))):
        pen.moveTo(box[0])
        for p in box[1:]:
            pen.lineTo(p)
        pen.closePath()
    glyphs['.notdef'], metrics['.notdef'] = pen.glyph(), (500, 50)
    glyphs['space'], metrics['space'] = TTGlyphPen(None).glyph(), (cfg['spaceWidth'], 0)

    for ch, nm in names.items():
        pen = TTGlyphPen(None)
        contours = [font_points(c) for c in outlines[ch]]
        for c in contours:
            pen.moveTo(c[0])
            for p in c[1:]:
                pen.lineTo(p)
            pen.closePath()
        glyphs[nm] = pen.glyph()
        metrics[nm] = (advances[ch], min(p[0] for c in contours for p in c))

    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=asc, descent=desc)
    family, style = cfg['familyName'], cfg['styleName']
    name = {'familyName': family, 'styleName': style,
            'uniqueFontIdentifier': '{} {} {}'.format(family, style, cfg['version']),
            'fullName': '{} {}'.format(family, style),
            'psName': '{}-{}'.format(family.replace(' ', ''), style.replace(' ', '')),
            'version': 'Version {}'.format(cfg['version'])}
    if cfg.get('copyright'):
        name['copyright'] = cfg['copyright']
    fb.setupNameTable(name)
    fb.setupOS2(sTypoAscender=asc, sTypoDescender=desc, sTypoLineGap=0,
                usWinAscent=asc, usWinDescent=-desc,
                sCapHeight=cfg['figureHeight'], sxHeight=cfg.get('xHeight', cfg['figureHeight']),
                achVendID='NONE', fsType=0)
    fb.setupPost()
    if kerns:
        fea = 'feature kern {\n' + ''.join(
            '    pos {} {} {};\n'.format(names[a], names[b], v) for (a, b), v in sorted(kerns.items())) + '} kern;\n'
        fb.addOpenTypeFeatures(fea)
        # The old 'kern' table as well, for software that ignores GPOS.
        table = KernTable_format_0()
        table.version, table.coverage, table.format = 0, 1, 0
        table.kernTable = {(names[a], names[b]): v for (a, b), v in kerns.items()}
        kern = newTable('kern')
        kern.version, kern.kernTables = 0, [table]
        fb.font['kern'] = kern
    fb.save(path)


# --------------------------------------------------------------- specimen

def draw_outline(d, contours, to_px, fill):
    for c in sorted(contours, key=lambda c: -abs(area(c))):
        d.polygon([to_px(p) for p in c], fill=fill if area(c) < 0 else 'white')


def specimen_cubes(cfg, ttf, outlines, out_dir):
    """The digits as text and on mock cube faces."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new('RGB', (1600, 960), 'white')
    d = ImageDraw.Draw(img)
    big = ImageFont.truetype(ttf, 200)
    d.text((60, 40), '0123456789', font=big, fill='black')
    # Cube faces: the digit's ink 55% of the face, as on the printed cubes.
    face, gap = 150, 12
    ink = max(bounds(o)[3] - bounds(o)[1] for o in outlines.values())
    cube_font = ImageFont.truetype(ttf, round(0.55 * face * cfg['unitsPerEm'] / ink))
    for row, counts in enumerate((('027', '100', '365'), ('069', '248', '613'))):
        for col, count in enumerate(counts):
            x0 = 60 + col * (3 * face + 2 * gap + 70)
            y0 = 360 + row * (face + 80)
            for k, ch in enumerate(count):
                fx = x0 + k * (face + gap)
                d.rounded_rectangle((fx, y0, fx + face, y0 + face), 14,
                                    fill='#f4f2ec', outline='#b9b5aa', width=3)
                l, t, r, b = d.textbbox((0, 0), ch, font=cube_font)
                d.text((fx + (face - (r - l)) / 2 - l, y0 + (face - (b - t)) / 2 - t),
                       ch, font=cube_font, fill='#151515')
    img.save(os.path.join(out_dir, 'specimen.png'))


def specimen_words(cfg, ttf, outlines, out_dir, stem):
    """The alphabet, and each model's wording on a band of its colours, sized
    to the band as the model scripts size it."""
    from PIL import Image, ImageDraw, ImageFont

    rows = cfg['specimen']['alphabet']
    img = Image.new('RGB', (1800, 140 * len(rows) + 60), 'white')
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(ttf, 110)
    for k, row in enumerate(rows):
        d.text((40, 30 + 140 * k), row, font=font, fill='black')
    img.save(os.path.join(out_dir, stem + '-alphabet.png'))

    bands = cfg['specimen']['bands']
    px_mm = 14.0
    width = int(max(b['run'] for b in bands) * px_mm) + 120
    img = Image.new('RGB', (width, sum(int(b['height'] * px_mm) + 70 for b in bands) + 40), 'white')
    d = ImageDraw.Draw(img)
    y = 30
    for band in bands:
        h = int(band['height'] * px_mm)
        d.text((60, y), band['label'], fill='#666666')
        y += 22
        d.rectangle((60, y, 60 + int(band['run'] * px_mm), y + h), fill=band['ground'])
        # One em that fits every phrase on the band, as the scripts do.
        probe = ImageFont.truetype(ttf, 1000)
        em = min(min(band['run'] / ((r - l) / 1000.0), band['height'] / ((b - t) / 1000.0))
                 for r, l, b, t in ((bb[2], bb[0], bb[3], bb[1]) for bb in
                                    (d.textbbox((0, 0), p, font=probe) for p in band['phrases'])))
        f = ImageFont.truetype(ttf, max(1, round(em * px_mm)))
        phrase = band['phrases'][0]
        l, t, r, b = d.textbbox((0, 0), phrase, font=f)
        d.text((60 + (band['run'] * px_mm - (r - l)) / 2 - l, y + (h - (b - t)) / 2 - t),
               phrase, font=f, fill=band['ink'])
        y += h + 48
    img.save(os.path.join(out_dir, stem + '-words.png'))


def skeleton_sheet(cfg, outlines, out_dir, stem):
    """Each glyph's outline with its pen lines over it."""
    from PIL import Image, ImageDraw

    s, cols = 0.24, 13
    cell_w, cell_h = 170, int((cfg['ascender'] - cfg['descender']) * s) + 30
    chars = list(cfg['glyphs'])
    rows = (len(chars) + cols - 1) // cols
    sk = Image.new('RGB', (cols * cell_w, rows * cell_h), 'white')
    d = ImageDraw.Draw(sk)
    for k, ch in enumerate(chars):
        spec = cfg['glyphs'][ch]
        x0, _, x1, _ = bounds(outlines[ch])
        ox = (k % cols) * cell_w + (cell_w - (x1 - x0) * s) / 2 - x0 * s
        oy = (k // cols) * cell_h + 10
        to_px = lambda p, ox=ox, oy=oy: (ox + p[0] * s, oy + (cfg['ascender'] - p[1]) * s)
        for yy in (0, cfg['figureHeight'], cfg.get('xHeight', cfg['figureHeight'])):
            d.line([to_px((x0 - 40, yy)), to_px((x1 + 40, yy))], fill='#dddddd', width=1)
        draw_outline(d, outlines[ch], to_px, '#d0d0d0')
        if 'rotate180Of' in spec:
            continue
        strokes, balls = read_glyph(glyph_file(cfg, spec))
        # The pen lines, moved and tilted the way the outline was.
        raw = glyph_outline(strokes, balls, cfg['brush'], cfg['simplify'])
        rx0, _, rx1, _ = bounds(raw)
        if 'defaultAdvance' in cfg:
            cx, shift = spec.get('advance', cfg['defaultAdvance']) / 2.0, 0.0
        else:
            cx = (rx0 + rx1) / 2.0
            tilted = [rotate(c, spec.get('tilt', 0.0), (cx, cfg['figureHeight'] / 2.0)) for c in raw]
            shift = x0 - bounds(tilted)[0]
        place = lambda pts: [(x + shift, y) for x, y in rotate(pts, spec.get('tilt', 0.0),
                                                                (cx, cfg['figureHeight'] / 2.0))]
        for segs, closed in strokes:
            d.line([to_px(p) for p in place(flatten(segs, 4))], fill='#c0392b', width=2)
        for c, r in balls:
            (x, y), = place([c])
            x, y = to_px((x, y))
            d.ellipse((x - r * s, y - r * s, x + r * s, y + r * s), outline='#c0392b', width=2)
    sk.save(os.path.join(out_dir, stem + '-skeletons.png'))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('config', nargs='?', default='font.json', help='font.json or lettering.json')
    ap.add_argument('--specimen', action='store_true', help='also draw the sample sheets')
    args = ap.parse_args()
    with open(os.path.join(HERE, args.config)) as f:
        cfg = json.load(f)
    out_dir = os.path.join(HERE, 'build')
    os.makedirs(out_dir, exist_ok=True)
    outlines = build_outlines(cfg)
    if 'defaultAdvance' in cfg:
        cfg.setdefault('spaceWidth', cfg['defaultAdvance'] // 2)
        advances = {ch: spec.get('advance', cfg['defaultAdvance']) for ch, spec in cfg['glyphs'].items()}
        kerns, close = {}, []
    else:
        advances = space_glyphs(cfg, outlines)
        kerns, close = kern_pairs(cfg, outlines, advances)
    stem = '{}-{}'.format(cfg['familyName'].replace(' ', ''), cfg['styleName'].replace(' ', ''))
    ttf = os.path.join(out_dir, stem + '.ttf')
    build_font(cfg, outlines, advances, kerns, ttf)
    points = sum(len(c) for o in outlines.values() for c in o)
    print('Wrote {} ({} glyphs, {} outline points, {} kerning pairs).'
          .format(ttf, len(outlines), points, len(kerns)))
    if close:
        print('{} pairs had to be pushed apart to stay printable without kerning: {}'
              .format(len(close), ', '.join('{}{} +{}'.format(a, b, k) for a, b, k in close[:40])))
    if args.specimen:
        if 'specimen' in cfg:
            specimen_words(cfg, ttf, outlines, out_dir, stem)
            print('Wrote build/{0}-alphabet.png and build/{0}-words.png.'.format(stem))
        else:
            specimen_cubes(cfg, ttf, outlines, out_dir)
            print('Wrote build/specimen.png.')
        skeleton_sheet(cfg, outlines, out_dir, stem)
        print('Wrote build/{}-skeletons.png.'.format(stem))


if __name__ == '__main__':
    main()
