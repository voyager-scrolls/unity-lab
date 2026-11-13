# render_floorplan.py - draws a level layout JSON top-down using catalog-measured footprints.
# Usage: py -3 specs/render_floorplan.py [specs/heist-bank-v3.json] [out.png]
# Colours: floors pastel per room, walls dark grey, doors orange, furniture blue,
# valuables gold, vehicles red, spawns green (team number), exterior light grey.
import io
import json
import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    raise SystemExit('PIL missing: py -3 -m pip install pillow')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYOUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'specs', 'heist-bank-v3.json')
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'specs', 'floorplan.png')
SCALE = 36  # px per metre
MARGIN = 60

with io.open(os.path.join(ROOT, 'specs', 'heist-catalog.json'), encoding='utf-8') as f:
    CATALOG = json.load(f)
BY = {}
for e in CATALOG:
    BY.setdefault(e['name'], e)
with io.open(LAYOUT, encoding='utf-8') as f:
    LAYOUT_DATA = json.load(f)

ROOM_COLORS = {
    'exterior': (226, 226, 226),
    'lobby': (255, 244, 214),
    'teller': (214, 240, 255),
    'vault': (255, 220, 220),
    'corridorL': (228, 255, 228),
    'corridorR': (240, 228, 255),
}


def bounds(name, rot):
    b = BY[name]['bounds']
    x0, x1, z0, z1 = b['min'][0], b['max'][0], b['min'][2], b['max'][2]
    r = int(round(rot)) % 360
    if r == 90:
        return z0, z1, -x1, -x0
    if r == 180:
        return -x1, -x0, -z1, -z0
    if r == 270:
        return -z1, -z0, x0, x1
    return x0, x1, z0, z1


def name_of(p):
    return p['prefab'].split('/')[-1].replace('.prefab', '')


# canvas bounds from layout rooms (+ margin)
mins = [1e9, 1e9]
maxs = [-1e9, -1e9]
for r in LAYOUT_DATA['rooms']:
    mins[0] = min(mins[0], r['bounds']['min'][0])
    mins[1] = min(mins[1], r['bounds']['min'][2])
    maxs[0] = max(maxs[0], r['bounds']['max'][0])
    maxs[1] = max(maxs[1], r['bounds']['max'][2])

W = int((maxs[0] - mins[0]) * SCALE) + 2 * MARGIN
H = int((maxs[1] - mins[1]) * SCALE) + 2 * MARGIN + 80
img = Image.new('RGB', (W, H), (255, 255, 255))
d = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype('arial.ttf', 16)
    small = ImageFont.truetype('arial.ttf', 11)
except Exception:
    font = ImageFont.load_default()
    small = ImageFont.load_default()


def px(x, z):
    return (MARGIN + (x - mins[0]) * SCALE, MARGIN + (z - mins[1]) * SCALE)


def rect(x0, z0, x1, z1, fill=None, outline=None, width=1):
    a = px(x0, z0)
    b = px(x1, z1)
    d.rectangle([a[0], a[1], b[0], b[1]], fill=fill, outline=outline, width=width)


# room floors with labels
for r in LAYOUT_DATA['rooms']:
    b = r['bounds']
    col = ROOM_COLORS.get(r['id'], (240, 240, 240))
    rect(b['min'][0], b['min'][2], b['max'][0], b['max'][2], fill=col)
    lp = px((b['min'][0] + b['max'][0]) / 2, (b['min'][2] + b['max'][2]) / 2)
    d.text((lp[0] - 34, lp[1] - 8), r['id'], fill=(90, 90, 90), font=font)

# 5m grid over interior
for x in range(-25, 26, 5):
    a = px(x, mins[1])
    b = px(x, maxs[1])
    d.line([a[0], a[1], b[0], b[1]], fill=(235, 235, 235), width=1)

# props
for r in LAYOUT_DATA['rooms']:
    for p in r['props']:
        n = name_of(p)
        if not n.startswith('SM_Env_') and not n.startswith('SM_Prop_') and not n.startswith('SM_Item_') and not n.startswith('SM_Veh_'):
            continue
        if 'Floor' in n or 'Ceiling' in n:
            continue
        x, z = p['position'][0], p['position'][2]
        x0, x1, z0, z1 = bounds(n, p['rotation'][1])
        x0 += x; x1 += x; z0 += z; z1 += z
        if n.startswith('SM_Env_Wall') or n.startswith('SM_Env_Vault'):
            if 'Door' in n or 'Frame' in n:
                rect(x0, z0, x1, z1, fill=(255, 165, 60), outline=(180, 100, 0))
            else:
                rect(x0, z0, x1, z1, fill=(70, 70, 70))
        elif n.startswith('SM_Veh_'):
            rect(x0, z0, x1, z1, fill=(220, 60, 60))
        elif n.startswith('SM_Item_') or 'Jewellery' in n or 'GoldBar' in n or 'Money' in n:
            rect(x0, z0, x1, z1, fill=(240, 200, 40))
        elif n.startswith('SM_Prop_'):
            if 'Rug' in n:
                rect(x0, z0, x1, z1, fill=(250, 230, 200), outline=(220, 190, 150))
            else:
                rect(x0, z0, x1, z1, fill=(120, 160, 220))

# spawn points
for r in LAYOUT_DATA['rooms']:
    for sp in r.get('spawnPoints', []) or []:
        x, z = sp['position'][0], sp['position'][2]
        c = px(x, z)
        col = (0, 160, 0) if sp.get('team') == 1 else (160, 0, 0)
        d.ellipse([c[0] - 7, c[1] - 7, c[0] + 7, c[1] + 7], fill=col)
        d.text((c[0] - 4, c[1] - 7), 'T' + str(sp.get('team', '?')), fill=(255, 255, 255), font=small)

# legend
ly = H - 70
items = [((70, 70, 70), 'walls'), ((255, 165, 60), 'doors'), ((120, 160, 220), 'props'),
         ((240, 200, 40), 'valuables'), ((220, 60, 60), 'vehicles'), ((0, 160, 0), 'spawn T1'),
         ((160, 0, 0), 'spawn T2')]
lx = MARGIN
for col, label in items:
    d.rectangle([lx, ly, lx + 14, ly + 14], fill=col)
    d.text((lx + 20, ly), label, fill=(60, 60, 60), font=small)
    lx += 110
d.text((MARGIN, ly + 24), '%s  |  %.0f px/m  |  bounds X %.0f..%.0f  Z %.0f..%.0f' % (
    os.path.basename(LAYOUT), SCALE, mins[0], maxs[0], mins[1], maxs[1]), fill=(60, 60, 60), font=small)

img.save(OUT)
print('WROTE', OUT, img.size)
