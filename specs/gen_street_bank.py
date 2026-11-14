"""Street Bank Heist level generator (reference: Bank_robbery_map_scene LVL-04).

Builds a neoclassical kit-built bank on a 25 x 20 m footprint facing a 20 m road,
with a forecourt, street blockade and flanking city buildings.

Writes specs/street-bank-v1.json in the schema consumed by LevelLayoutGenerator.
Run: py -3 specs/gen_street_bank.py
"""
import json
import os
import math

HERE = os.path.dirname(os.path.abspath(__file__))
CAT_PATH = os.path.join(HERE, 'city-catalog.json')
OUT_PATH = os.path.join(HERE, 'street-bank-v1.json')

CAT = json.load(open(CAT_PATH, encoding='utf-8'))['entries']

PACK_DIR = {
    'heist': 'PolygonHeist',
    'city': 'PolygonCity',
    'town': 'PolygonTown',
    'br': 'PolygonBattleRoyale',
}


def find(pack, name):
    key = '/' + PACK_DIR[pack] + '/'
    for e in CAT:
        if e['name'] == name and key in e['path']:
            return e
    raise SystemExit('MISSING PREFAB: %s / %s' % (pack, name))


def bnd(pack, name):
    b = find(pack, name)['bounds']
    return (b['min'][0], b['min'][1], b['min'][2],
            b['max'][0], b['max'][1], b['max'][2])


def rot_pt(px, pz, rot):
    """Unity Y rotation: x' = x cos + z sin, z' = -x sin + z cos."""
    r = math.radians(rot % 360)
    c, s = math.cos(r), math.sin(r)
    return px * c + pz * s, -px * s + pz * c


ROOMS = {}
ORDER = ['exterior', 'lobby', 'teller']


def room(rid, mn, mx):
    ROOMS[rid] = {
        'id': rid,
        'bounds': {'min': mn, 'max': mx},
        'props': [],
        'spawnPoints': [],
        'coverPoints': [],
        'killZones': [],
    }


room('exterior', [-40.0, 0.0, -56.0], [40.0, 12.0, 0.0])
room('lobby', [-12.5, 0.0, 0.0], [12.5, 6.0, 15.0])
room('teller', [-12.5, 0.0, 15.0], [12.5, 3.4, 20.0])

TRACK = {}
FOOT = []
GAP = 0.012


def emit(rid, pack, name, px, py, pz, rot):
    e = find(pack, name)
    ROOMS[rid]['props'].append({
        'prefab': e['path'],
        'position': [round(px, 4), round(py, 4), round(pz, 4)],
        'rotation': [0.0, float(rot % 360), 0.0],
        'scale': [1.0, 1.0, 1.0],
    })
    return e


def add(rid, pack, name, x, z, rot=0, y=None, key=None):
    """Centre the rotated footprint at (x, z); ground-snap unless y given."""
    x0, y0, z0, x1, y1, z1 = bnd(pack, name)
    cx, cz = rot_pt((x0 + x1) / 2.0, (z0 + z1) / 2.0, rot)
    if y is None:
        y = -y0
    px, pz = x - cx, z - cz
    emit(rid, pack, name, px, y, pz, rot)
    FOOT.append((rid, name, x, z, (x1 - x0) / 2.0, (z1 - z0) / 2.0, y))
    if key:
        TRACK[key] = (x, z, y + y1)
    return key


def add_on(rid, key, pack, name, dx, dz, rot=0, lift=0.0):
    """Stack a prop on top of a tracked host using WORLD offsets."""
    hx, hz, top = TRACK[key]
    x0, y0, z0, x1, y1, z1 = bnd(pack, name)
    cx, cz = rot_pt((x0 + x1) / 2.0, (z0 + z1) / 2.0, rot)
    emit(rid, pack, name, hx + dx - cx, top + GAP + lift, hz + dz - cz, rot)


