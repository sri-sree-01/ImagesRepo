"""Build the v3 plate set for TTD Info's "Today's Srivari Card".

Sources (originals are never modified):
  - newjigsaw_images/                          square deity / ayudha / vahanam art
  - hservices.in/wishes/images/{balaji,krishna,lakshmi,shiva,universal}

Output (under ttd_info/daily_card/):
  srivari/  divine/  wishes/   optimized JPEGs
  manifest_v3.json             read by app builds with themed rotation;
                               manifest.json (v2) is left untouched for
                               older app versions.

Run:  python scripts/build_daily_card_v3.py
"""
import json
import os
import re
from datetime import date

from PIL import Image, ImageEnhance, ImageFilter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, 'ttd_info', 'daily_card')
JIGSAW = os.path.join(REPO, 'newjigsaw_images')
WISHES = r'D:\MyData\workspace\GitHub\hservices.in\wishes\images'

QUALITY = 80
SQUARE = 1080
MAX_W = 1080  # portrait plates are kept at native size up to this width

# ── jigsaw art: theme by file stem (from a visual review) ────────────────
JIGSAW_THEMES = {
    'krishna': ['a (1)', 'c (3)', 'c (4)', 'd (10)', 'd (9)', 'e (6)', 'g (21)',
                'g (23)', 'g (4)', 'g (5)', 'g (6)', 'h (4)', 'i (11)',
                'i (14)', 'i (15)', 'i (16)', 'i (3)'],
    'vishnu': ['a (2)', 'd (13)', 'g (22)', 'i (10)', 'i (4)'],
    'ayudha': ['a (27)', 'a (28)', 'b (6)', 'b (7)', 'b (8)', 'c (17)', 'c (18)',
               'c (19)', 'c (20)', 'c (5)', 'c (7)', 'e (10)', 'e (7)', 'e (8)',
               'f (14)', 'f (3)', 'f (4)', 'f (5)', 'f (6)', 'g (1)', 'g (24)',
               'g (7)', 'g (8)', 'h (1)', 'h (10)', 'h (14)', 'h (2)', 'h (3)',
               'h (8)', 'i (1)', 'i (17)', 'i (18)', 'i (2)'],
    'ganesha': ['c (30)', 'c (31)', 'e (12)', 'e (17)', 'e (18)', 'e (5)',
                'f (15)', 'f (16)', 'f (17)', 'f (18)', 'f (22)', 'f (23)',
                'g (18)', 'g (19)', 'g (20)', 'g (3)', 'g (9)', 'h (11)',
                'h (12)', 'h (13)', 'h (9)', 'i (5)', 'i (6)', 'i (7)',
                'i (8)', 'i (9)'],
    'shiva': ['c (6)', 'f (8)', 'f (9)', 'k (11)', 'k (15)', 'k (35)', 'k (37)'],
    'lakshmi': ['g (2)', 'k (1)', 'k (23)', 'k (8)'],
    'vahanam': ['k (12)', 'k (13)', 'k (14)', 'k (16)', 'k (18)', 'k (2)',
                'k (22)', 'k (24)', 'k (25)', 'k (26)', 'k (27)', 'k (28)',
                'k (3)', 'k (30)', 'k (31)', 'k (32)', 'k (33)', 'k (34)',
                'k (38)', 'k (4)', 'k (5)', 'k (6)', 'k (7)', 'k (9)'],
}
# Collage, framed photo, baked-in text, or animals that read as inauspicious
# on a blessing card (buffalo, owl, camel, rat, ram, makara).
JIGSAW_SKIP = {'k (10)', 'k (17)', 'k (19)', 'k (20)', 'k (21)', 'k (29)',
               'k (36)', 'i (12)', 'i (13)'}

BALAJI_SKIP = {'87.jpg', '110.jpg'}  # white-background cut-outs

WISHES_ITEMS = [  # (group, file, theme)
    ('krishna', 'krishna1.jpeg', 'vishnu'),   # Sri Rama
    ('krishna', 'krishna2.jpeg', 'vishnu'),
    ('krishna', 'krishna3.jpeg', 'vishnu'),   # Anantha Sayana
    ('krishna', 'krishna4.jpeg', 'krishna'),
    ('krishna', 'krishna5.jpeg', 'krishna'),
    ('krishna', 'krishna6.jpeg', 'krishna'),
    ('lakshmi', 'lakshmi1.jpeg', 'lakshmi'),
    ('lakshmi', 'lakshmi2.jpeg', 'lakshmi'),
    ('lakshmi', 'lakshmi3.jpeg', 'lakshmi'),
    ('lakshmi', 'lakshmi4.jpeg', 'lakshmi'),
    ('shiva', 'shiva1.png', 'shiva'),
    ('shiva', 'shiva2.png', 'shiva'),
    ('shiva', 'shiva3.png', 'shiva'),
    ('universal', '1.jpg', 'tirumala'),
    ('universal', '2.jpg', 'tirumala'),
    ('universal', '3.jpg', 'tirumala'),
    ('universal', '4.jpg', 'srivari'),
    ('universal', '5.jpg', 'srivari'),
    ('universal', '6.jpg', 'srivari'),
    ('universal', '7.jpg', 'tirumala'),
    # 4.png / 5.png / 7.png are duplicates of the .jpg files.
]

