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


room('exterior', [-70.0, 0.0, -75.0], [70.0, 12.0, 40.0])
room('lobby', [-12.5, 0.0, 0.0], [12.5, 6.0, 15.0])
room('teller', [-12.5, 0.0, 15.0], [12.5, 3.4, 20.0])

TRACK = {}
FOOT = []
GAP = 0.012


def free_row(x, z, half=2.5):
    """True when a 5x5 footprint at (x, z) clears existing ground props."""
    for rid, name, fx, fz, hw, hd, fy in FOOT:
        if rid != 'exterior' or fy > 0.3:
            continue
        if abs(x - fx) < half + hw - 0.02 and abs(z - fz) < half + hd - 0.02:
            return False
    return True


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
# 24 columns x 5 m = 120 m of frontage, build range x -60..60.
GX = tuple(-57.5 + 5.0 * i for i in range(24))
CROSS_X = (-47.5, 47.5)
# Side-street mouths are a full 15 m wide road corridor centred on x = +-47.5.
IN_MOUTH = (42.5, 47.5, 52.5)

for x in GX:
    in_cross = abs(x) in IN_MOUTH
    for z in (-2.5, -7.5):
        if in_cross:
            add('exterior', 'city', 'SM_Env_Road_01', x, z, 90)
        else:
            add('exterior', 'city', 'SM_Env_Sidewalk_01', x, z)
    for z in (-12.5, -17.5, -22.5, -27.5):
        add('exterior', 'city', 'SM_Env_Road_01', x, z)
    for z in (-32.5, -37.5):
        if in_cross:
            add('exterior', 'city', 'SM_Env_Road_01', x, z, 90)
        else:
            add('exterior', 'city', 'SM_Env_Sidewalk_01', x, z)

# Single road tile everywhere: no lane-marking tiles (they read as bold white bars).

for x in (-2.5, 2.5):
    add('exterior', 'city', 'SM_Env_Road_Crossing_01', x, -11.0, 90, y=0.012)
for cx in CROSS_X:
    for x in (cx - 5.0, cx + 5.0):
        if abs(x - cx) > 2.6:
            pass
    add('exterior', 'city', 'SM_Env_Road_Crossing_01', cx, -11.0, 90, y=0.012)

# Back lots: paving behind the bank so the deep blocks stand on real ground.
for x in GX:
    if abs(x) < 15.0:
        continue
    for z in (2.5, 7.5, 12.5, 17.5, 22.5, 27.5):
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

# Portico railings removed: the 5 m glass-infill panels read as loose leaning glass from the street.

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

# Flags on the facade band (reference: four banners above the entrance).
for fx in (-8.5, -4.5, 4.5, 8.5):
    add('exterior', 'heist', 'SM_Prop_Flag_Wall_01', fx, -0.30, 180, y=4.2)
    add('exterior', 'heist', 'SM_Prop_Flag_Wall_02', fx, -0.30, 180, y=4.2)

# Stone planters with shrubs flanking the entrance.
for px in (-4.2, 4.2):
    add('exterior', 'city', 'SM_Prop_Planter_01', px, -1.3, 0, y=0.0)
    add('exterior', 'heist', 'SM_Prop_Plant_02', px, -1.3, 0, y=0.82)

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
# Entrance stanchions only: the red ropes read as floating ribbons, so they stay removed.
# STOP signs flanking the bank entrance (user-requested exception: keep them).
for sx in (-12.0, 12.0):
    add('exterior', 'city', 'SM_Prop_Sign_Stop_01', sx, -3.4, 180)
for x in (-12.0, 12.0):
    add('exterior', 'heist', 'SM_Prop_Bin_01', x, -8.0, 0)
    add('exterior', 'heist', 'SM_Veh_Car_Police_Heist_01', x * 2.05, -6.0, 90 if x < 0 else 270)

