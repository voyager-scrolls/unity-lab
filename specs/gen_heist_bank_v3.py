# gen_heist_bank_v3.py - "next level" bank design: 6m grand lobby, wall-mounted fixtures,
# surface-stacked valuables, coplanar-safe placement. Run: py -3 specs/gen_heist_bank_v3.py
#
# Design rules (all enforced by the validator before shipping):
#  - 5m kit grid: wall runs sum exactly to room spans
#  - Exterior shell is 6m (two 3m courses); lobby is open to 6m; service rooms have 3m suspended ceilings
#  - Wall fixtures mounted via measured rotated AABB; back face flush to wall plane (+12mm gap, no z-fighting)
#  - Valuables placed ON/IN surfaces (display-case interiors, desk tops, trolley tops) - never floating
#  - Flat overlays (rugs, signs, blinds) lifted 12mm off their host face to prevent z-fighting
#  - Furniture footprints derived from catalog bmin/bmax (pivot-correct), checked for containment + overlap
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT_PATH = os.path.join(ROOT, 'specs', 'heist-catalog.json')
OUT_PATH = os.path.join(ROOT, 'specs', 'heist-bank-v3.json')
GAP = 0.012  # surface overlay gap: kills coplanar z-fighting

with io.open(CAT_PATH, encoding='utf-8') as f:
    CATALOG = json.load(f)
BY = {}
for e in CATALOG:
    BY.setdefault(e['name'], e)


def P(name):
    e = BY.get(name)
    if e is None:
        raise SystemExit('MISSING PREFAB: ' + name)
    return e


def sz(name):
    b = P(name)['bounds']
    return (b['max'][0] - b['min'][0], b['max'][1] - b['min'][1], b['max'][2] - b['min'][2])


def rot_box(name, rot):
    """Rotated local AABB (dx0, dx1, dz0, dz1, dy0, dy1) relative to pivot, rot in {0,90,180,270}."""
    b = P(name)['bounds']
    x0, x1, z0, z1 = b['min'][0], b['max'][0], b['min'][2], b['max'][2]
    y0, y1 = b['min'][1], b['max'][1]
    r = int(round(rot)) % 360
    if r == 0:
        return x0, x1, z0, z1, y0, y1
    if r == 180:
        return -x1, -x0, -z1, -z0, y0, y1
    if r == 90:
        return z0, z1, -x1, -x0, y0, y1
    return -z1, -z0, x0, x1, y0, y1  # 270


ROOMS = {
    'exterior':  {'min': [-20, 0, -25], 'max': [20, 6, 0], 'h': 0},
    'lobby':     {'min': [-12.5, 0, 0], 'max': [12.5, 6, 10], 'h': 6},
    'teller':    {'min': [-12.5, 0, 10], 'max': [12.5, 3, 15], 'h': 3},
    'vault':     {'min': [-7.5, 0, 15], 'max': [7.5, 3, 25], 'h': 3},
    'corridorL': {'min': [-12.5, 0, 15], 'max': [-7.5, 3, 25], 'h': 3},
    'corridorR': {'min': [7.5, 0, 15], 'max': [12.5, 3, 25], 'h': 3},
}
for r in ROOMS.values():
    r['id'] = None
    r['props'] = []
    r['spawnPoints'] = []
    r['killZones'] = []

TRACK = {}  # placement registry: key -> {room, name, x, y, z, rot, top}


def _emit(room, name, x, y, z, rot, extra=None):
    p = {'prefab': P(name)['path'],
         'position': [round(x, 4), round(y, 4), round(z, 4)],
         'rotation': [0.0, float(int(round(rot)) % 360), 0.0],
         'scale': [1.0, 1.0, 1.0]}
    if extra:
        p.update(extra)
    ROOMS[room]['props'].append(p)
    return p


