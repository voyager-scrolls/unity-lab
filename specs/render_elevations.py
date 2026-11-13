# render_elevations.py - front (X-Y) and side (Z-Y) elevations from a level layout JSON.
# Catches floating props, desk stacking errors, ceiling/roof gaps without a Unity build.
# Usage: py -3 specs/render_elevations.py [layout.json] [out-prefix]
import io
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYOUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'specs', 'heist-bank-v3.json')
PREFIX = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'specs', 'elevation')

with io.open(os.path.join(ROOT, 'specs', 'heist-catalog.json'), encoding='utf-8') as f:
    CATALOG = json.load(f)
BY = {}
for e in CATALOG:
    BY.setdefault(e['name'], e)
with io.open(LAYOUT, encoding='utf-8') as f:
    DATA = json.load(f)


def name_of(p):
    return p['prefab'].split('/')[-1].replace('.prefab', '')


def y_range(p):
    b = BY[name_of(p)]['bounds']
    return p['position'][1] + b['min'][1], p['position'][1] + b['max'][1]


def x_range(p):
    n = name_of(p)
    b = BY[n]['bounds']
    x0, x1 = b['min'][0], b['max'][0]
    z0, z1 = b['min'][2], b['max'][2]
    r = int(round(p['rotation'][1])) % 360
    if r == 90:
        x0, x1 = z0, z1
    elif r == 180:
        x0, x1 = -x1, -x0
    elif r == 270:
        x0, x1 = -z1, -z0
    return p['position'][0] + x0, p['position'][0] + x1


def z_range(p):
    n = name_of(p)
    b = BY[n]['bounds']
    x0, x1 = b['min'][0], b['max'][0]
    z0, z1 = b['min'][2], b['max'][2]
    r = int(round(p['rotation'][1])) % 360
    if r == 90:
        z0, z1 = -x1, -x0
    elif r == 180:
        z0, z1 = -z1, -z0
    elif r == 270:
        z0, z1 = x0, x1
    return p['position'][2] + z0, p['position'][2] + z1


def color_for(n):
    if n.startswith('SM_Env_Wall') or n.startswith('SM_Env_Vault'):
        return (80, 80, 80)
    if n.startswith('SM_Env_Ceiling'):
        return (150, 150, 150)
    if n.startswith('SM_Env_Roof'):
        return (110, 110, 110)
    if n.startswith('SM_Env_Floor'):
        return (200, 200, 200)
    if n.startswith('SM_Veh_'):
        return (220, 60, 60)
    if 'Jewellery' in n or 'GoldBar' in n or 'Money' in n or n.startswith('SM_Item_'):
        return (240, 200, 40)
    return (120, 160, 220)


def render(axis, out):
    if axis == 'front':
        lo, hi = -20.0, 20.0
        getter = x_range
        label = 'FRONT ELEVATION (X-Y)'
    else:
        lo, hi = -25.0, 27.0
        getter = z_range
        label = 'SIDE ELEVATION (Z-Y)'
    SCALE = 30
    M = 60
    W = int((hi - lo) * SCALE) + 2 * M
    H = int(8.0 * SCALE) + 2 * M + 40
    img = Image.new('RGB', (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype('arial.ttf', 14)
    except Exception:
        font = ImageFont.load_default()

    def px(u, y):
        return (M + (u - lo) * SCALE, M + (7.5 - y) * SCALE)

    # ground + floor lines
    d.line([px(lo, 0)[0], px(lo, 0)[1], px(hi, 0)[0], px(hi, 0)[1]], fill=(120, 120, 120), width=2)
    for lvl in (3.0, 6.0):
        d.line([px(lo, lvl)[0], px(lo, lvl)[1], px(hi, lvl)[0], px(hi, lvl)[1]], fill=(225, 225, 225))

    items = []
    for room in DATA['rooms']:
        for p in room['props']:
            n = name_of(p)
            if n not in BY:
                continue
            a0, a1 = getter(p)
            y0, y1 = y_range(p)
            if a1 < lo or a0 > hi:
                continue
            col = color_for(n)
            items.append((y0, n, a0, a1, y0, y1, col))
    items.sort(key=lambda t: t[0])
    for _, n, a0, a1, y0, y1, col in items:
        p0 = px(a0, y1)
        p1 = px(a1, y0)
        if p1[0] - p0[0] < 1:
            continue
        d.rectangle([p0[0], p0[1], p1[0], p1[1]], outline=col)
    d.text((M, H - 34), '%s  |  %s' % (label, os.path.basename(LAYOUT)), fill=(60, 60, 60), font=font)
    img.save(out)
    print('WROTE', out, img.size)


render('front', PREFIX + '-front.png')
render('side', PREFIX + '-side.png')