# Trees along both kerbs and the far sidewalk.
for x in (-54.0, -42.0, -30.0, 30.0, 42.0, 54.0):
    add('exterior', 'city', 'SM_Env_Tree_01', x, -5.0, 0)
for x in (-52.0, -37.0, -22.0, 22.0, 37.0, 52.0):
    add('exterior', 'city', 'SM_Env_Tree_02', x, -35.5, 0)

# Street lights along both kerbs: arms turn over the road, bases clear of cars.
LIGHT_X = (-53.75, -41.25, -28.75, -16.25, 16.25, 28.75, 41.25, 53.75)
for x in LIGHT_X:
    add('exterior', 'city', 'SM_Prop_LightPole_Base_01', x, -9.4, 180)
    add('exterior', 'city', 'SM_Prop_LightPole_Base_01', x, -30.6, 0)
for x in (-47.5, 47.5):
    add('exterior', 'city', 'SM_Prop_TrafficLight_03', x, -9.2, 180)
    add('exterior', 'city', 'SM_Prop_TrafficLight_03', x, -30.8, 0)

# ---------------------------------------------------------------- street blockade (zone C/E)
# Tiered, broken cordon: low grey blocks and crates with a few tall sandbag bastions,
# a clear centre breach on the line of the bank doors.
add('exterior', 'br', 'SM_Prop_Barricade_01', -3.2, -14.6, 340)
add('exterior', 'br', 'SM_Prop_Barricade_01', 3.2, -14.6, 20)
add('exterior', 'br', 'SM_Prop_Barrier_04', -8.0, -14.6, 0)
add('exterior', 'br', 'SM_Prop_Barrier_04', 8.0, -14.6, 0)

# Wing line: one continuous cinderblock wall (2.5 m modules on a 2.45 m pitch) so the
# cordon reads as a barrier instead of scattered debris. Crates sit tight behind the wall.
WING_X = [13.0 + 2.45 * k for k in range(9)]
for side in (-1, 1):
    for k, wx in enumerate(WING_X):
        px = side * wx
        add('exterior', 'br', 'SM_Prop_Cinderblock_Wall_01', px, -14.6, 0)
        if k % 3 == 1:
            add('exterior', 'br', 'SM_Prop_Crate_Large_01', px, -16.3, 0)
        if k % 3 == 2:
            add('exterior', 'br', 'SM_Prop_Crate_01', px, -16.2, 0)
        if k % 4 == 0:
            add('exterior', 'city', 'SM_Prop_Cone_01', px, -13.5, 0)
        if k % 5 == 2:
            add('exterior', 'br', 'SM_Prop_AmmoBox_01', px + 0.9, -16.4, 0)

for wx in (-28.0, -16.0, 16.0, 28.0):
    add('exterior', 'br', 'SM_Prop_Spotlight_01', wx, -17.0, 0)

# Vehicles holding the blockade and the flanks.
add('exterior', 'heist', 'SM_Veh_SwatVan_01', -25.5, -19.5, 90)
add('exterior', 'heist', 'SM_Veh_SwatVan_01', 25.5, -19.5, 270)
add('exterior', 'heist', 'SM_Veh_SwatVan_01', -39.0, -20.5, 90)
add('exterior', 'heist', 'SM_Veh_SwatVan_01', 39.0, -20.5, 270)
add('exterior', 'br', 'SM_Veh_Armored_Car_01', -11.0, -24.0, 0)
add('exterior', 'br', 'SM_Veh_Armored_Car_01', 33.0, -24.5, 180)
add('exterior', 'br', 'SM_Veh_Truck_01', 47.5, -21.5, 90)
add('exterior', 'br', 'SM_Veh_Truck_01', -47.5, -21.5, 270)
add('exterior', 'br', 'SM_Prop_AmmoBox_01', -22.6, -19.6, 0)
add('exterior', 'br', 'SM_Prop_Wirespool_01', 21.5, -20.5, 0)
add('exterior', 'br', 'SM_Prop_Wirespool_01', -21.5, -21.5, 0)