# ---------------------------------------------------------------- ground
# Forecourt: 16 x 2 pale slabs, z 0..-10.
for x in (-37.5, -32.5, -27.5, -22.5, -17.5, -12.5, -7.5, -2.5, 2.5, 7.5, 12.5, 17.5, 22.5, 27.5, 32.5, 37.5):
    for z in (-2.5, -7.5):
        add('exterior', 'city', 'SM_Env_Sidewalk_01', x, z)

# Road: 16 x 4 asphalt tiles, z -10..-30.
for x in (-37.5, -32.5, -27.5, -22.5, -17.5, -12.5, -7.5, -2.5, 2.5, 7.5, 12.5, 17.5, 22.5, 27.5, 32.5, 37.5):
    for z in (-12.5, -17.5, -22.5, -27.5):
        add('exterior', 'city', 'SM_Env_Road_01', x, z)

# Lane markings down the road centre.
for x in (-37.5, -32.5, -27.5, -22.5, -17.5, -12.5, -7.5, -2.5, 2.5, 7.5, 12.5, 17.5, 22.5, 27.5, 32.5, 37.5):
    add('exterior', 'city', 'SM_Env_Road_Lines_01', x, -20.0, y=0.012)

# Zebra crossing on the bank axis.
for x in (-2.5, 2.5):
    add('exterior', 'city', 'SM_Env_Road_Crossing_01', x, -11.0, y=0.012)

# Far sidewalk: 16 x 2 slabs, z -30..-40.
for x in (-37.5, -32.5, -27.5, -22.5, -17.5, -12.5, -7.5, -2.5, 2.5, 7.5, 12.5, 17.5, 22.5, 27.5, 32.5, 37.5):
    for z in (-32.5, -37.5):
        add('exterior', 'city', 'SM_Env_Sidewalk_01', x, z)

# ---------------------------------------------------------------- building shell
# Front facade, z = 0: solid courses. Ground floor leaves a 5 m entrance gap.
FACADE = []
for x in (-10.0, -5.0, 5.0, 10.0):
    add('lobby', 'heist', 'SM_Env_Wall_Exterior_01', x, 0.0, 0.0, y=0.0)
for y in (3.0, 6.0, 9.0):
    for x in (-10.0, -5.0, 0.0, 5.0, 10.0):
        add('lobby', 'heist', 'SM_Env_Wall_Exterior_01', x, 0.0, 0.0, y=y)
for y in (0.0, 3.0, 6.0, 9.0):
    for x in ((-10.0, -5.0, 5.0, 10.0) if y == 0.0 else (-10.0, -5.0, 0.0, 5.0, 10.0)):
        FACADE.append((x, y, 2.5))

# Side walls x = +-12.5, four courses, z 0..20.
for y in (0.0, 3.0, 6.0, 9.0):
    for z in (2.5, 7.5, 12.5, 17.5):
        add('lobby', 'heist', 'SM_Env_Wall_Exterior_01', -12.5, z, 90, y=y)
        add('lobby', 'heist', 'SM_Env_Wall_Exterior_01', 12.5, z, 270, y=y)

# Back wall z = 20.
for y in (0.0, 3.0, 6.0, 9.0):
    for x in (-10.0, -5.0, 0.0, 5.0, 10.0):
        add('teller', 'heist', 'SM_Env_Wall_Exterior_01', x, 20.0, 180, y=y)

# Cornice and stepped pediment.
for x in (-10.0, -5.0, 0.0, 5.0, 10.0):
    add('lobby', 'heist', 'SM_Env_Roof_05', x, 0.0, 0.0, y=12.0)
for x in (-10.0, -5.0, 0.0, 5.0, 10.0):
    add('lobby', 'heist', 'SM_Env_Roof_05', x, 0.0, 0.0, y=12.91)
for x in (-5.0, 0.0, 5.0):
    add('lobby', 'heist', 'SM_Env_Roof_05', x, 0.0, 0.0, y=13.82)