def add(room, name, x, z, rot=0.0, y=None, key=None):
    """Place on the floor by default (bottom at y=0), exact pivot-aware."""
    _, _, _, _, _, _ = (0, 0, 0, 0, 0, 0)
    if y is None:
        y = -P(name)['bounds']['min'][1]
    p = _emit(room, name, x, y, z, rot)
    if key:
        TRACK[key] = {'room': room, 'name': name, 'x': x, 'y': y, 'z': z, 'rot': rot,
                      'top': y + P(name)['bounds']['max'][1]}
    return p


def add_on(room, key, name, dx, dz, rot=0.0, lift=0.0):
    """Stack onto a tracked host surface (top of host), offset dx/dz in world axes."""
    h = TRACK[key]
    y = h['top'] - P(name)['bounds']['min'][1] + lift + GAP
    p = _emit(room, name, h['x'] + dx, y, h['z'] + dz, rot, {'surface': True})
    return p


def add_mount(room, name, axis, plane, room_dir, u, h, rot):
    """Mount a fixture flush to a wall plane. axis 'z' or 'x'; room_dir is the side the room is on."""
    dx0, dx1, dz0, dz1, dy0, dy1 = rot_box(name, rot)
    if axis == 'z':
        x = u
        if room_dir > 0:
            z = plane + GAP - dz0
        else:
            z = plane - GAP - dz1
    else:
        z = u
        if room_dir > 0:
            x = plane + GAP - dx0
        else:
            x = plane - GAP - dx1
    y = h - dy0
    _emit(room, name, x, y, z, rot, {'mounted': True})
    return {'x': x, 'y': y, 'z': z, 'rot': rot, 'name': name, 'axis': axis, 'plane': plane, 'room_dir': room_dir}


MOUNTED = []

# ------------------------------------------------------------------ floors (5m kit)
FLOOR_A, FLOOR_B = 'SM_Env_Floor_01', 'SM_Env_Floor_02'


def room_at(x, z):
    for rid in ('lobby', 'teller', 'vault', 'corridorL', 'corridorR', 'exterior'):
        b = ROOMS[rid]
        if b['min'][0] <= x <= b['max'][0] and b['min'][2] <= z <= b['max'][2]:
            return rid
    raise SystemExit('no room for %s,%s' % (x, z))


for x in (-10, -5, 0, 5, 10):
    for z in (2.5, 7.5, 12.5):
        add(room_at(x, z), FLOOR_A if (round(x) + round(z)) % 10 == 0 else FLOOR_B, x, z)
for x in (-5, 0, 5):
    for z in (17.5, 22.5):
        add('vault', FLOOR_A if (x + z) % 10 == 0 else FLOOR_B, x, z)
for x in (-10, 10):
    for z in (17.5, 22.5):
        add('corridorL' if x < 0 else 'corridorR',
            FLOOR_A if (x + z) % 10 == 0 else FLOOR_B, x, z)
for x in (-17.5, -12.5, -7.5, -2.5, 2.5, 7.5, 12.5, 17.5):
    for z in (-2.5, -7.5, -12.5, -17.5, -22.5):
        add('exterior', FLOOR_A if (round(x) + round(z)) % 10 == 0 else FLOOR_B, x, z)

# ------------------------------------------------------------------ ceilings (bottom at room height)
CEILINGS = ['SM_Env_Ceiling_01', 'SM_Env_Ceiling_02', 'SM_Env_Ceiling_03',
            'SM_Env_Ceiling_04', 'SM_Env_Ceiling_05']
ci = 0
for x in (-10, -5, 0, 5, 10):
    for z in (2.5, 7.5):
        add('lobby', CEILINGS[ci % len(CEILINGS)], x, z, y=6.0 - P(CEILINGS[ci % len(CEILINGS)])['bounds']['min'][1])
        ci += 1
for x in (-10, -5, 0, 5, 10):
    for z in (12.5, 17.5, 22.5):
        rid = room_at(x, z)
        n = CEILINGS[ci % len(CEILINGS)]
        add(rid, n, x, z, y=3.0 - P(n)['bounds']['min'][1])
        ci += 1