# Loose crates kept off the carriageway (they read as glitched litter from every angle).
for cx in (-26.0, 26.0):
    add('exterior', 'city', 'SM_Prop_CardboardBox_02', cx, -33.4, 15)

# ---------------------------------------------------------------- tenement frontage
NEAR_SHOPS = ('SM_Bld_Shop_01', 'SM_Bld_Shop_02', 'SM_Bld_Shop_05',
              'SM_Bld_Shop_06', 'SM_Bld_Apartment_Door_01',
              'SM_Bld_Shop_Corner_01', 'SM_Bld_Shop_04')
NEAR_STACKS = ('SM_Bld_Apartment_Stack_01', 'SM_Bld_Apartment_Stack_02',
               'SM_Bld_Apartment_Stack_03')
NEAR_ROOFS = ('SM_Bld_Apartment_Roof_01', 'SM_Bld_Apartment_Roof_02',
              'SM_Bld_Apartment_Roof_03')
COVERS = ('SM_Bld_Shop_Cover_02', 'SM_Bld_Shop_Cover_03', 'SM_Bld_Shop_Cover_01')
UPPER = ('SM_Bld_Apartment_01', 'SM_Bld_Apartment_02', 'SM_Bld_Apartment_03')


def tenement(rid, x, z, rot, i, storeys, shop_row=True):
    add(rid, 'city', NEAR_SHOPS[i % len(NEAR_SHOPS)] if shop_row
        else UPPER[i % 3], x, z, rot, y=0.0)
    add(rid, 'city', NEAR_STACKS[i % 3], x, z, rot, y=3.0)
    top = 12.0
    if storeys >= 4:
        add(rid, 'city', UPPER[i % 3], x, z, rot, y=12.0)
        top = 15.0
    if storeys >= 5:
        add(rid, 'city', UPPER[(i + 1) % 3], x, z, rot, y=15.0)
        top = 18.0
    add(rid, 'city', NEAR_ROOFS[i % 3], x, z, rot, y=top)
    return top


# Near frontage: two blocks per side split by a cross street at x +-47.5.
NEAR_L = (14.6, 19.6, 24.6, 29.6, 34.6, 39.6, 44.6, 52.5, 57.5)
for side in (-1, 1):
    for i, ax in enumerate(NEAR_L):
        x = side * ax
        top = tenement('exterior', x, 2.6, 180, i, 3 + (i % 3))
        if i % 2 == 1:
            add('exterior', 'city', COVERS[i % 3], x, -0.9, 180, y=3.05)
        if i in (1, 4, 7):
            add('exterior', 'city', 'SM_Prop_Phones_01', side * (ax - 1.4), -3.6, 0)

# Deep back row behind the near frontage (left and right of the bank).
for side in (-1, 1):
    for i, ax in enumerate((22.5, 27.5, 32.5, 37.5, 42.5, 52.5, 57.5)):
        tenement('exterior', side * ax, 11.0, 180, i + 2, 4 + (i % 2), shop_row=False)

# Landmark towers behind, visible over the tenement roofs.
for side in (-1, 1):
    add('exterior', 'city', 'SM_Bld_OfficeSquare_01', side * 34.0, 25.0, 0)
    add('exterior', 'city', 'SM_Bld_Spire_01', side * 34.0, 25.0, 0, y=30.0)
    add('exterior', 'city', 'SM_Bld_OfficeOctagon_01', side * 54.0, 24.0, 0)

# Far side of the road: continuous frontage facing the bank.
FAR_SHOPS = ('SM_Bld_Shop_01', 'SM_Bld_Shop_04', 'SM_Bld_Shop_02',
             'SM_Bld_Shop_06', 'SM_Bld_Shop_Corner_01',
             'SM_Bld_Apartment_Door_Corner_01')