# ---------------------------------------------------------------- portico
PORTICO_X = (-7.5, -4.5, -1.5, 1.5, 4.5, 7.5)
for x in PORTICO_X:
    add('exterior', 'heist', 'SM_Env_Pillar_Exterior_Floor_01', x, -3.0, 0, y=0.0)
    add('exterior', 'heist', 'SM_Env_Pillar_Exterior_Floor_01', x, -3.0, 0, y=3.0)

for x in (-7.5, -2.5, 2.5, 7.5):
    add('exterior', 'heist', 'SM_Env_Floor_01', x, -2.5, 0, y=6.0)
    add('exterior', 'heist', 'SM_Env_Roof_05', x, -2.5, 0, y=6.07)

for x in (-7.5, 7.5):
    add('exterior', 'heist', 'SM_Env_Steps_Edge_01', x, -5.4, 0, y=0.0)

for x in (-6.0, 0.0, 6.0):
    add('exterior', 'heist', 'SM_Env_Ceiling_Light_01', x, -2.5, 0, y=5.95)

add('exterior', 'heist', 'SM_Env_Railing_01', -10.0, -5.4, 0, y=0.0)
add('exterior', 'heist', 'SM_Env_Railing_01', 10.0, -5.4, 0, y=0.0)

# ---------------------------------------------------------------- facade openings
WINDOW_X = (-11.0, -8.0, -5.0, -2.0, 2.0, 5.0, 8.0, 11.0)
for x in WINDOW_X:
    add('exterior', 'city', 'SM_Prop_Window_01', x, -0.26, 0, y=6.6)
for x in WINDOW_X:
    if abs(x) < 3.0:
        continue
    add('exterior', 'city', 'SM_Prop_Window_01', x, -0.26, 0, y=9.6)
for x in (-10.0, -7.5, -5.0, 5.0, 7.5, 10.0):
    add('exterior', 'city', 'SM_Prop_Window_01', x, -0.26, 0, y=1.0)

add('exterior', 'heist', 'SM_Prop_Sign_Money_Bank_01', 0.0, -0.26, 180, y=9.5)

for z in (2.5, 7.5, 12.5, 17.5):
    for y in (6.6, 9.6):
        add('exterior', 'city', 'SM_Prop_Window_01', -12.76, z, 90, y=y)
        add('exterior', 'city', 'SM_Prop_Window_01', 12.76, z, 270, y=y)

# ---------------------------------------------------------------- interior
for x in (-10.0, -5.0, 0.0, 5.0, 10.0):
    for z in (2.5, 7.5, 12.5):
        add('lobby', 'heist', 'SM_Env_Sidewalk_01', x, z, y=0.0)
        add('lobby', 'heist', 'SM_Env_Ceiling_01', x, z, y=6.0)
for x in (-10.0, -5.0, 0.0, 5.0, 10.0):
    add('teller', 'heist', 'SM_Env_Floor_02', x, 17.5)
    add('teller', 'heist', 'SM_Env_Ceiling_01', x, 17.5, y=3.4)

# Ceiling lights.
for x in (-8.0, 0.0, 8.0):
    for z in (3.0, 8.0, 12.0):
        add('lobby', 'heist', 'SM_Env_Ceiling_Light_01', x, z, y=5.99)
for x in (-8.0, 0.0, 8.0):
    add('teller', 'heist', 'SM_Env_Ceiling_Light_01', x, 17.5, y=3.39)

# Teller counters facing the lobby, staff side behind.
for x in (-5.0, 0.0, 5.0):
    key = 'desk%d' % int(x * 10)
    add('lobby', 'heist', 'SM_Prop_TellerDesk_01', x, 13.8, 180, key=key)
    add_on('lobby', key, 'heist', 'SM_Prop_Computer_01', 0.0, 0.0, 0)
    add_on('lobby', key, 'heist', 'SM_Prop_DeskLight_01', -0.85, 0.1, 180)
    add_on('lobby', key, 'heist', 'SM_Prop_Money_Stack_01', -0.55, 0.25, 15)
    add_on('lobby', key, 'heist', 'SM_Prop_Folder_01', 0.72, 0.12, 90)