# ------------------------------------------------------------------ walls (two 3m courses)
W_EXT = 'SM_Env_Wall_Exterior_01'
W_EXT_WIN = 'SM_Env_Wall_Exterior_Window_01'
W_EXT_DD = 'SM_Env_Wall_Exterior_DoubleDoor_01'
W_INT = 'SM_Env_Wall_Interior_01'
W_INT_WIN = 'SM_Env_Wall_Interior_Window_01'
W_INT_DOOR = 'SM_Env_Wall_Interior_Door_01'
V_FRAME = 'SM_Env_VaultDoor_Frame_01'
V_WALL = 'SM_Env_VaultGate_Wall_01'


def wall(room, name, x, z, rot, course):
    add(room, name, x, z, rot, y=course * 3.0 - P(name)['bounds']['min'][1])


# facade Z=0: entry centre, windows lower + upper courses
for x, n in ((-10, W_EXT_WIN), (-5, W_EXT_WIN), (0, W_EXT_DD), (5, W_EXT_WIN), (10, W_EXT_WIN)):
    wall('lobby', n, x, 0.0, 0.0, 0)
for x, n in ((-10, W_EXT_WIN), (-5, W_EXT_WIN), (0, W_EXT), (5, W_EXT_WIN), (10, W_EXT_WIN)):
    wall('lobby', n, x, 0.0, 0.0, 1)
# back Z=25: two courses (6m shell)
for x in (-10, -5, 0, 5, 10):
    wall(room_at(x, 24.9), W_EXT, x, 25.0, 180.0, 0)
    wall(room_at(x, 24.9), W_EXT, x, 25.0, 180.0, 1)
# sides X=+-12.5: two courses
for z in (2.5, 7.5, 12.5, 17.5, 22.5):
    rid = room_at(-12.4, z)
    wall(rid, W_EXT_WIN if z == 7.5 else W_EXT, -12.5, z, 90.0, 0)
    wall(rid, W_EXT, -12.5, z, 90.0, 1)
for z in (2.5, 7.5, 12.5, 17.5, 22.5):
    rid = room_at(12.4, z)
    wall(rid, W_EXT_WIN if z == 7.5 else W_EXT, 12.5, z, 270.0, 0)
    wall(rid, W_EXT, 12.5, z, 270.0, 1)
# lobby/teller wall Z=10: openings lower, solid upper (lobby is 6m)
for x, n in ((-10, W_INT_DOOR), (-5, W_INT_WIN), (0, W_INT_WIN), (5, W_INT_WIN), (10, W_INT_DOOR)):
    wall('teller', n, x, 10.0, 0.0, 0)
for x in (-10, -5, 0, 5, 10):
    wall('lobby', W_INT, x, 10.0, 0.0, 1)
# teller/vault wall Z=15
for x, n, r in ((-10, W_INT_DOOR, 'corridorL'), (-5, V_WALL, 'vault'), (0, V_FRAME, 'vault'),
                (5, V_WALL, 'vault'), (10, W_INT_DOOR, 'corridorR')):
    wall(r, n, x, 15.0, 0.0, 0)
# vault side walls
for z in (17.5, 22.5):
    wall('vault', V_WALL, -7.5, z, 90.0, 0)
    wall('vault', V_WALL, 7.5, z, 270.0, 0)