FAR_X = tuple(-57.5 + 5.0 * i for i in range(24))
for i, x in enumerate(FAR_X):
    if abs(x) in (47.5,):
        continue
    top = tenement('exterior', x, -42.8, 0, i, 3 + (i % 3))
    if i % 2 == 0:
        add('exterior', 'city', COVERS[i % 3], x, -40.2, 0, y=3.05)

# Third row behind the back row: taller blocks filling both map sides.
for side in (-1, 1):
    for i, ax in enumerate((20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0, 55.0)):
        n = 5 + (i % 2)
        add('exterior', 'city', NEAR_SHOPS[i % len(NEAR_SHOPS)], side * ax, 19.0, 180, y=0.0)
        add('exterior', 'city', NEAR_STACKS[i % 3], side * ax, 19.0, 180, y=3.0)
        add('exterior', 'city', UPPER[i % 3], side * ax, 19.0, 180, y=12.0)
        add('exterior', 'city', UPPER[(i + 1) % 3], side * ax, 19.0, 180, y=15.0)
        add('exterior', 'city', NEAR_ROOFS[i % 3], side * ax, 19.0, 180, y=18.0 if n >= 5 else 15.0)
    add('exterior', 'city', 'SM_Bld_OfficeSquare_03', side * 44.0, 27.0, 0)
    add('exterior', 'city', 'SM_Bld_Spire_01', side * 44.0, 27.0, 0, y=30.0)

# Second far row, backdrop depth and corner blocks around the whole map.
for i, x in enumerate((-50.0, -45.0, -40.0, -35.0, -30.0, -25.0, -20.0, -15.0,
                       -10.0, -5.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0,
                       35.0, 40.0, 45.0, 50.0)):
    tenement('exterior', x, -52.5, 0, i + 1, 4 + (i % 2), shop_row=False)

# Corner blocks: buildings wrapping round into both cross streets and the map edges.
for side in (-1, 1):
    for i, cz in enumerate((9.0, 14.0, 19.0, 24.0)):
        tenement('exterior', side * 57.0, cz, 90 if side > 0 else 270,
                 i + 1, 4 + (i % 2))
    for i, cz in enumerate((-47.0, -52.0)):
        tenement('exterior', side * 57.0, cz, 90 if side > 0 else 270,
                 i + 2, 5, shop_row=False)

for side in (-1, 1):
    add('exterior', 'city', 'SM_Bld_OfficeSquare_03', side * 30.0, -58.0, 0)
    add('exterior', 'city', 'SM_Bld_OfficeOctagon_01', side * 52.0, -59.0, 0)

# Kerbside traffic: mixed models, both kerbs, some cross-street parking.
CARS = (
    (-42.0, 'SM_Veh_Car_Taxi_01', 90), (-35.0, 'SM_Veh_Car_Sedan_01', 90),
    (-28.0, 'SM_Veh_Car_Van_01', 90), (-21.0, 'SM_Veh_Car_Small_01', 90),
    (21.0, 'SM_Veh_Car_Muscle_01', 270), (28.0, 'SM_Veh_Car_Taxi_01', 270),
    (35.0, 'SM_Veh_Car_Van_01', 270), (42.0, 'SM_Veh_Car_Sedan_01', 270),
)
for cx, cname, crot in CARS:
    add('exterior', 'city', cname, cx, -11.9, crot)

FAR_CARS = (
    (-42.0, 'SM_Veh_Car_Sedan_01'), (-34.0, 'SM_Veh_Car_Taxi_01'),
    (-26.0, 'SM_Veh_Car_Small_01'), (-18.0, 'SM_Veh_Car_Van_01'),
    (18.0, 'SM_Veh_Car_Taxi_01'), (26.0, 'SM_Veh_Car_Sedan_01'),
    (34.0, 'SM_Veh_Car_Police_01'), (42.0, 'SM_Veh_Car_Van_01'),
)
for cx, cname in FAR_CARS:
    add('exterior', 'city', cname, cx, -28.6, 270)

