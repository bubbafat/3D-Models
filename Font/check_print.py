#!/usr/bin/env python3
"""How well a font will print at the size a model uses it.

Draws each glyph, and each whole phrase, at its real size, 0.01 mm to the
pixel, and finds the parts a 0.4 mm nozzle can't make cleanly. Strokes
narrower than two printed lines (0.84 mm) print ragged, and narrower than one
line (0.42 mm) don't print. White gaps narrower than that fill in -- inside a
letter, or between two letters of a phrase.

    python3 check_print.py                      the digits in build/, cube size
    python3 check_print.py --compare <ttf>      and another font, sized the same way
    python3 check_print.py build/CountdownLettering-Regular.ttf \\
        --chars "DAYS'TILVCONG!" --text "DAYS 'TIL VACATION" \\
        --text "VACATION IS CALLING!" --fit 88 9

Text is sized by its ink, as the model scripts size it. --ink (11 mm unless
given) makes all ten digits together that tall, which is how the cube scripts
calibrate. --fit takes the largest size at which every --text phrase fits
RUN x HEIGHT mm, as they fit their lettering. --em sets the em directly; it is
the font's own em, not the text height a Fusion report prints, which is a
different measure.

It writes build/printability.png: black is ink, red is stroke thinner than
two lines (darker red, thinner than one), and blue is a white gap narrower
than two lines (darker blue, narrower than one).

Needs numpy, scipy and Pillow.
"""

import argparse
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import distance_transform_edt as edt

HERE = os.path.dirname(os.path.abspath(__file__))
MM_PER_PX = 0.01
LINE = 0.42                       # one Bambu line on a 0.4 mm nozzle
DIGITS = '0123456789'


def render(ttf, em_mm, text):
    font = ImageFont.truetype(ttf, round(em_mm / MM_PER_PX))
    l, t, r, b = font.getbbox(text)
    pad = 100
    img = Image.new('L', (r - l + 2 * pad, b - t + 2 * pad), 0)
    ImageDraw.Draw(img).text((pad - l, pad - t), text, font=font, fill=255)
    return np.array(img) >= 128


def ink_size(ttf, em_mm, text):
    """Width and height of the ink, in mm."""
    ink = render(ttf, em_mm, text)
    rows, cols = np.where(ink)
    return ((cols.max() - cols.min() + 1) * MM_PER_PX, (rows.max() - rows.min() + 1) * MM_PER_PX)


def ink_em(ttf, height):
    """The em at which all ten digits together stand height mm tall."""
    probe = 10.0
    return probe * height / ink_size(ttf, probe, DIGITS)[1]


def fit_em(ttf, phrases, run, height):
    probe = 10.0
    sizes = [ink_size(ttf, probe, p) for p in phrases]
    return min(min(run / w, height / h) for w, h in sizes) * probe


def opened(mask, width_mm):
    """What is left of mask after rolling a disc width_mm across it: the
    parts at least that wide."""
    r = width_mm / 2.0 / MM_PER_PX
    core = edt(mask) > r
    if not core.any():
        return np.zeros_like(mask)
    return edt(~core) <= r


def measure(ttf, em_mm, texts):
    rows, pictures = [], []
    px_area = MM_PER_PX * MM_PER_PX
    for text in texts:
        ink = render(ttf, em_mm, text)
        thin1 = ink & ~opened(ink, LINE)
        thin2 = ink & ~opened(ink, 2 * LINE)
        gap1 = ~ink & ~opened(~ink, LINE)
        gap2 = ~ink & ~opened(~ink, 2 * LINE)
        rows.append((text, ink.sum() * px_area, thin2.sum() * px_area, thin1.sum() * px_area,
                     gap2.sum() * px_area, gap1.sum() * px_area))
        pic = np.full(ink.shape + (3,), 255, np.uint8)
        pic[ink] = (20, 20, 20)
        pic[thin2] = (235, 90, 80)
        pic[thin1] = (150, 0, 0)
        pic[gap2] = (90, 150, 240)
        pic[gap1] = (0, 40, 160)
        pictures.append(Image.fromarray(pic))
    return rows, pictures