# ------------------------------------------------------------------ lobby (6m grand hall)
add('lobby', 'SM_Prop_Rug_01', 0.0, 4.5, 0.0, y=GAP)
add('lobby', 'SM_Prop_Statue_01', 0.0, 1.6, 180.0)
add('lobby', 'SM_Prop_Couch_01', -8.0, 2.0, 90.0)
add('lobby', 'SM_Prop_Couch_02', 8.0, 2.0, 270.0)
add('lobby', 'SM_Prop_Couch_01', -8.0, 8.0, 90.0)
add('lobby', 'SM_Prop_Couch_02', 8.0, 8.0, 270.0)
add('lobby', 'SM_Prop_CoffeTable_01', -6.2, 2.0, 0.0)
add('lobby', 'SM_Prop_CoffeeTable_02', 6.2, 2.0, 0.0)
add('lobby', 'SM_Prop_Plant_01', -11.4, 1.2, 0.0)
add('lobby', 'SM_Prop_Plant_02', 11.4, 1.2, 0.0)
add('lobby', 'SM_Prop_Plant_03', -11.4, 9.0, 0.0)
add('lobby', 'SM_Prop_Plant_01', 11.4, 9.0, 0.0)
add('lobby', 'SM_Prop_ATM_01', -12.0, 5.5, 90.0)
add('lobby', 'SM_Prop_ATM_01', 12.0, 5.5, 270.0)
add('lobby', 'SM_Prop_Pillar_01', -5.0, 5.0, 0.0)
add('lobby', 'SM_Prop_Pillar_01', 5.0, 5.0, 0.0)
add('lobby', 'SM_Prop_WaterCooler_01', 11.4, 6.8, 270.0)
add('lobby', 'SM_Prop_Bin_01', -11.4, 6.8, 0.0)
for px in (-3.0, -1.2, 1.2, 3.0):
    add('lobby', 'SM_Prop_RopeBarrier_Pole_01', px, 1.2, 0.0)
# display cases flanking the entrance, jewellery presented inside the glass
add('lobby', 'SM_Prop_DisplayCase_01', -9.0, 1.6, 90.0, key='caseL1')
add('lobby', 'SM_Prop_Jewellery_01', -9.0, 1.45, 0.0, key='jL1', y=0.80)
add('lobby', 'SM_Prop_Jewellery_02', -9.0, 1.6, 0.0, key='jL2', y=0.80)
add('lobby', 'SM_Prop_Jewellery_Ring_01', -9.0, 1.75, 0.0, key='jL3', y=0.80)
add('lobby', 'SM_Prop_DisplayCase_02', 9.0, 1.6, 270.0, key='caseR1')
add('lobby', 'SM_Prop_Jewellery_03', 9.0, 1.45, 0.0, key='jR1', y=0.52)
add('lobby', 'SM_Prop_Jewellery_Necklace_01', 9.0, 1.65, 0.0, key='jR2', y=0.52)
add('lobby', 'SM_Prop_Jewellery_Rings_01', 9.0, 1.8, 0.0, key='jR3', y=0.52)
# wall fixtures
MOUNTED.append(add_mount('lobby', 'SM_Prop_Sign_Bank_01', 'z', 10.0, -1, 0.0, 3.3, 180.0))
MOUNTED.append(add_mount('lobby', 'SM_Prop_Camera_01', 'z', 0.0, 1, -9.5, 2.9, 180.0))
MOUNTED.append(add_mount('lobby', 'SM_Prop_Camera_01', 'z', 0.0, 1, 9.5, 2.9, 180.0))
MOUNTED.append(add_mount('lobby', 'SM_Prop_Camera_01', 'x', -12.5, 1, 5.0, 2.9, 90.0))
MOUNTED.append(add_mount('lobby', 'SM_Prop_AlarmButton_01', 'z', 10.0, -1, 9.2, 1.2, 180.0))
for wx in (-10, -5, 5, 10):
    MOUNTED.append(add_mount('lobby', 'SM_Env_Wall_Window_Blinds_01', 'z', 0.0, 1, wx, 0.87, 0.0))