# Cross-street mouths: kept clear of vehicles (the enforcement trucks park here).


# Sidewalk furniture along both pedestrian roadsides.
NEAR_SIDE = (-57.5, -53.0, -48.5, -43.0, -38.5, -33.0, -28.5, -23.0,
             -18.5, -15.5, 15.5, 18.5, 23.0, 28.5, 33.0, 38.5, 43.0,
             48.5, 53.0, 57.5)
for i, sx in enumerate(NEAR_SIDE):
    if i % 2 == 0:
        add('exterior', 'city', 'SM_Prop_ParkBench_01', sx, -2.2, 180)
    else:
        add('exterior', 'city', 'SM_Prop_Planter_02', sx, -2.4, 0)
for sx in (-55.0, -45.0, -36.0, -27.0, -17.0, 17.0, 27.0, 36.0, 45.0, 55.0):
    add('exterior', 'city', 'SM_Prop_Trashbin_01', sx, -3.4, 0)
for sx in (-51.0, -41.0, -31.0, -21.0, 21.0, 31.0, 41.0, 51.0):
    add('exterior', 'city', 'SM_Prop_Hydrant_01', sx, -4.2, 0)
for sx in (-39.0, -24.0, 24.0, 39.0):
    add('exterior', 'city', 'SM_Prop_Mailbox_01', sx + 1.9, -0.9, 0)
# Duplicate planter row removed: the row at z -2.4 below already dresses the sidewalk.
# Duplicate phone booth row removed: booths are placed against the frontage by the ax loop.
for sx in (-29.0, -25.5, 25.5, 29.0):
    add('exterior', 'city', 'SM_Prop_Cone_02', sx, -9.4, 0)
for sx in (-3.6, 3.6):
    add('exterior', 'city', 'SM_Prop_TrafficLight_03', sx, -11.2, 180)
for sx in (-6.0, -4.5, 4.5, 6.0):
    add('exterior', 'city', 'SM_Prop_Cone_01', sx, -11.6, 0)
# Stop signs removed from the bank forecourt: they belong at junctions, not on a plaza.
for sx in (-36.5, 36.5):
    add('exterior', 'city', 'SM_Prop_BusStop_01', sx, -3.9, 180)


for sx in (-54.0, -44.0, -34.0, -24.0, 24.0, 34.0, 44.0, 54.0):
    add('exterior', 'city', 'SM_Prop_ParkBench_01', sx, -2.2, 180)
for sx in (-56.5, -46.5, -31.5, -26.5, 26.5, 31.5, 46.5, 56.5):
    add('exterior', 'city', 'SM_Prop_Hydrant_01', sx, -4.2, 0)
for sx in (-36.5, -16.5, 16.5, 36.5):
    add('exterior', 'city', 'SM_Prop_Mailbox_01', sx + 1.9, -0.9, 0)
for sx in (-38.5, -18.5, 18.5, 38.5, -57.5, 57.5):
    add('exterior', 'city', 'SM_Prop_Trashbin_01', sx, -3.2, 0)
for sx in (-32.0, -20.0, 20.0, 32.0):
    add('exterior', 'city', 'SM_Prop_Planter_01', sx, -3.1, 0)
for sx in (-25.0, 25.0):
    add('exterior', 'city', 'SM_Prop_Cone_01', sx, -9.2, 0)
for sx in (-48.0, 48.0):
    add('exterior', 'city', 'SM_Prop_BusStop_01', sx, -35.6, 0)
for sx in (-3.6, 3.6):
    add('exterior', 'city', 'SM_Prop_TrafficLight_03', sx, -11.2, 180)
for sx in (-6.0, -4.5, 4.5, 6.0):
    add('exterior', 'city', 'SM_Prop_Cone_01', sx, -11.6, 0)