# Teller partition at z=15, staff openings beyond +-7.5.
for x in (-5.0, 0.0, 5.0):
    add('lobby', 'heist', 'SM_Env_Wall_Interior_01', x, 15.0, 0, y=0.0)
add('lobby', 'heist', 'SM_Prop_Sign_Bank_01', 0.0, 14.9, 180, y=2.05)
add('lobby', 'heist', 'SM_Prop_Flag_Wall_01', -4.8, 14.9, 180, y=1.40)
add('lobby', 'heist', 'SM_Prop_Flag_Wall_02', 4.8, 14.9, 180, y=1.40)

# Lobby furniture and dressing.
add('lobby', 'heist', 'SM_Prop_Rug_01', 0.0, 8.0)
add('lobby', 'heist', 'SM_Prop_Statue_01', 0.0, 2.4, 180)
add('lobby', 'heist', 'SM_Prop_Pillar_01', -6.0, 8.0, 0, key='bustL')
add_on('lobby', 'bustL', 'heist', 'SM_Prop_Statue_01', 0.0, 0.0, 180)
add('lobby', 'heist', 'SM_Prop_Pillar_01', 6.0, 8.0, 0, key='bustR')
add_on('lobby', 'bustR', 'heist', 'SM_Prop_Statue_01', 0.0, 0.0, 180)
add('lobby', 'heist', 'SM_Prop_Couch_01', -10.2, 4.0, 90)
add('lobby', 'heist', 'SM_Prop_Couch_02', 10.2, 4.0, 270)
add('lobby', 'heist', 'SM_Prop_CoffeeTable_02', -10.2, 6.6, 90)
add('lobby', 'heist', 'SM_Prop_ATM_01', -10.6, 10.6, 90)
add('lobby', 'heist', 'SM_Prop_ATM_01', 10.6, 10.6, 270)
add('lobby', 'heist', 'SM_Prop_Plant_01', -11.4, 1.4, 0)
add('lobby', 'heist', 'SM_Prop_Plant_01', 11.4, 1.4, 0)
add('lobby', 'heist', 'SM_Prop_DisplayCase_01', -11.5, 12.6, 90)
add('lobby', 'heist', 'SM_Prop_DisplayCase_02', 11.5, 12.6, 270)

# Teller back office.
add('teller', 'heist', 'SM_Prop_Desk_01', -8.0, 17.0, 90)
add('teller', 'heist', 'SM_Prop_Seat_01', -9.6, 17.0, 90)
add('teller', 'heist', 'SM_Prop_Shelf_01', 11.6, 17.0, 270)
add('teller', 'heist', 'SM_Prop_Drawers_01', 10.0, 19.0, 0)
add('teller', 'heist', 'SM_Prop_Plant_03', -11.4, 19.0, 0)

# ---------------------------------------------------------------- forecourt dressing
for x in (-9.0, 9.0):
    add('exterior', 'heist', 'SM_Prop_Flag_Pole_01', x, -4.2, 0)
for x in (-3.0, -1.2, 1.2, 3.0):
    add('exterior', 'heist', 'SM_Prop_RopeBarrier_Pole_01', x, -7.2, 0)
for x in (-2.1, 0.0, 2.1):
    add('exterior', 'heist', 'SM_Prop_RopeBarrier_01', x, -7.2, 0, y=0.67)
add('exterior', 'heist', 'SM_Prop_Bin_01', -12.0, -8.0, 0)
add('exterior', 'heist', 'SM_Prop_Bin_01', 12.0, -8.0, 0)
add('exterior', 'heist', 'SM_Veh_Car_Police_Heist_01', -21.0, -6.0, 90)
add('exterior', 'heist', 'SM_Veh_Car_Police_Heist_01', 21.0, -6.0, 270)

