# render_navmesh.py - overlay baked NavMesh triangles (green) on the level floor plan.
# Usage: py -3 specs/render_navmesh.py [layout.json] [navmesh.json] [out.png]
import io
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYOUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'specs', 'heist-bank-v3.json')
NAVMESH = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'specs', 'navmesh-latest.json')
OUT = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, 'specs', 'navmesh-overlay.png')
SCALE = 36
MARGIN = 60

with io.open(os.path.join(ROOT, 'specs', 'heist-catalog.json'), encoding='utf-8') as f:
    CATALOG = json.load(f)
BY = {}
for e in CATALOG:
    BY.setdefault(e['name'], e)
with io.open(LAYOUT, encoding='utf-8') as f:
    DATA = json.load(f)
with io.open(NAVMESH, encoding='utf-8') as f:
    NAV = json.load(f)

mins = [1e9, 1e9]
maxs = [-1e9, -1e9]
for r in DATA['rooms']:
    mins[0] = min(mins[0], r['bounds']['min'][0])
    mins[1] = min(mins[1], r['bounds']['min'][2])
    maxs[0] = max(maxs[0], r['bounds']['max'][0])
    maxs[1] = max(maxs[1], r['bounds']['max'][2])

W = int((maxs[0] - mins[0]) * SCALE) + 2 * MARGIN
H = int((maxs[1] - mins[1]) * SCALE) + 2 * MARGIN + 60
img = Image.new('RGB', (W, H), (255, 255, 255))
d = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype('arial.ttf', 14)
    small = ImageFont.truetype('arial.ttf', 11)
except Exception:
    font = ImageFont.load_default()
    small = font


def px(x, z):
    return (MARGIN + (x - mins[0]) * SCALE, MARGIN + (z - mins[1]) * SCALE)


def name_of(p):
    return p['prefab'].split('/')[-1].replace('.prefab', '')


def rot_bounds(name, rot):
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


for r in DATA['rooms']:
    b = r['bounds']
    a = px(b['min'][0], b['min'][2])
    c = px(b['max'][0], b['max'][2])
    d.rectangle([a[0], a[1], c[0], c[1]], outline=(200, 200, 200))

# walls/props light grey so the overlay reads clearly
for r in DATA['rooms']:
    for p in r['props']:
        n = name_of(p)
        if n not in BY:
            continue
        if 'Floor' in n or 'Ceiling' in n or 'Roof' in n:
            continue
        x0, x1, z0, z1 = rot_bounds(n, p['rotation'][1])
        x0 += p['position'][0]
        x1 += p['position'][0]
        z0 += p['position'][2]
        z1 += p['position'][2]
        a = px(x0, z0)
        c = px(x1, z1)
        col = (120, 120, 120) if n.startswith('SM_Env_') else (205, 205, 205)
        d.rectangle([a[0], a[1], c[0], c[1]], fill=col)

# navmesh triangles (green, alpha-blended via overlay)
overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
od = ImageDraw.Draw(overlay)
verts = NAV.get('vertices', [])
idx = NAV.get('indices', [])
tris = 0
for i in range(0, len(idx) - 2, 3):
    pts = []
    for k in (idx[i], idx[i + 1], idx[i + 2]):
        if k < 0 or k >= len(verts):
            continue
        v = verts[k]
        pts.append(px(v[0], v[2]))
    if len(pts) == 3:
        od.polygon(pts, fill=(0, 200, 80, 90))
        tris += 1
img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
d = ImageDraw.Draw(img)

# spawns + cover points
for r in DATA['rooms']:
    for sp in r.get('spawnPoints', []) or []:
        c = px(sp['position'][0], sp['position'][2])
        col = (0, 120, 0) if sp.get('team') == 1 else (170, 0, 0)
        d.ellipse([c[0] - 6, c[1] - 6, c[0] + 6, c[1] + 6], fill=col)
    for cp in r.get('coverPoints', []) or []:
        c = px(cp['position'][0], cp['position'][2])
        d.rectangle([c[0] - 3, c[1] - 3, c[0] + 3, c[1] + 3], fill=(0, 120, 220))

d.text((MARGIN, H - 30), 'navmesh tris=%d verts=%d  |  %s' % (tris, len(verts), os.path.basename(NAVMESH)),
       fill=(40, 40, 40), font=font)
img.save(OUT)
print('WROTE', OUT, img.size, 'tris', tris, 'verts', len(verts))