# Far-side furniture, signage and the fenced pocket park.
for i, sx in enumerate((-57.5, -51.0, -45.0, -39.0, -33.0, -27.0, -21.0, -15.5,
                        15.5, 21.0, 27.0, 33.0, 39.0, 45.0, 51.0, 57.5)):
    if i % 2 == 0:
        add('exterior', 'city', 'SM_Prop_ParkBench_01', sx, -33.6, 0)
    else:
        add('exterior', 'city', 'SM_Prop_Trashbin_02', sx, -34.0, 180)
for sx in (-48.0, -36.0, -24.0, 24.0, 36.0, 48.0):
    add('exterior', 'city', 'SM_Prop_Planter_01', sx, -32.6, 180)
for sx in (-42.0, -30.0, 30.0, 42.0):
    add('exterior', 'city', 'SM_Prop_Hydrant_01', sx, -34.8, 180)
for sx in (-18.0, 18.0):
    add('exterior', 'city', 'SM_Prop_Mailbox_01', sx + 1.9, -34.8, 180)
for sx in (-9.0, 9.0):
    add('exterior', 'city', 'SM_Prop_TrashCan_01', sx, -33.0, 0)
for x in (-12.5, -7.5, 7.5, 12.5):
    add('exterior', 'city', 'SM_Env_Fence_01', x, -39.7, 0, y=0.0)
for x in (-10.0, 10.0):
    add('exterior', 'city', 'SM_Env_Fence_End_01', x, -39.7, 0)
for x in (-10.5, 10.5):
    add('exterior', 'city', 'SM_Prop_ParkBench_01', x, -37.4, 180)
for x in (-9.5, 9.5):
    add('exterior', 'city', 'SM_Env_Tree_03', x, -37.2, 0)

# ================================================================ exterior expansion (iteration 2)
# --- side-street canyons: continuous walls down both cross streets (x = +-57)
for side in (-1, 1):
    for i, cz in enumerate((-6.0, -11.0, -16.0, -21.0, -26.0, -31.0, -36.0)):
        tenement('exterior', side * 57.0, cz, 90 if side < 0 else 270, i + 1, 3 + (i % 3))

# --- skyline behind the bank so the top edge of the map is built up
for side in (-1, 1):
    for i, ax in enumerate((17.5, 22.5, 27.5, 32.5, 37.5, 42.5, 47.5, 52.5)):
        tenement('exterior', side * ax, 27.0, 180, i + 2, 4 + (i % 2), shop_row=False)
    add('exterior', 'city', 'SM_Bld_Spire_01', side * 22.0, 33.0, 0)
    add('exterior', 'city', 'SM_Bld_Spire_01', side * 46.0, 33.0, 0)

# --- rooftop dressing so roofs read as working buildings, not empty slabs
ROOF_SPOTS = (14.6, 29.6, 44.6)
for side in (-1, 1):
    for i, ax in enumerate(ROOF_SPOTS):
        bx = side * ax
        add('exterior', 'city', 'SM_Prop_Water_Tower_01', bx - 1.2, 3.2, 0, y=12.78)
        add('exterior', 'city', 'SM_Bld_Roof_Access_01', bx + 1.6, 3.4, 0, y=12.74)
        add('exterior', 'city', 'SM_Prop_Roof_Aircon_02', bx + 0.9, 1.5, 0, y=12.74)
        add('exterior', 'city', 'SM_Prop_Vents_Straight_01', bx - 0.9, 4.6, 0, y=12.74)
    for i, ax in enumerate((19.6, 34.6, 49.6)):
        add('exterior', 'city', 'SM_Prop_Roof_Aircon_03', side * ax, 3.9, 0, y=15.74)
        add('exterior', 'city', 'SM_Prop_Vents_End_01', side * (ax + 1.4), 2.2, 0, y=15.74)