# Trees along the forecourt edge and the far sidewalk.
for x in (-33.0, -26.0, 26.0, 33.0):
    add('exterior', 'city', 'SM_Env_Tree_01', x, -5.0, 0)
for x in (-35.0, -25.0, -15.0, 15.0, 25.0, 35.0):
    add('exterior', 'city', 'SM_Env_Tree_02', x, -35.5, 0)

# Street lights along both kerbs.
for x in (-30.0, -15.0, 15.0, 30.0):
    add('exterior', 'city', 'SM_Prop_LightPole_Base_01', x, -10.6, 0)
    add('exterior', 'city', 'SM_Prop_LightPole_Base_01', x, -29.4, 180)

# ---------------------------------------------------------------- street blockade (zone C/E)
add('exterior', 'br', 'SM_Prop_Barrier_04', -8.0, -13.5, 0)
add('exterior', 'br', 'SM_Prop_Barrier_04', 8.0, -13.5, 0)
add('exterior', 'br', 'SM_Prop_Barricade_01', -4.0, -13.5, 20)
add('exterior', 'br', 'SM_Prop_Barricade_01', 4.0, -13.5, 340)
add('exterior', 'br', 'SM_Prop_Barrier_04', -13.6, -13.5, 0)
add('exterior', 'br', 'SM_Prop_Barrier_04', 13.6, -13.5, 0)
add('exterior', 'br', 'SM_Prop_Cinderblock_Wall_01', -17.0, -13.5, 0)
add('exterior', 'br', 'SM_Prop_Cinderblock_Wall_01', 17.0, -13.5, 0)
add('exterior', 'br', 'SM_Prop_Crate_01', -10.5, -15.2, 15)
add('exterior', 'br', 'SM_Prop_Crate_01', 10.5, -15.2, 345)
add('exterior', 'br', 'SM_Prop_Crate_Large_01', -6.2, -16.0, 0)
add('exterior', 'br', 'SM_Prop_Crate_Large_01', 6.2, -16.0, 0)
add('exterior', 'br', 'SM_Prop_Spotlight_01', -20.0, -13.0, 0)
add('exterior', 'br', 'SM_Prop_Spotlight_01', 20.0, -13.0, 0)

# Vehicles holding the blockade.
add('exterior', 'heist', 'SM_Veh_SwatVan_01', -24.0, -18.0, 90)
add('exterior', 'heist', 'SM_Veh_SwatVan_01', 24.0, -18.0, 270)
add('exterior', 'br', 'SM_Veh_Armored_Car_01', -6.0, -24.0, 0)
add('exterior', 'br', 'SM_Veh_Truck_01', 14.0, -27.0, 90)
add('exterior', 'br', 'SM_Prop_AmmoBox_01', -22.6, -19.6, 0)
add('exterior', 'br', 'SM_Prop_Wirespool_01', 21.5, -20.5, 0)

# Flanking city buildings (colliders on, used as street walls).
add('exterior', 'city', 'SM_Bld_OfficeSquare_02', -32.0, 6.0, 0)
add('exterior', 'city', 'SM_Bld_OfficeSquare_02', 32.0, 6.0, 180)
add('exterior', 'city', 'SM_Bld_OfficeSquare_04', -32.0, -47.5, 0)
add('exterior', 'city', 'SM_Bld_OfficeSquare_04', 32.0, -47.5, 180)

# ---------------------------------------------------------------- spawns + cover + kills
SPAWNS = [
    ('exterior', (-12.0, 0.0, -22.0), 1, 'delta'),
    ('exterior', (12.0, 0.0, -22.0), 1, 'delta'),
    ('exterior', (-4.0, 0.0, -30.0), 1, 'recon'),
    ('exterior', (4.0, 0.0, -30.0), 1, 'recon'),
    ('lobby', (-9.0, 0.0, 5.0), 2, 'delta'),
    ('lobby', (9.0, 0.0, 5.0), 2, 'recon'),
    ('lobby', (0.0, 0.0, 9.0), 2, 'recon'),
    ('teller', (0.0, 0.0, 17.5), 2, 'delta'),
]
for rid, p, team, kind in SPAWNS:
    ROOMS[rid]['spawnPoints'].append({
        'position': [p[0], p[1], p[2]], 'team': team, 'type': kind,
    })