# ------------------------------------------------------------------ teller (3m suspended ceiling)
for x in (-6.0, -2.0, 2.0, 6.0):
    add('teller', 'SM_Prop_TellerDesk_01', x, 11.8, 180.0, key='desk%d' % int(x * 10))
    add('teller', 'SM_Prop_TellerDesk_Barrier_01', x, 10.45, 180.0)
    add('teller', 'SM_Prop_Seat_01', x, 13.0, 180.0)
    k = 'desk%d' % int(x * 10)
    add_on('teller', k, 'SM_Prop_Computer_01', 0.0, 0.0, 180.0)
    add_on('teller', k, 'SM_Prop_Computer_Screen_01', 0.0, -0.1, 180.0, lift=0.18)
    add_on('teller', k, 'SM_Prop_Computer_Keyboard_01', 0.0, -0.45, 180.0)
    add_on('teller', k, 'SM_Prop_Money_Stack_01', -0.6, 0.2, 15.0)
    add_on('teller', k, 'SM_Prop_Money_Stack_02', 0.55, 0.25, 200.0)
    add_on('teller', k, 'SM_Prop_Folder_01', 0.75, -0.2, 90.0)
    add_on('teller', k, 'SM_Prop_DeskLight_01', -0.9, -0.35, 180.0)
add('teller', 'SM_Prop_Shelf_01', 11.4, 12.0, 270.0)
add('teller', 'SM_Prop_Drawers_01', -11.4, 12.0, 90.0)
add('teller', 'SM_Prop_DisplayCase_01', -10.5, 14.5, 0.0, key='tcase1')
add('teller', 'SM_Prop_Jewellery_Necklace_02', -10.7, 14.5, 0.0, y=0.80)
add('teller', 'SM_Prop_Jewellery_04', -10.3, 14.5, 0.0, y=0.80)
add('teller', 'SM_Prop_DisplayCase_02', 10.5, 14.5, 0.0, key='tcase2')
add('teller', 'SM_Prop_Jewellery_02', 10.3, 14.5, 0.0, y=0.52)
add('teller', 'SM_Prop_Jewellery_Ring_01', 10.7, 14.5, 0.0, y=0.52)
MOUNTED.append(add_mount('teller', 'SM_Prop_Camera_01', 'z', 15.0, -1, -8.0, 2.6, 0.0))
MOUNTED.append(add_mount('teller', 'SM_Prop_AirVent_01', 'z', 15.0, -1, 8.0, 2.6, 0.0))
MOUNTED.append(add_mount('teller', 'SM_Prop_AlarmButton_01', 'z', 10.0, 1, 9.2, 1.2, 0.0))

# ------------------------------------------------------------------ vault (3m)
for z in (17.5, 22.5):
    pass
MOUNTED.append(add_mount('vault', 'SM_Prop_SafeDepositBoxes_01', 'x', -7.5, 1, 17.5, 0.0, 270.0))
MOUNTED.append(add_mount('vault', 'SM_Prop_SafeDepositBoxes_01', 'x', 7.5, -1, 22.5, 0.0, 90.0))
add('vault', 'SM_Prop_Table_01', 0.0, 20.0, 0.0, key='vtable')
add_on('vault', 'vtable', 'SM_Prop_GoldBar_01', -0.6, 0.0, 20.0)
add_on('vault', 'vtable', 'SM_Prop_GoldBar_02', -0.2, 0.05, 65.0)
add_on('vault', 'vtable', 'SM_Prop_GoldBar_01', 0.25, 0.0, 340.0)
add_on('vault', 'vtable', 'SM_Prop_Money_Stack_01', 0.8, 0.0, 15.0)
add_on('vault', 'vtable', 'SM_Prop_Drill_01', -1.2, 0.0, 90.0)
add_on('vault', 'vtable', 'SM_Item_Crowbar_01', 1.2, 0.1, 80.0)
add('vault', 'SM_Prop_VaultTrolley_01', 3.2, 21.0, 0.0, key='vtrolley')
add_on('vault', 'vtrolley', 'SM_Prop_Money_Stack_02', 0.0, 0.0, 0.0)
add_on('vault', 'vtrolley', 'SM_Prop_Money_Stack_03', 0.3, 0.2, 40.0)
add('vault', 'SM_Item_DuffleBag_Full_01', -3.4, 18.2, 270.0)
add('vault', 'SM_Item_DuffleBag_Open_Empty_01', -4.2, 21.5, 90.0)
MOUNTED.append(add_mount('vault', 'SM_Prop_Camera_01', 'z', 25.0, -1, 0.0, 2.6, 0.0))
MOUNTED.append(add_mount('vault', 'SM_Prop_AirVent_01', 'x', -7.5, 1, 20.0, 2.6, 90.0))