# --- hanging blade signs + flat shopfront signs on the near row
BLADES = ('SM_Prop_LargeSign_Pizza_01', 'SM_Prop_LargeSign_Burger_01', 'SM_Prop_LargeSign_Coffee_01',
          'SM_Prop_LargeSign_Donut_01', 'SM_Prop_LargeSign_Taco_01', 'SM_Prop_LargeSign_Hotdog_01',
          'SM_Prop_LargeSign_Milkshake_01', 'SM_Prop_LargeSign_Guitar_01')
FLATS = ('SM_Prop_Sign_Pizza_01', 'SM_Prop_Sign_Cafe_01', 'SM_Prop_Sign_Bar_01', 'SM_Prop_Sign_Pub_01',
         'SM_Prop_Sign_Barber_01', 'SM_Prop_Sign_Hotel_01', 'SM_Prop_Sign_XXX_01', 'SM_Prop_Sign_Parking_01')
for side in (-1, 1):
    for i, ax in enumerate((15.4, 20.4, 25.4, 30.4, 35.4, 40.4, 45.4, 51.0)):
#         add('exterior', 'city', 'SM_Prop_Sign_Attachment_01', side * ax, -0.55, 180 if side > 0 else 0, y=5.65)
#         add('exterior', 'city', BLADES[i % len(BLADES)], side * ax, -1.85, 180 if side > 0 else 0, y=4.55)
        add('exterior', 'city', FLATS[(i + 3) % len(FLATS)], side * ax, -0.22, 180 if side > 0 else 0, y=3.35)

# --- second lane + stopped approach queue (kept clear of the armoured cars)
add('exterior', 'city', 'SM_Veh_Car_Taxi_01', -5.6, -18.6, 20)
add('exterior', 'city', 'SM_Veh_Car_Police_01', 5.6, -18.9, 200)
add('exterior', 'city', 'SM_Veh_Car_Van_01', -2.0, -30.8, 15)
add('exterior', 'city', 'SM_Veh_Car_Sedan_01', 6.4, -31.2, 195)

# --- enforcement cover on both wings: containers, barrier clusters, tank traps
for side in (-1, 1):
    add('exterior', 'br', 'SM_Prop_Container_01', side * 32.0, -17.2, 90)
    add('exterior', 'br', 'SM_Prop_Container_Small_01', side * 44.0, -18.6, 90)
    add('exterior', 'br', 'SM_Prop_Barrier_01', side * 20.6, -16.2, 0)
    add('exterior', 'br', 'SM_Prop_Barrier_02', side * 21.9, -16.2, 0)
    add('exterior', 'br', 'SM_Prop_Barrier_03', side * 36.6, -16.4, 0)
    add('exterior', 'br', 'SM_Prop_TankTrap_01', side * 25.4, -16.0, 25)
    add('exterior', 'br', 'SM_Prop_TankTrap_01', side * 41.2, -16.2, 335)
    # Loose drop crates and cardboard boxes removed from the cordon rear: they read as litter.

# --- pedestrian detail: parking meters, newspaper boxes, bags, manholes, patches, bay lines
for x in (-50.0, -42.0, -34.0, -26.0, -18.0, 18.0, 26.0, 34.0, 42.0, 50.0):
    add('exterior', 'city', 'SM_Prop_ParkingMeter_01', x, -10.9, 0)
    add('exterior', 'city', 'SM_Prop_Newspaper_02', x + 2.4, -0.9, 180 if x > 0 else 0)
    add('exterior', 'city', 'SM_Prop_TrashBag_0%d' % (1 + (int(abs(x)) % 3)), x - 2.2, -0.9, 0)
for x in (-38.0, -12.0, 12.0, 38.0):
    add('exterior', 'city', 'SM_Prop_Manhole_01', x, -18.0, 0, y=0.01)
    add('exterior', 'city', 'SM_Prop_Manhole_02', x + 3.0, -25.0, 0, y=0.01)