COVER = [
    (-24.0, -15.6), (24.0, -15.6), (-8.0, -12.4), (8.0, -12.4),
    (-13.0, -14.4), (13.0, -14.4), (-17.0, -14.4), (17.0, -14.4),
    (-6.0, -22.2), (6.0, -22.4), (-22.6, -20.6), (21.5, -21.4),
    (-30.0, -8.0), (30.0, -8.0), (-10.5, -16.2), (10.5, -16.2),
    (-11.0, 4.0), (11.0, 4.0), (-11.0, 10.0), (11.0, 10.0),
    (-6.0, 11.0), (6.0, 11.0), (0.0, 12.2), (-3.0, 3.2), (3.0, 3.2),
    (-20.0, -26.0), (20.0, -26.0), (-34.0, -33.0), (34.0, -33.0),
    (0.0, -33.0), (-15.0, -31.0), (15.0, -31.0),
]
for x, z in COVER:
    ROOMS['exterior']['coverPoints'].append({'position': [x, 0.0, z]})
ROOMS['lobby']['coverPoints'].append({'position': [0.0, 0.0, 12.0]})

ROOMS['exterior']['killZones'].append({
    'position': [0.0, -5.0, -20.0], 'size': [96.0, 1.0, 48.0],
})
ROOMS['lobby']['killZones'].append({
    'position': [0.0, -6.0, 7.5], 'size': [40.0, 1.0, 40.0],
})

LOS = [
    ('street_to_facade', (0.0, 1.5, -20.0), (0.0, 1.5, -0.6), True),
    ('entrance_open', (0.0, 1.5, -5.0), (0.0, 1.5, 4.0), False),
    ('lobby_to_teller', (8.5, 1.5, 6.0), (8.5, 1.5, 17.5), False),
    ('street_cross', (-14.0, 1.5, -20.0), (14.0, 1.5, -20.0), False),
    ('barrier_cover', (-8.0, 1.2, -12.6), (-8.0, 1.2, -16.0), True),
    ('forecourt_side', (20.0, 1.5, -6.0), (20.0, 1.5, 2.0), False),
]

LAYOUT = {
    'name': 'Street Bank Heist',
    'version': 1,
    'description': 'Kit-built neoclassical bank, forecourt, 20 m road, street blockade.',
    'rooms': [ROOMS[r] for r in ORDER],
    'globalSpawnPoints': None,
    'losChecks': [
        {'name': n, 'from': list(a), 'to': list(b), 'blocked': c} for n, a, b, c in LOS
    ],
    'navMesh': None,
}

# ---------------------------------------------------------------- validation
FAIL = []

FLOOR_TILES = {
    'SM_Env_Sidewalk_01', 'SM_Env_Road_01',
    'SM_Env_Floor_01', 'SM_Env_Floor_02',
}
EXPECT_FLOORS = {'exterior': 132, 'lobby': 15, 'teller': 5}

counts = {r: {'floors': 0, 'ceilings': 0, 'props': 0} for r in ORDER}
for rid in ORDER:
    for p in ROOMS[rid]['props']:
        nm = os.path.basename(p['prefab']).replace('.prefab', '')
        if nm in FLOOR_TILES:
            counts[rid]['floors'] += 1
        elif nm.startswith('SM_Env_Ceiling_'):
            counts[rid]['ceilings'] += 1
        else:
            counts[rid]['props'] += 1

for rid in ORDER:
    if counts[rid]['floors'] != EXPECT_FLOORS[rid]:
        FAIL.append('%s floors=%d expected %d' % (rid, counts[rid]['floors'], EXPECT_FLOORS[rid]))