# ------------------------------------------------------------------ corridors / offices
add('corridorL', 'SM_Prop_Desk_01', -10.0, 17.0, 90.0, key='ldesk')
add('corridorL', 'SM_Prop_Seat_01', -8.6, 17.0, 270.0)
add_on('corridorL', 'ldesk', 'SM_Prop_Computer_01', 0.0, 0.3, 90.0)
add_on('corridorL', 'ldesk', 'SM_Prop_Computer_Screen_01', 0.15, 0.3, 90.0, lift=0.18)
add_on('corridorL', 'ldesk', 'SM_Prop_Folder_02', -0.4, -0.2, 90.0)
add('corridorL', 'SM_Prop_Shelf_01', -12.0, 20.0, 90.0)
add('corridorL', 'SM_Prop_Drawers_01', -10.0, 23.0, 0.0)
add('corridorL', 'SM_Prop_Plant_02', -8.8, 23.6, 0.0)
MOUNTED.append(add_mount('corridorL', 'SM_Prop_Camera_01', 'x', -12.5, 1, 22.0, 2.6, 90.0))
add('corridorR', 'SM_Prop_Desk_02', 10.0, 17.0, 270.0, key='rdesk')
add('corridorR', 'SM_Prop_Seat_01', 8.6, 17.0, 90.0)
add_on('corridorR', 'rdesk', 'SM_Prop_Computer_01', 0.0, 0.3, 270.0)
add_on('corridorR', 'rdesk', 'SM_Prop_Folder_03', 0.4, -0.2, 270.0)
add('corridorR', 'SM_Prop_Shelf_01', 12.0, 20.0, 270.0)
add('corridorR', 'SM_Prop_WaterCooler_01', 8.4, 23.4, 0.0)
add('corridorR', 'SM_Prop_Drawers_01', 10.0, 23.0, 0.0)
MOUNTED.append(add_mount('corridorR', 'SM_Prop_Camera_01', 'x', 12.5, -1, 22.0, 2.6, 270.0))

# ------------------------------------------------------------------ exterior
add('exterior', 'SM_Env_Pillar_Exterior_Floor_01', -14.5, -3.0, 0.0)
add('exterior', 'SM_Env_Pillar_Exterior_Floor_01', 14.5, -3.0, 0.0)
add('exterior', 'SM_Env_Pillar_Exterior_Floor_01', -14.5, -9.0, 0.0)
add('exterior', 'SM_Env_Pillar_Exterior_Floor_01', 14.5, -9.0, 0.0)
MOUNTED.append(add_mount('exterior', 'SM_Prop_Sign_Money_Bank_01', 'z', 0.0, -1, 0.0, 3.4, 0.0))
add('exterior', 'SM_Veh_Car_Police_Heist_01', -9.0, -7.0, 90.0)
add('exterior', 'SM_Veh_SwatVan_01', 9.0, -9.0, 270.0)
add('exterior', 'SM_Veh_Helicopter_01', 0.0, -17.0, 0.0)
add('exterior', 'SM_Prop_Bin_01', -15.0, -2.0, 0.0)
add('exterior', 'SM_Prop_Bin_01', 15.0, -2.0, 0.0)
add('exterior', 'SM_Prop_Plant_03', -15.0, -4.0, 0.0)
add('exterior', 'SM_Prop_Plant_03', 15.0, -4.0, 0.0)
add('exterior', 'SM_Prop_Statue_01', -4.0, -3.5, 0.0)
add('exterior', 'SM_Prop_Statue_01', 4.0, -3.5, 0.0)
for px in (-3.0, 3.0):
    add('exterior', 'SM_Prop_RopeBarrier_Pole_01', px, -1.6, 0.0)