def report(label, rows, total=True):
    print('\n{}'.format(label))
    print('{:22s} ink mm2   stroke <0.84  <0.42   gap <0.84  <0.42   (mm2)'.format('glyph'))
    for text, ink, t2, t1, g2, g1 in rows:
        print('  {:20s} {:6.1f}    {:6.2f}  {:6.2f}     {:6.2f}  {:6.2f}   thin {:4.1f}% of ink'
              .format(text[:20], ink, t2, t1, g2, g1, 100.0 * t2 / ink))
    if total and len(rows) > 1:
        tot = [sum(r[k] for r in rows) for k in range(1, 6)]
        print('  {:20s} {:6.1f}    {:6.2f}  {:6.2f}     {:6.2f}  {:6.2f}   thin {:4.1f}% of ink'
              .format('all', *tot, 100.0 * tot[1] / tot[0]))


def sheet(groups, path):
    """One row of glyph cells per font, then each phrase on its own row."""
    cell, width = 220, 1800
    blocks = []
    for label, glyph_pics, phrase_pics in groups:
        blocks.append(('label', label))
        for start in range(0, len(glyph_pics), width // cell):
            blocks.append(('cells', glyph_pics[start:start + width // cell]))
        for p in phrase_pics:
            blocks.append(('phrase', p))
    heights = {'label': 30, 'cells': cell, 'phrase': 160}
    img = Image.new('RGB', (width + 40, sum(heights[k] for k, _ in blocks) + 20), 'white')
    d = ImageDraw.Draw(img)
    y = 10
    for kind, item in blocks:
        if kind == 'label':
            d.text((20, y + 8), item, fill='black')
        elif kind == 'cells':
            for k, p in enumerate(item):
                s = (cell - 20) / max(p.size)
                p = p.resize((max(1, round(p.size[0] * s)), max(1, round(p.size[1] * s))), Image.LANCZOS)
                img.paste(p, (20 + k * cell + (cell - p.size[0]) // 2, y + (cell - p.size[1]) // 2))
        else:
            s = min(width / item.size[0], 150 / item.size[1])
            p = item.resize((max(1, round(item.size[0] * s)), max(1, round(item.size[1] * s))), Image.LANCZOS)
            img.paste(p, (20, y + 5))
        y += heights[kind]
    img.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('ttf', nargs='?', default=os.path.join(HERE, 'build', 'CountdownDigits-Regular.ttf'))
    ap.add_argument('--ink', type=float, default=11.0,
                    help='size so all ten digits stand this tall, mm, as the cube scripts do')
    ap.add_argument('--em', type=float, help="the font's em on the model, mm, instead of --ink")
    ap.add_argument('--chars', default=DIGITS, help='the glyphs to measure one by one')
    ap.add_argument('--text', action='append', default=[], help='a phrase to measure as a whole')
    ap.add_argument('--fit', nargs=2, type=float, metavar=('RUN', 'HEIGHT'),
                    help='size the text to fit RUN x HEIGHT mm, as the model scripts do')
    ap.add_argument('--compare', help='another font to measure the same way')
    ap.add_argument('--compare-em', type=float, help="its em on the model, mm, instead of --ink")
    args = ap.parse_args()

    groups = []
    for ttf, em in ((args.ttf, args.em), (args.compare, args.compare_em)):
        if not ttf:
            continue
        if args.fit and args.text:
            em = fit_em(ttf, args.text, *args.fit)
        elif em is None:
            em = ink_em(ttf, args.ink)
        label = '{} at a {:.2f} mm em'.format(os.path.basename(ttf), em)
        rows, pics = measure(ttf, em, [c for c in args.chars if c.strip()])
        report(label, rows)
        prows, ppics = measure(ttf, em, args.text) if args.text else ([], [])
        if prows:
            report('{}, whole phrases'.format(label), prows, total=False)
        groups.append((label, pics, ppics))
    out = os.path.join(HERE, 'build', 'printability.png')
    sheet(groups, out)
    print('\nWrote {}'.format(out))


if __name__ == '__main__':
    main()