for z in (-14.5, -21.5):
    add('exterior', 'city', 'SM_Env_Road_Patch_01', -22.0, z, 12, y=0.005)
    add('exterior', 'city', 'SM_Env_Road_Patch_01', 26.0, z, 340, y=0.005)
for x in (-52.5, -42.5, -32.5, -22.5, 22.5, 32.5, 42.5, 52.5):
    add('exterior', 'city', 'SM_Env_Road_ParkingLines_01', x, -13.9, 0, y=0.006)
    add('exterior', 'city', 'SM_Env_Road_ParkingLines_01', x, -26.6, 0, y=0.006)
for side in (-1, 1):
    add('exterior', 'city', 'SM_Prop_Sign_GiveWay_01', side * 45.6, -10.9, 180)
    add('exterior', 'city', 'SM_Prop_Sign_Street_01', side * 44.8, -2.2, 0, y=2.6)
    add('exterior', 'city', 'SM_Prop_Cone_01', side * 33.0, -9.6, 0)
    add('exterior', 'city', 'SM_Prop_Cone_02', side * 34.2, -9.9, 0)


# ---------------------------------------------------------------- facade relief + kerbside litter
# Pilasters on the bank's upper facade so the hero block is not a blank slab.
for px in (-11.5, -8.5, 8.5, 11.5):
    for py in (6.0, 9.0):
        add('exterior', 'heist', 'SM_Env_Pillar_Exterior_04', px, -0.28, 0, y=py)
# Deeper projecting cornice over the existing roof edge.
for cx in (-10.0, -5.0, 0.0, 5.0, 10.0):
    add('exterior', 'heist', 'SM_Env_Roof_05', cx, -0.35, 0, y=11.95)
# Boxes moved off the carriageway onto the far sidewalk.
for bx in (-26.0, 26.0):
    add('exterior', 'city', 'SM_Prop_CardboardBox_02', bx, -33.4, 0)
# Building mass filling the empty strip directly behind the bank.
for bx in (-12.5, -7.5, -2.5, 2.5, 7.5, 12.5):
    tenement('exterior', bx, 25.0, 180, 2, 4, shop_row=False)
for bx in (-10.0, 0.0, 10.0):
    tenement('exterior', bx, 31.0, 180, 3, 5, shop_row=False)
add('exterior', 'city', 'SM_Bld_Spire_01', 0.0, 35.0, 0)

# ---------------------------------------------------------------- outer city grid
# One extra tall column per side, one module beyond the existing x +-59.5 row.
for side in (-1, 1):
    rot = 90 if side > 0 else 270
    for i, z in enumerate(-57.5 + 5.0 * k for k in range(18)):
        x = side * 65.0
        if free_row(x, z):
            tenement('exterior', x, z, rot, i + 3, 5, shop_row=False)

# Two extra rows closing the bottom of the map, skipping landmark footprints.
for ri, z in enumerate((-64.5, -69.5)):
    for i, x in enumerate(FAR_X):
        if free_row(x, z):
            tenement('exterior', x, z, 0, i + ri + 5, 5, shop_row=False)

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
    ('street_to_facade', (8.0, 1.5, -20.0), (8.0, 1.5, -0.6), True),
    ('entrance_open', (0.0, 1.5, -5.0), (0.0, 1.5, 4.0), False),
    ('lobby_to_teller', (8.5, 1.5, 6.0), (8.5, 1.5, 17.5), False),
    ('street_cross', (-14.0, 1.5, -20.0), (14.0, 1.5, -20.0), False),
    ('barrier_cover', (-8.0, 1.2, -12.6), (-8.0, 1.2, -16.0), True),
    ('forecourt_cross', (-20.0, 1.5, -8.6), (20.0, 1.5, -8.6), False),
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
EXPECT_FLOORS = {'lobby': 15, 'teller': 5}

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
    if rid in EXPECT_FLOORS and counts[rid]['floors'] != EXPECT_FLOORS[rid]:
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