# ------------------------------------------------------------------ spawns + killzone
ROOMS['lobby']['spawnPoints'] = [
    {'position': [-8.0, 1.0, 2.0], 'team': 1, 'type': 'delta'},
    {'position': [8.0, 1.0, 2.0], 'team': 1, 'type': 'delta'},
    {'position': [0.0, 1.0, 6.5], 'team': 1, 'type': 'delta'},
]
ROOMS['teller']['spawnPoints'] = [{'position': [0.0, 1.0, 13.0], 'team': 2, 'type': 'recon'}]
ROOMS['vault']['spawnPoints'] = [{'position': [0.0, 1.0, 20.0], 'team': 2, 'type': 'recon'}]
ROOMS['exterior']['spawnPoints'] = [
    {'position': [0.0, 1.0, -8.0], 'team': 2, 'type': 'recon'},
    {'position': [-10.0, 1.0, -5.0], 'team': 2, 'type': 'recon'},
    {'position': [10.0, 1.0, -5.0], 'team': 2, 'type': 'recon'},
]
ROOMS['lobby']['killZones'] = [{'position': [0.0, -5.0, 0.0], 'size': [80.0, 1.0, 80.0]}]

ORDER = ('exterior', 'lobby', 'teller', 'vault', 'corridorL', 'corridorR')
out = {
    'name': 'Heist Bank v3',
    'version': 3,
    'description': '6m grand lobby, wall-mounted fixtures, surface-stacked valuables, two-course shell',
    'rooms': [],
    'globalSpawnPoints': [],
    'navMesh': {'agentRadius': 0.4, 'agentHeight': 2.0, 'maxSlope': 45.0, 'stepHeight': 0.4},
}
for rid in ORDER:
    r = ROOMS[rid]
    r['id'] = rid
    out['rooms'].append({'id': rid,
                         'bounds': {'min': r['min'], 'max': r['max']},
                         'props': r['props'],
                         'spawnPoints': r['spawnPoints'],
                         'killZones': r['killZones']})

# ------------------------------------------------------------------ validation
FAIL = []
WARN = []


def world_aabb(p):
    n = p['prefab'].split('/')[-1].replace('.prefab', '')
    rot = p['rotation'][1]
    dx0, dx1, dz0, dz1, _, _ = rot_box(n, rot)
    x, z = p['position'][0], p['position'][2]
    return (x + dx0, z + dz0, x + dx1, z + dz1)


COUNTS = {rid: {'floors': 0, 'ceilings': 0, 'walls': 0, 'props': 0} for rid in ORDER}
for rid in ORDER:
    for p in ROOMS[rid]['props']:
        n = p['prefab'].split('/')[-1].replace('.prefab', '')
        if n.startswith('SM_Env_Floor'):
            COUNTS[rid]['floors'] += 1
        elif n.startswith('SM_Env_Ceiling'):
            COUNTS[rid]['ceilings'] += 1
        elif n.startswith('SM_Env_Wall') or n.startswith('SM_Env_Vault'):
            COUNTS[rid]['walls'] += 1
        else:
            COUNTS[rid]['props'] += 1

EXPECT = {'lobby': (10, 10), 'teller': (5, 5), 'vault': (6, 6),
          'corridorL': (2, 2), 'corridorR': (2, 2), 'exterior': (40, 0)}
for rid, (ef, ec) in EXPECT.items():
    if COUNTS[rid]['floors'] != ef:
        FAIL.append('%s floors=%d expected %d' % (rid, COUNTS[rid]['floors'], ef))
    if COUNTS[rid]['ceilings'] != ec:
        FAIL.append('%s ceilings=%d expected %d' % (rid, COUNTS[rid]['ceilings'], ec))