LABELS = {
    'srivari': 'Srivari', 'vishnu': 'Sri Maha Vishnu', 'krishna': 'Sri Krishna',
    'ganesha': 'Vighneswara', 'lakshmi': 'Sri Mahalakshmi', 'shiva': 'Maha Shiva',
    'ayudha': 'Divya Ayudham', 'vahanam': 'Vahanam', 'tirumala': 'Tirumala',
}

# Which themes today's default plate is picked from, per weekday. Days not
# listed use every plate.
WEEKDAYS = {
    'mon': ['shiva'],               # Somavaram
    'wed': ['ganesha', 'krishna'],  # Budhavaram
    'thu': ['vishnu', 'ayudha'],    # Guruvaram
    'fri': ['lakshmi'],             # Sukravaram
    'sat': ['srivari'],             # Sanivaram — Srivari's day
}


def save(im, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.convert('RGB').save(path, 'JPEG', quality=QUALITY, optimize=True,
                           progressive=True)


def to_square(im):
    """Square plate. Near-square art is centre-cropped; wide art is fitted
    on a blurred, darkened copy of itself so nothing is cut off."""
    im = im.convert('RGB')
    w, h = im.size
    ratio = max(w, h) / min(w, h)
    if ratio <= 1.3:
        s = min(w, h)
        im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
        return im.resize((SQUARE, SQUARE), Image.LANCZOS)
    scale = SQUARE / min(w, h)
    bg = im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
    bw, bh = bg.size
    bg = bg.crop(((bw - SQUARE) // 2, (bh - SQUARE) // 2,
                  (bw - SQUARE) // 2 + SQUARE, (bh - SQUARE) // 2 + SQUARE))
    bg = ImageEnhance.Brightness(bg.filter(ImageFilter.GaussianBlur(28))).enhance(0.6)
    fit = SQUARE / max(w, h)
    fg = im.resize((round(w * fit), round(h * fit)), Image.LANCZOS)
    bg.paste(fg, ((SQUARE - fg.size[0]) // 2, (SQUARE - fg.size[1]) // 2))
    return bg


def portrait(im):
    im = im.convert('RGB')
    w, h = im.size
    if w > MAX_W:
        im = im.resize((MAX_W, round(h * MAX_W / w)), Image.LANCZOS)
    return im


def slug(stem):
    return re.sub(r'[^a-z0-9]+', '_', stem.lower()).strip('_')


def main():
    arts = []
    unmapped = []

    # Keep every v2 plate (all Srivari), first.
    v2 = json.load(open(os.path.join(OUT, 'manifest.json'), encoding='utf-8'))
    for a in v2['arts']:
        arts.append({**a, 'theme': 'srivari'})

    # Srivari (balaji) — tall 9:16 plates.
    bdir = os.path.join(WISHES, 'balaji')
    def bkey(f):
        m = re.match(r'(\d+)', f)
        return (0, int(m.group(1))) if m else (1, f)
    for f in sorted(os.listdir(bdir), key=bkey):
        if f in BALAJI_SKIP or not f.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue
        im = Image.open(os.path.join(bdir, f))
        w, h = im.size
        square = h / w < 1.2
        rel = f'srivari/{slug(os.path.splitext(f)[0])}.jpg'
        save(to_square(im) if square else portrait(im), os.path.join(OUT, rel))
        arts.append({'file': rel, 'layout': 'square' if square else 'full',
                     'label': LABELS['srivari'], 'theme': 'srivari'})

    # Divine (jigsaw) — square.
    theme_of = {stem: t for t, stems in JIGSAW_THEMES.items() for stem in stems}
    for f in sorted(os.listdir(JIGSAW)):
        stem, ext = os.path.splitext(f)
        if ext.lower() != '.png' or stem in JIGSAW_SKIP:
            continue
        t = theme_of.get(stem)
        if t is None:
            unmapped.append(f)
            continue
        rel = f'divine/{t}_{slug(stem)}.jpg'
        save(to_square(Image.open(os.path.join(JIGSAW, f))), os.path.join(OUT, rel))
        arts.append({'file': rel, 'layout': 'square', 'label': LABELS[t], 'theme': t})

    # Wishes (krishna / lakshmi / shiva / universal).
    for group, f, t in WISHES_ITEMS:
        im = Image.open(os.path.join(WISHES, group, f))
        w, h = im.size
        tall = h / w >= 1.2
        rel = f'wishes/{group}_{slug(os.path.splitext(f)[0])}.jpg'
        save(portrait(im) if tall else to_square(im), os.path.join(OUT, rel))
        arts.append({'file': rel, 'layout': 'full' if tall else 'square',
                     'label': LABELS[t], 'theme': t})

    manifest = {
        'version': 3,
        'updated': date.today().isoformat(),
        'weekdays': WEEKDAYS,
        'arts': arts,
        'vahanams': v2.get('vahanams', {}),
    }
    with open(os.path.join(OUT, 'manifest_v3.json'), 'w', encoding='utf-8') as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    counts = {}
    for a in arts:
        counts[a['theme']] = counts.get(a['theme'], 0) + 1
    print('plates:', len(arts), counts)
    if unmapped:
        print('UNMAPPED jigsaw files (skipped):', unmapped)


if __name__ == '__main__':
    main()