# Facade ray check: every sample on z = 0 must land on a solid wall module
# except the 5 m entrance gap at ground level.
WALL_MIN_Y, WALL_MAX_Y = 0.0, 3.0
facade = [(fx, fy) for fx, fy, _hw in FACADE]

SAMPLES = 0
SHELL_FAILS = 0
for xi in range(-24, 25):
    x = xi * 0.5
    for y in (0.5, 1.6, 2.5):
        if abs(x) <= 2.4:
            continue
        SAMPLES += 1
        ok = any(abs(x - fx) <= 2.5 and fy <= y <= fy + WALL_MAX_Y for fx, fy in facade)
        if not ok:
            SHELL_FAILS += 1
            if SHELL_FAILS <= 20:
                print('SHELL_MISS x=%.1f y=%.1f' % (x, y))
    for y in (4.0, 5.0, 7.0, 8.0, 10.0, 11.0):
        SAMPLES += 1
        ok = any(abs(x - fx) <= 2.5 and fy <= y <= fy + WALL_MAX_Y for fx, fy in facade)
        if not ok:
            SHELL_FAILS += 1
            if SHELL_FAILS <= 20:
                print('SHELL_MISS x=%.1f y=%.1f' % (x, y))
if SHELL_FAILS:
    FAIL.append('FACADE_SHELL fails=%d of %d' % (SHELL_FAILS, SAMPLES))

# Containment (warn only).
WARN = []
for rid in ORDER:
    mn = ROOMS[rid]['bounds']['min']
    mx = ROOMS[rid]['bounds']['max']
    for p in ROOMS[rid]['props']:
        x, y, z = p['position']
        if not (mn[0] - 6 <= x <= mx[0] + 6 and mn[2] - 6 <= z <= mx[2] + 6):
            WARN.append('%s prop outside bounds: %s at %s' % (rid, os.path.basename(p['prefab']), [x, z]))

# Overlap check on large ground props in the exterior (pairwise AABB).
BIG = []
for rid, name, cx, cz, hw, hd, y in FOOT:
    if rid != 'exterior':
        continue
    if name.startswith(('SM_Env_Sidewalk', 'SM_Env_Road', 'SM_Env_Floor', 'SM_Env_Steps')):
        continue
    if hw >= 1.2 and hd >= 1.2 and y < 0.3:
        BIG.append((name, cx, cz, hw, hd))

OVERLAPS = 0
for i in range(len(BIG)):
    for j in range(i + 1, len(BIG)):
        n1, x1, z1, hw1, hd1 = BIG[i]
        n2, x2, z2, hw2, hd2 = BIG[j]
        if abs(x1 - x2) < hw1 + hw2 - 0.02 and abs(z1 - z2) < hd1 + hd2 - 0.02:
            OVERLAPS += 1
            WARN.append('OVERLAP %s %s at (%.1f,%.1f)' % (n1, n2, x1, z1))

print('ROOMS:', ORDER)
for rid in ORDER:
    print('  %-9s floors=%d ceilings=%d props=%d' % (
        rid, counts[rid]['floors'], counts[rid]['ceilings'], counts[rid]['props']))
print('TOTAL PROPS', sum(len(ROOMS[r]['props']) for r in ORDER))
print('COVER POINTS', sum(len(ROOMS[r]['coverPoints']) for r in ORDER))
print('SPAWNS', sum(len(ROOMS[r]['spawnPoints']) for r in ORDER))
print('LOS CHECKS', len(LOS))
print('FACADE_SAMPLES', SAMPLES, 'FACADE_FAILS', SHELL_FAILS)
print('OVERLAPS', OVERLAPS)

if FAIL:
    for w in WARN:
        print('WARN:', w)
    for f in FAIL:
        print('FAIL:', f)
    raise SystemExit('VALIDATION_FAILED')

for w in WARN:
    print('WARN:', w)

with open(OUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(LAYOUT, f, indent=1)
print('WROTE', OUT_PATH)
print('VALIDATION_OK')