for label, names in (('front-lower', [W_EXT_WIN, W_EXT_WIN, W_EXT_DD, W_EXT_WIN, W_EXT_WIN]),
                     ('front-upper', [W_EXT_WIN, W_EXT_WIN, W_EXT, W_EXT_WIN, W_EXT_WIN]),
                     ('z10-lower', [W_INT_DOOR, W_INT_WIN, W_INT_WIN, W_INT_WIN, W_INT_DOOR]),
                     ('z15', [W_INT_DOOR, V_WALL, V_FRAME, V_WALL, W_INT_DOOR])):
    span = sum(sz(n)[0] for n in names)
    if abs(span - 25.0) > 0.01:
        FAIL.append('%s wall span %.2f != 25' % (label, span))
side = sum(sz(W_EXT_WIN if z == 7.5 else W_EXT)[0] for z in (2.5, 7.5, 12.5, 17.5, 22.5))
if abs(side - 25.0) > 0.01:
    FAIL.append('side wall span %.2f != 25' % side)

# mounted fixture flushness
for m in MOUNTED:
    dx0, dx1, dz0, dz1, _, _ = rot_box(m['name'], m['rot'])
    if m['axis'] == 'z':
        near = (m['z'] + dz0) if m['room_dir'] > 0 else (m['z'] + dz1)
    else:
        near = (m['x'] + dx0) if m['room_dir'] > 0 else (m['x'] + dx1)
    if abs(near - m['plane']) > 0.05:
        FAIL.append('mount not flush: %s gap=%.3f' % (m['name'], near - m['plane']))

# prop containment + furniture overlap (surface items exempt)
FURNITURE_EXEMPT = ('SM_Prop_Rug', 'SM_Prop_Money', 'SM_Prop_Folder', 'SM_Prop_GoldBar',
                    'SM_Prop_Computer', 'SM_Prop_Alarm', 'SM_Prop_Camera', 'SM_Prop_Sign',
                    'SM_Prop_Flag', 'SM_Prop_Air', 'SM_Prop_Sprinkler', 'SM_Prop_Fire',
                    'SM_Prop_RopeBarrier', 'SM_Prop_DeskLight', 'SM_Prop_Jewellery', 'SM_Item_')
for rid in ORDER:
    b = ROOMS[rid]
    furn = []
    for p in ROOMS[rid]['props']:
        n = p['prefab'].split('/')[-1].replace('.prefab', '')
        if p.get('mounted') or p.get('surface'):
            continue
        x0, z0, x1, z1 = world_aabb(p)
        if not n.startswith('SM_Env_') and (x0 < b['min'][0] - 0.05 or z0 < b['min'][2] - 0.05
                                            or x1 > b['max'][0] + 0.05 or z1 > b['max'][2] + 0.05):
            WARN.append('%s OUTSIDE: %s at %s' % (rid, n, p['position']))
        if n.startswith('SM_Prop_') and not n.startswith(FURNITURE_EXEMPT):
            furn.append((n, (x0, z0, x1, z1)))
    for i in range(len(furn)):
        for j in range(i + 1, len(furn)):
            a, fa = furn[i]
            c, fc = furn[j]
            if fa[0] < fc[2] - 0.08 and fc[0] < fa[2] - 0.08 and fa[1] < fc[3] - 0.08 and fc[1] < fa[3] - 0.08:
                WARN.append('%s OVERLAP: %s <-> %s' % (rid, a, c))

print('ROOMS:', ORDER)
for rid in ORDER:
    print('  %-10s floors=%2d ceilings=%2d walls=%2d props=%3d' % (
        rid, COUNTS[rid]['floors'], COUNTS[rid]['ceilings'], COUNTS[rid]['walls'], COUNTS[rid]['props']))
print('TOTAL PROPS:', sum(len(ROOMS[r]['props']) for r in ORDER))
print('MOUNTED FIXTURES:', len(MOUNTED))
for w in WARN:
    print('WARN:', w)
for f in FAIL:
    print('FAIL:', f)
if FAIL:
    print('VALIDATION_FAILED')
    raise SystemExit(1)

with io.open(OUT_PATH, 'w', encoding='utf-8', newline='\n') as f:
    json.dump(out, f, indent=2)
print('VALIDATION_OK')
print('WROTE', OUT_PATH)
