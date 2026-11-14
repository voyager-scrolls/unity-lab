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
#  - Walls read solid: wall slots take only SOLID modules (W_EXT, W_INT, V_FRAME); glass, grille, blind and door-panel modules fail validation; mounts need solid backing; exterior shell is ray-checked
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


def rot_center(name, rot):
    """Offset from prefab pivot to the centre of its rotated AABB (kit pieces use corner pivots)."""
    dx0, dx1, dz0, dz1, _, _ = rot_box(name, rot)
    return (dx0 + dx1) / 2.0, (dz0 + dz1) / 2.0


def add(room, name, x, z, rot=0.0, y=None, key=None):
    """Place with the footprint CENTRE at (x, z); bottom at y (default floor)."""
    if y is None:
        y = -P(name)['bounds']['min'][1]
    cx, cz = rot_center(name, rot)
    px_, pz_ = x - cx, z - cz
    p = _emit(room, name, px_, y, pz_, rot)
    if key:
        TRACK[key] = {'room': room, 'name': name, 'x': px_, 'y': y, 'z': pz_, 'rot': rot,
                      'top': y + P(name)['bounds']['max'][1], 'cx': x, 'cz': z}
    return p


def add_on(room, key, name, dx, dz, rot=0.0, lift=0.0):
    """Stack onto a tracked host surface, offset from the host footprint centre."""
    h = TRACK[key]
    tx, tz = h['cx'] + dx, h['cz'] + dz
    y = h['top'] - P(name)['bounds']['min'][1] + lift + GAP
    cx, cz = rot_center(name, rot)
    p = _emit(room, name, tx - cx, y, tz - cz, rot, {'surface': True})
    return p


def add_mount(room, name, axis, plane, room_dir, u, h, rot):
    """Mount a fixture flush to a wall plane; u is the AABB CENTRE coordinate along the wall."""
    dx0, dx1, dz0, dz1, dy0, dy1 = rot_box(name, rot)
    if axis == 'z':
        x = u - (dx0 + dx1) / 2.0
        if room_dir > 0:
            z = plane + GAP - dz0
        else:
            z = plane - GAP - dz1
    else:
        z = u - (dz0 + dz1) / 2.0
        if room_dir > 0:
            x = plane + GAP - dx0
        else:
            x = plane - GAP - dx1
    y = h - dy0
    _emit(room, name, x, y, z, rot, {'mounted': True})
    return {'x': x, 'y': y, 'z': z, 'rot': rot, 'name': name, 'axis': axis, 'plane': plane, 'room_dir': room_dir, 'u': u, 'h': h}


CEILING_MOUNTED = []


def add_ceiling(room, name, x, z, rot, ceil_y):
    """Hang a pendant fixture from the ceiling (its AABB top touches ceil_y)."""
    y = ceil_y - P(name)['bounds']['max'][1]
    cx, cz = rot_center(name, rot)
    _emit(room, name, x - cx, y, z - cz, rot, {'mounted': True})
    CEILING_MOUNTED.append({'name': name, 'x': x, 'z': z, 'top': y + P(name)['bounds']['max'][1], 'ceil': ceil_y})


MOUNTED = []

# ------------------------------------------------------------------ floors (5m kit)
FLOOR_A, FLOOR_B = 'SM_Env_Floor_01', 'SM_Env_Floor_02'
# Plaza surface: the Floor_01/02 atlas region is a black-and-white checker, not a paving slab.
# Sidewalk_01 reads as concrete paving and is the only exterior-grade slab in the kit.
PLAZA = 'SM_Env_Sidewalk_01'
PLAZA_Y = -P(PLAZA)['bounds']['max'][1]  # slab top flush to y=0 so props sit on it


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
        add('vault', PLAZA, x, z, y=PLAZA_Y)
for x in (-10, 10):
    for z in (17.5, 22.5):
        add('corridorL' if x < 0 else 'corridorR',
            FLOOR_A if (x + z) % 10 == 0 else FLOOR_B, x, z)
for x in (-17.5, -12.5, -7.5, -2.5, 2.5, 7.5, 12.5, 17.5):
    for z in (-2.5, -7.5, -12.5, -17.5, -22.5):
        add('exterior', PLAZA, x, z, y=PLAZA_Y)

# ------------------------------------------------------------------ ceilings (bottom at room height)
CEILINGS = ['SM_Env_Ceiling_01', 'SM_Env_Ceiling_02', 'SM_Env_Ceiling_03',
            'SM_Env_Ceiling_04', 'SM_Env_Ceiling_05']
# the right corridor's original pair is 04 (z=17.5) + 05 (z=22.5); corridorL copies that
# exact pair so both staff corridors match. Other rooms keep their own designs.
CORRIDOR_CEILINGS = ['SM_Env_Ceiling_04', 'SM_Env_Ceiling_05']
ci = 0
for x in (-10, -5, 0, 5, 10):
    for z in (12.5, 17.5, 22.5):
        rid = room_at(x, z)
        if rid in ('corridorL', 'corridorR'):
            n = CORRIDOR_CEILINGS[0 if z < 20 else 1]
        else:
            n = CEILINGS[ci % len(CEILINGS)]
            ci += 1
        add(rid, n, x, z, y=3.0 - P(n)['bounds']['min'][1])

# Roof caps the entire footprint at 6m. The lobby has no ceiling tiles - the roof underside IS its ceiling.
for x in (-10, -5, 0, 5, 10):
    for z in (2.5, 7.5, 12.5, 17.5, 22.5):
        add('lobby', 'SM_Env_Roof_05', x, z, y=6.0 - P('SM_Env_Roof_05')['bounds']['min'][1])

# ------------------------------------------------------------------ ceiling light fixtures
# SM_Env_Ceiling_Light_01 is a 0.73m emissive disc whose AABB top is y=0.
# LevelBuilder attaches a warm point light to every instance of this prefab.
def light(room, x, z, ceil_y):
    add(room, 'SM_Env_Ceiling_Light_01', x, z, 0.0, y=ceil_y)


for lx in (-8.0, 0.0, 8.0):
    for lz in (3.0, 7.0):
        light('lobby', lx, lz, 6.0)
for lx in (-8.0, 0.0, 8.0):
    light('teller', lx, 12.5, 3.0)
for lx in (-3.5, 3.5):
    for lz in (17.5, 22.5):
        light('vault', lx, lz, 3.0)
light('corridorL', -10.0, 20.0, 3.0)
light('corridorR', 10.0, 20.0, 3.0)

# ------------------------------------------------------------------ walls (two 3m courses)
W_EXT = 'SM_Env_Wall_Exterior_01'
W_EXT_WIN = 'SM_Env_Wall_Exterior_Window_01'
W_EXT_DD = 'SM_Env_Wall_Exterior_DoubleDoor_01'
W_INT = 'SM_Env_Wall_Interior_01'
W_INT_WIN = 'SM_Env_Wall_Interior_Window_01'
W_INT_DOOR = 'SM_Env_Wall_Interior_Door_01'
V_FRAME = 'SM_Env_VaultDoor_Frame_01'
V_WALL = 'SM_Env_VaultGate_Wall_01'
SOLID = (W_EXT, W_INT, V_FRAME)


def wall(room, name, x, z, rot, course):
    if name not in SOLID:
        raise SystemExit('NON-SOLID WALL MODULE: ' + name)
    add(room, name, x, z, rot, y=course * 3.0 - P(name)['bounds']['min'][1])


# facade Z=0: solid both courses; 5m entrance opening in the lower course (no door modules: they block passage or read as glass)
for x in (-10, -5, 5, 10):
    wall('lobby', W_EXT, x, 0.0, 0.0, 0)
for x in (-10, -5, 0, 5, 10):
    wall('lobby', W_EXT, x, 0.0, 0.0, 1)
# back Z=25: two courses (6m shell)
for x in (-10, -5, 0, 5, 10):
    wall(room_at(x, 24.9), W_EXT, x, 25.0, 180.0, 0)
    wall(room_at(x, 24.9), W_EXT, x, 25.0, 180.0, 1)
# sides X=+-12.5: two courses
for z in (2.5, 7.5, 12.5, 17.5, 22.5):
    rid = room_at(-12.4, z)
    wall(rid, W_EXT, -12.5, z, 90.0, 0)
    wall(rid, W_EXT, -12.5, z, 90.0, 1)
for z in (2.5, 7.5, 12.5, 17.5, 22.5):
    rid = room_at(12.4, z)
    wall(rid, W_EXT, 12.5, z, 270.0, 0)
    wall(rid, W_EXT, 12.5, z, 270.0, 1)
# lobby/teller wall Z=10: solid, open passages at +-10 (closed door modules block the NavMesh)
for x in (-5, 0, 5):
    wall('teller', W_INT, x, 10.0, 0.0, 0)
for x in (-10, -5, 0, 5, 10):
    wall('lobby', W_INT, x, 10.0, 0.0, 1)
# teller/vault wall Z=15: solid walls either side of the vault door.
# The door frame module is 0.74m deep - it is pushed back so its face is flush with the
# teller-side wall face (14.92), which removes the protruding slab and the edge slivers.
for x in (-5, 5):
    wall('vault', W_EXT, x, 15.0, 0.0, 0)
add('vault', V_FRAME, 0.0, 15.39, 0.0, y=0.0)
# vault side walls (solid)
for z in (17.5, 22.5):
    wall('vault', W_EXT, -7.5, z, 90.0, 0)
    wall('vault', W_EXT, 7.5, z, 270.0, 0)

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
add('lobby', 'SM_Prop_Pillar_01', -5.0, 5.0, 0.0, key='lbustbaseL')
add_on('lobby', 'lbustbaseL', 'SM_Prop_Statue_01', 0.0, 0.0, 180.0)
add('lobby', 'SM_Prop_Pillar_01', 5.0, 5.0, 0.0, key='lbustbaseR')
add_on('lobby', 'lbustbaseR', 'SM_Prop_Statue_01', 0.0, 0.0, 180.0)
add('lobby', 'SM_Prop_WaterCooler_01', 11.4, 6.8, 270.0)
add('lobby', 'SM_Prop_Bin_01', -11.4, 6.8, 0.0)
for px in (-3.0, -1.2, 1.2, 3.0):
    add('lobby', 'SM_Prop_RopeBarrier_Pole_01', px, 1.2, 0.0)
# ---- jewellery counters: four cases, stocked dense, trays aligned with the case axis ----
CASE_LONG = [('SM_Prop_Jewellery_04', 0.95), ('SM_Prop_Jewellery_Rings_01', 1.55),
             ('SM_Prop_Jewellery_Necklace_02', 2.00), ('SM_Prop_Jewellery_Necklace_01', 2.45)]
CASE_FRONT = [('SM_Prop_Jewellery_04', -4.90), ('SM_Prop_Jewellery_Rings_01', -4.30),
              ('SM_Prop_Jewellery_Ring_01', -3.70), ('SM_Prop_Jewellery_Necklace_04', -3.10)]
# side-wall cases (long axis runs along Z)
add('lobby', 'SM_Prop_DisplayCase_01', -9.0, 1.6, 90.0, key='caseL1')
for i, (n, z) in enumerate(CASE_LONG):
    add('lobby', n, -9.0, z, 90.0, y=0.80)
add('lobby', 'SM_Prop_DisplayCase_01', 9.0, 1.6, 270.0, key='caseR1')
for i, (n, z) in enumerate(CASE_LONG):
    add('lobby', n, 9.0, z, 90.0, y=0.80)
# entrance cases against the facade (long axis runs along X)
add('lobby', 'SM_Prop_DisplayCase_01', -4.0, 0.75, 0.0, key='caseL2')
for i, (n, x) in enumerate(CASE_FRONT):
    add('lobby', n, x, 0.75, 0.0, y=0.80)
add('lobby', 'SM_Prop_DisplayCase_01', 4.0, 0.75, 0.0, key='caseR2')
for i, (n, x) in enumerate(CASE_FRONT):
    add('lobby', n, -x, 0.75, 0.0, y=0.80)
# ---- robbery staging: entry spill, loot being sorted on the rug, cases being cleared ----
add('lobby', 'SM_Item_DuffleBag_Open_Empty_01', -2.05, 2.35, 25.0)
add('lobby', 'SM_Prop_Money_Note_03', -1.35, 2.55, 40.0, y=0.02)
add('lobby', 'SM_Prop_Money_Note_05', -2.60, 2.90, 300.0, y=0.02)
add('lobby', 'SM_Prop_Money_Note_07', -1.70, 3.20, 15.0, y=0.02)
add('lobby', 'SM_Item_Crowbar_01', -2.55, 1.70, 65.0, y=0.09)
add('lobby', 'SM_Item_Mask_Clown_01', -0.75, 2.90, 220.0, y=0.13)
add('lobby', 'SM_Item_Briefcase_01', 0.55, 5.00, 100.0, y=0.18)
add('lobby', 'SM_Prop_Money_Stack_03', -0.55, 5.30, 12.0, y=0.18)
add('lobby', 'SM_Prop_Jewellery_Necklace_03', 0.90, 5.80, 0.0, y=0.18)
add('lobby', 'SM_Prop_Jewellery_Rings_01', -0.15, 5.90, 20.0, y=0.19)
add('lobby', 'SM_Prop_Jewellery_04', 0.65, 5.60, 40.0, y=0.18)
add('lobby', 'SM_Prop_Money_Note_01', -0.90, 5.70, 75.0, y=0.18)
# pieces dropped at the foot of the two side cases
add('lobby', 'SM_Prop_Jewellery_Rings_01', -8.75, 1.05, 30.0, y=0.02)
add('lobby', 'SM_Prop_Jewellery_Ring_01', -8.55, 1.35, 0.0, y=0.02)
add('lobby', 'SM_Prop_Jewellery_04', -8.90, 1.45, 15.0, y=0.0)
add('lobby', 'SM_Prop_Jewellery_03', 8.75, 1.05, 25.0, y=0.0)
add('lobby', 'SM_Prop_Jewellery_Ring_01', 8.55, 1.35, 0.0, y=0.02)
# cash dragged off the ATMs
add('lobby', 'SM_Prop_Money_Stack_02', -11.35, 5.00, 20.0)
add('lobby', 'SM_Prop_Money_Stack_02', 11.35, 6.00, 340.0)
add('lobby', 'SM_Prop_Money_Note_04', -11.05, 4.65, 55.0, y=0.02)
add('lobby', 'SM_Prop_Money_Note_06', 11.05, 6.35, 290.0, y=0.02)
# wall fixtures
MOUNTED.append(add_mount('lobby', 'SM_Prop_Sign_Bank_01', 'z', 10.0, -1, 0.0, 3.3, 180.0))
# ceiling pendant cameras (the kit's Camera_01 hangs below its pivot - mount at ceiling, not wall)
add_ceiling('lobby', 'SM_Prop_Camera_01', -9.5, 3.0, 180.0, 6.0)
add_ceiling('lobby', 'SM_Prop_Camera_01', 9.5, 3.0, 180.0, 6.0)
add_ceiling('lobby', 'SM_Prop_Camera_01', -12.1, 5.0, 90.0, 6.0)
MOUNTED.append(add_mount('lobby', 'SM_Prop_AlarmButton_01', 'z', 10.0, -1, 7.0, 1.2, 180.0))
MOUNTED.append(add_mount('lobby', 'SM_Prop_Flag_Wall_01', 'x', -12.5, 1, 3.5, 1.4, 90.0))
MOUNTED.append(add_mount('lobby', 'SM_Prop_Flag_Wall_02', 'x', 12.5, -1, 3.5, 1.4, 270.0))

# ------------------------------------------------------------------ teller (3m suspended ceiling)
# teller counters stand in the lobby, pulled 1.8m off the partition so staff have a workable aisle
# (fronts face the lobby; the workstation sits on the staff side, +z towards the partition)
# counter dressing: computer centred, cash on the side facing the neighbouring desk,
# lamp on the opposite end pushed inboard so its base sits clear of the counter edge
for x, s in ((-5.0, 1.0), (0.0, -1.0), (5.0, -1.0)):
    k = 'desk%d' % int(x * 10)
    add('lobby', 'SM_Prop_TellerDesk_01', x, 8.2, 180.0, key=k)
    add_on('lobby', k, 'SM_Prop_Computer_01', 0.0, 0.0, 0.0)
    add_on('lobby', k, 'SM_Prop_Money_Stack_01', 0.72 * s, -0.10, 0.0)
    add_on('lobby', k, 'SM_Prop_DeskLight_01', -0.58 * s, -0.26, 180.0)
# display cases against the side walls, stocked and being emptied
TCASE = [('SM_Prop_Jewellery_04', 11.55), ('SM_Prop_Jewellery_Rings_01', 12.05),
         ('SM_Prop_Jewellery_Necklace_03', 12.55), ('SM_Prop_Jewellery_03', 13.05)]
add('teller', 'SM_Prop_DisplayCase_01', -12.15, 12.5, 90.0, key='tcase1')
for i, (n, z) in enumerate(TCASE):
    add('teller', n, -12.15, z, 90.0, y=0.80)
add('teller', 'SM_Prop_DisplayCase_01', 12.15, 12.5, 270.0, key='tcase2')
for i, (n, z) in enumerate(TCASE):
    add('teller', n, 12.15, z, 90.0, y=0.80)
add('teller', 'SM_Prop_Jewellery_Rings_01', -11.35, 12.15, 20.0, y=0.02)
add('teller', 'SM_Prop_Jewellery_Ring_01', -11.20, 12.75, 0.0, y=0.02)
add('teller', 'SM_Prop_Jewellery_04', 11.30, 12.30, 35.0, y=0.0)
add('teller', 'SM_Prop_Jewellery_Necklace_04', 11.45, 13.00, 0.0, y=0.0)
# ---- robbery staging behind the wall: cash trail from the passages to the vault door ----
add('teller', 'SM_Prop_Money_Stack_01', -6.40, 11.60, 20.0)
add('teller', 'SM_Prop_Money_Stack_02', -3.10, 12.70, 350.0)
add('teller', 'SM_Prop_Money_Note_02', -4.60, 12.20, 60.0, y=0.02)
add('teller', 'SM_Prop_Money_Note_05', -1.60, 13.10, 300.0, y=0.02)
add('teller', 'SM_Prop_Money_Stack_03', -3.60, 13.90, 5.0)
add('teller', 'SM_Prop_Money_Stack_02', 2.90, 13.95, 355.0)
add('teller', 'SM_Prop_Money_Note_06', 1.20, 13.40, 25.0, y=0.02)
# ---- the breach: two charges planted on the floor right in front of the vault door ----
add('teller', 'SM_Item_Bomb_01', -1.15, 14.35, 20.0)
add('teller', 'SM_Item_Bomb_01', 1.35, 14.35, 340.0)
add('teller', 'SM_Item_Briefcase_02', -2.15, 14.15, 75.0, y=0.10)
# gear dropped at the breach point
add('teller', 'SM_Item_Mask_Balaclava_01', 1.75, 13.75, 200.0, y=0.11)
add('teller', 'SM_Item_Mask_Hockey_01', -1.90, 13.50, 120.0, y=0.10)
add('teller', 'SM_Wep_RifleBandit_01', 7.60, 10.70, 70.0, y=0.16)
add('teller', 'SM_Item_AmmoPack_01', 7.20, 11.10, 30.0)
# ---- staff aisle behind the counters: cash swept off the tills, bag being filled ----
add('lobby', 'SM_Prop_Money_Stack_03', -4.30, 9.35, 10.0)
add('lobby', 'SM_Prop_Money_Stack_02', 1.10, 9.30, 350.0)
add('lobby', 'SM_Prop_Money_Stack_01', 5.40, 9.40, 20.0)
add('lobby', 'SM_Prop_Money_Note_04', -3.20, 9.55, 15.0, y=0.02)
add('lobby', 'SM_Prop_Money_Note_01', 2.20, 9.50, 100.0, y=0.02)
add('lobby', 'SM_Prop_Money_Note_07', 0.20, 9.60, 250.0, y=0.02)
add('lobby', 'SM_Item_DuffleBag_Open_Empty_01', 3.60, 9.30, 200.0)
add('lobby', 'SM_Item_Mask_Balaclava_01', 2.75, 9.55, 140.0, y=0.11)
add('lobby', 'SM_Item_Crowbar_01', -6.00, 9.45, 80.0, y=0.09)
MOUNTED.append(add_mount('teller', 'SM_Prop_AirVent_01', 'z', 14.92, -1, 5.0, 2.6, 0.0))
add_ceiling('teller', 'SM_Prop_Camera_01', -8.0, 14.6, 0.0, 3.0)
MOUNTED.append(add_mount('teller', 'SM_Prop_AlarmButton_01', 'z', 10.0, 1, 7.0, 1.2, 0.0))

# ------------------------------------------------------------------ vault (3m)
for z in (17.5, 22.5):
    pass
MOUNTED.append(add_mount('vault', 'SM_Prop_SafeDepositBoxes_01', 'x', -7.5, 1, 20.0, 0.0, 90.0))
MOUNTED.append(add_mount('vault', 'SM_Prop_SafeDepositBoxes_01', 'x', 7.5, -1, 20.0, 0.0, 270.0))
add('vault', 'SM_Prop_Table_01', 0.0, 20.0, 0.0, key='vtable')
add_on('vault', 'vtable', 'SM_Prop_GoldBar_01', -0.6, 0.0, 20.0)
add_on('vault', 'vtable', 'SM_Prop_GoldBar_02', -0.2, 0.05, 65.0)
add_on('vault', 'vtable', 'SM_Prop_GoldBar_01', 0.25, 0.0, 340.0)
add_on('vault', 'vtable', 'SM_Prop_Money_Stack_01', 0.45, 0.3, 15.0)
add_on('vault', 'vtable', 'SM_Prop_Jewellery_Necklace_02', -0.75, 0.42, 0.0)
add_on('vault', 'vtable', 'SM_Prop_Jewellery_Rings_01', 0.05, 0.40, 0.0)
# crowbar lies along the table's long axis, fully on the top (table top x +-1.06, z +-0.65)
add_on('vault', 'vtable', 'SM_Item_Crowbar_01', 0.82, 0.0, 0.0, lift=0.02)
# the drill is 1.6m long - too big for the table, it goes on the floor beside it
add('vault', 'SM_Prop_Drill_01', -2.6, 20.0, 90.0, key='vdrill')
add('vault', 'SM_Prop_VaultTrolley_01', 3.2, 21.0, 0.0, key='vtrolley')
add('vault', 'SM_Item_DuffleBag_Full_01', -3.4, 18.2, 270.0)
add('vault', 'SM_Item_DuffleBag_Open_Empty_01', -4.2, 21.5, 90.0)
add('vault', 'SM_Item_DuffleBag_Open_Full_01', 1.6, 18.4, 90.0)
# hijacked-vault dressing: the score scattered where it was dropped
add('vault', 'SM_Wep_RifleBandit_01', -5.9, 18.6, 90.0, y=0.16)
add('vault', 'SM_Item_AmmoPack_01', -5.4, 19.5, 30.0)
add('vault', 'SM_Item_Mask_Balaclava_01', -4.9, 19.2, 200.0, y=0.11)
add('vault', 'SM_Item_Mask_Hockey_01', -4.5, 19.9, 120.0, y=0.10)
add('vault', 'SM_Item_Briefcase_01', 2.4, 19.2, 40.0, y=0.10)
add('vault', 'SM_Item_Hacksaw_01', 5.8, 18.9, 15.0, y=0.11)
# jewellery spilling out of the trays
add('vault', 'SM_Prop_Jewellery_Necklace_03', -1.90, 19.30, 0.0)
add('vault', 'SM_Prop_Jewellery_Rings_01', -1.20, 19.70, 25.0, y=0.02)
add('vault', 'SM_Prop_Jewellery_04', 0.90, 21.30, 40.0)
add('vault', 'SM_Prop_Jewellery_Ring_01', 2.00, 20.60, 0.0, y=0.02)
# cash piles staged for the carry-out, plus loot on the trolley deck
add('vault', 'SM_Prop_Money_Stack_02', -4.80, 22.10, 15.0)
add('vault', 'SM_Prop_Money_Stack_03', 2.60, 22.30, 345.0)
add('vault', 'SM_Prop_Money_Note_03', -3.90, 22.50, 70.0, y=0.02)
add('vault', 'SM_Prop_Money_Note_07', 4.40, 20.40, 240.0, y=0.02)
add('vault', 'SM_Prop_Money_Stack_01', 3.2, 21.0, 0.0, y=1.083)
MOUNTED.append(add_mount('vault', 'SM_Prop_AirVent_01', 'z', 25.0, -1, -3.5, 2.6, 0.0))
add_ceiling('vault', 'SM_Prop_Camera_01', 0.0, 24.6, 0.0, 3.0)

# ------------------------------------------------------------------ corridors / offices
add('corridorL', 'SM_Prop_Desk_01', -10.0, 17.0, 90.0, key='ldesk')
add('corridorL', 'SM_Prop_Seat_01', -11.32, 17.0, 90.0)
add_on('corridorL', 'ldesk', 'SM_Prop_Folder_02', -0.4, -0.2, 90.0)
add('corridorL', 'SM_Prop_Pillar_01', -11.4, 23.4, 0.0, key='lstatuebase')
add_on('corridorL', 'lstatuebase', 'SM_Prop_Statue_01', 0.0, 0.0, 180.0)
add('corridorL', 'SM_Prop_Shelf_01', -12.0, 20.0, 90.0)
add('corridorL', 'SM_Prop_Drawers_01', -10.0, 23.0, 0.0)
add('corridorL', 'SM_Prop_Plant_02', -8.8, 23.6, 0.0)
add_ceiling('corridorL', 'SM_Prop_Camera_01', -12.1, 22.0, 90.0, 3.0)
add('corridorL', 'SM_Prop_Money_Stack_01', -8.60, 19.40, 25.0)
add('corridorR', 'SM_Prop_Desk_02', 10.0, 17.0, 270.0, key='rdesk')
add('corridorR', 'SM_Prop_Seat_01', 11.32, 17.0, 270.0)
add_on('corridorR', 'rdesk', 'SM_Prop_Computer_01', 0.0, 0.3, 270.0)
add_on('corridorR', 'rdesk', 'SM_Prop_Folder_03', 0.4, -0.2, 270.0)
add('corridorR', 'SM_Prop_Pillar_01', 11.4, 23.4, 0.0, key='rstatuebase')
add_on('corridorR', 'rstatuebase', 'SM_Prop_Statue_01', 0.0, 0.0, 180.0)
add('corridorR', 'SM_Prop_Shelf_01', 12.0, 20.0, 270.0)
add('corridorR', 'SM_Prop_WaterCooler_01', 8.4, 23.4, 0.0)
add('corridorR', 'SM_Prop_Drawers_01', 10.0, 23.0, 0.0)
add_ceiling('corridorR', 'SM_Prop_Camera_01', 12.1, 22.0, 270.0, 3.0)
add('corridorR', 'SM_Item_Briefcase_01', 9.40, 19.20, 95.0, y=0.10)

# ------------------------------------------------------------------ exterior
add('exterior', 'SM_Env_Pillar_Exterior_Floor_01', -14.5, -3.0, 0.0)
add('exterior', 'SM_Env_Pillar_Exterior_Floor_01', 14.5, -3.0, 0.0)
add('exterior', 'SM_Env_Pillar_Exterior_Floor_01', -14.5, -9.0, 0.0)
add('exterior', 'SM_Env_Pillar_Exterior_Floor_01', 14.5, -9.0, 0.0)
MOUNTED.append(add_mount('exterior', 'SM_Prop_Sign_Money_Bank_01', 'z', 0.0, -1, 0.0, 3.4, 180.0))
add('exterior', 'SM_Veh_Car_Police_Heist_01', -9.0, -7.0, 90.0)
add('exterior', 'SM_Veh_SwatVan_01', 9.0, -9.0, 270.0)
add('exterior', 'SM_Veh_Helicopter_01', -17.0, -15.0, 0.0)
add('exterior', 'SM_Prop_Bin_01', -15.0, -2.0, 0.0)
add('exterior', 'SM_Prop_Bin_01', 15.0, -2.0, 0.0)
add('exterior', 'SM_Prop_Flag_Pole_01', -6.0, -4.5, 0.0)
add('exterior', 'SM_Prop_Flag_Pole_01', 6.0, -4.5, 0.0)
add('exterior', 'SM_Prop_Plant_03', -15.0, -4.0, 0.0)
add('exterior', 'SM_Prop_Plant_03', 15.0, -4.0, 0.0)
for px in (-3.0, 3.0):
    add('exterior', 'SM_Prop_RopeBarrier_Pole_01', px, -1.6, 0.0)

# ------------------------------------------------------------------ spawns + killzone
ROOMS['lobby']['spawnPoints'] = [
    {'position': [-8.0, 1.0, 2.0], 'team': 1, 'type': 'delta'},
    {'position': [8.0, 1.0, 2.0], 'team': 1, 'type': 'delta'},
    {'position': [0.0, 1.0, 6.5], 'team': 1, 'type': 'delta'},
]
ROOMS['teller']['spawnPoints'] = [{'position': [-9.8, 1.0, 14.2], 'team': 2, 'type': 'recon'}]
ROOMS['vault']['spawnPoints'] = [{'position': [-3.5, 1.0, 23.5], 'team': 2, 'type': 'recon'}]
ROOMS['exterior']['spawnPoints'] = [
    {'position': [0.0, 1.0, -8.0], 'team': 2, 'type': 'recon'},
    {'position': [-10.0, 1.0, -5.0], 'team': 2, 'type': 'recon'},
    {'position': [10.0, 1.0, -5.0], 'team': 2, 'type': 'recon'},
]
ROOMS['lobby']['killZones'] = [{'position': [0.0, -5.0, 0.0], 'size': [80.0, 1.0, 80.0]}]

# ---------------------------------------------------------------- sightline checks (builder raycasts these)
LOS_CHECKS = [
    {'name': 'lobby-teller-wall', 'from': [0.0, 0.8, 5.0], 'to': [0.0, 0.8, 12.5], 'blocked': True},
    {'name': 'teller-vault-wall', 'from': [3.0, 0.8, 13.0], 'to': [3.0, 0.8, 20.0], 'blocked': True},
    {'name': 'vault-corridorL-wall', 'from': [3.0, 0.8, 22.0], 'to': [-10.0, 0.8, 20.0], 'blocked': True},
    {'name': 'vault-corridorR-wall', 'from': [-3.0, 0.8, 22.0], 'to': [10.0, 0.8, 20.0], 'blocked': True},
    {'name': 'lobby-exterior-window', 'from': [-9.0, 0.8, 3.0], 'to': [-9.0, 0.8, -5.0], 'blocked': True},
    {'name': 'entrance-open', 'from': [0.6, 0.8, -8.0], 'to': [0.6, 0.8, 4.0], 'blocked': False},
]

# ---------------------------------------------------------------- AI cover points
# Positions behind designed cover (couches, pillars, cases, desks, vehicles), spacing >= 2m.
COVER = {
    'lobby': [(-7.2, 1.0), (7.2, 1.0), (-7.0, 8.8), (7.0, 8.8), (-5.0, 4.3), (5.0, 4.3),
              (-9.8, 3.2), (9.8, 3.2), (-2.0, 1.6), (2.0, 1.6), (0.0, 7.2), (-11.0, 5.5),
              (11.0, 5.5)],
    'teller': [(-7.0, 12.9), (7.0, 12.9), (-3.0, 14.0), (3.0, 14.0), (-10.0, 13.6), (10.0, 13.6)],
    'vault': [(-6.0, 16.6), (6.0, 16.6), (-3.5, 23.5), (3.5, 23.5)],
    'corridorL': [(-11.3, 19.6), (-8.7, 21.5)],
    'corridorR': [(11.3, 19.6), (8.7, 21.5)],
    'exterior': [(-9.0, -5.0), (9.0, -7.0), (0.0, -9.5), (-12.0, -3.0), (12.0, -3.0)],
}
for rid, pts in COVER.items():
    ROOMS[rid]['coverPoints'] = [{'position': [x, 0.1, z]} for (x, z) in pts]

for r in ROOMS.values():
    r.setdefault('coverPoints', [])

ORDER = ('exterior', 'lobby', 'teller', 'vault', 'corridorL', 'corridorR')
out = {
    'name': 'Heist Bank v3',
    'version': 3,
    'description': '6m grand lobby, wall-mounted fixtures, surface-stacked valuables, two-course shell',
    'rooms': [],
    'globalSpawnPoints': [],
    'losChecks': LOS_CHECKS,
    'navMesh': {'agentRadius': 0.4, 'agentHeight': 2.0, 'maxSlope': 45.0, 'stepHeight': 0.4},
}
for rid in ORDER:
    r = ROOMS[rid]
    r['id'] = rid
    out['rooms'].append({'id': rid,
                         'bounds': {'min': r['min'], 'max': r['max']},
                         'props': r['props'],
                         'spawnPoints': r['spawnPoints'],
                         'coverPoints': r['coverPoints'],
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
        if n.startswith('SM_Env_Floor') or n.startswith('SM_Env_Sidewalk'):
            COUNTS[rid]['floors'] += 1
        elif n.startswith('SM_Env_Ceiling_Light'):
            COUNTS[rid]['lights'] = COUNTS[rid].get('lights', 0) + 1
        elif n.startswith('SM_Env_Ceiling'):
            COUNTS[rid]['ceilings'] += 1
        elif n.startswith('SM_Env_Wall') or n.startswith('SM_Env_Vault'):
            COUNTS[rid]['walls'] += 1
        else:
            COUNTS[rid]['props'] += 1

EXPECT = {'lobby': (10, 0), 'teller': (5, 5), 'vault': (6, 6),
          'corridorL': (2, 2), 'corridorR': (2, 2), 'exterior': (40, 0)}
ROOF_COUNT = sum(1 for p in ROOMS['lobby']['props']
                 if p['prefab'].split('/')[-1].startswith('SM_Env_Roof'))
if ROOF_COUNT != 25:
    FAIL.append('roof tiles=%d expected 25' % ROOF_COUNT)
for rid, (ef, ec) in EXPECT.items():
    if COUNTS[rid]['floors'] != ef:
        FAIL.append('%s floors=%d expected %d' % (rid, COUNTS[rid]['floors'], ef))
    if COUNTS[rid]['ceilings'] != ec:
        FAIL.append('%s ceilings=%d expected %d' % (rid, COUNTS[rid]['ceilings'], ec))

for label, names, opens in (('front-lower', [W_EXT, W_EXT, W_EXT, W_EXT], 1),
                            ('front-upper', [W_EXT, W_EXT, W_EXT, W_EXT, W_EXT], 0),
                            ('z10-lower', [W_INT, W_INT, W_INT], 2),
                            ('z10-upper', [W_INT, W_INT, W_INT, W_INT, W_INT], 0),
                            ('z15', [W_EXT, V_FRAME, W_EXT], 2),
                            ('back', [W_EXT, W_EXT, W_EXT, W_EXT, W_EXT], 0)):
    span = sum(sz(n)[0] for n in names) + 5.0 * opens
    if abs(span - 25.0) > 0.01:
        FAIL.append('%s wall span %.2f != 25' % (label, span))
side = sum(sz(W_EXT)[0] for z in (2.5, 7.5, 12.5, 17.5, 22.5))
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

# pendant fixtures: their AABB top must touch the ceiling
for m in CEILING_MOUNTED:
    if abs(m['top'] - m['ceil']) > 0.05:
        FAIL.append('pendant not on ceiling: %s gap=%.3f' % (m['name'], m['top'] - m['ceil']))

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

# cover point validation: inside room bounds + spacing
all_cp = []
for rid in ORDER:
    b = ROOMS[rid]
    for cp in ROOMS[rid]['coverPoints']:
        x, z = cp['position'][0], cp['position'][2]
        if not (b['min'][0] <= x <= b['max'][0] and b['min'][2] <= z <= b['max'][2]):
            FAIL.append('%s cover point outside bounds at %s,%s' % (rid, x, z))
        all_cp.append((rid, x, z))
for i in range(len(all_cp)):
    for j in range(i + 1, len(all_cp)):
        dx = all_cp[i][1] - all_cp[j][1]
        dz = all_cp[i][2] - all_cp[j][2]
        if dx * dx + dz * dz < 4.0:
            FAIL.append('cover points closer than 2m: %s<->%s' % (all_cp[i], all_cp[j]))
if len(all_cp) < 20:
    FAIL.append('only %d cover points (need >= 20 for bot coverage)' % len(all_cp))

# ------------------------------------------------------------------ solid-wall gate
FORBIDDEN_NAMES = {W_EXT_WIN, W_EXT_DD, W_INT_WIN, W_INT_DOOR, V_WALL,
                   'SM_Env_Wall_Window_Blinds_01', 'SM_Env_Door_01', 'SM_Env_Door_02'}


def pname(p):
    return p['prefab'].split('/')[-1].replace('.prefab', '')


def is_forbidden(n):
    return (n in FORBIDDEN_NAMES or 'Window' in n or 'Blinds' in n
            or 'VaultGate' in n or n.startswith('SM_Env_Door'))


def world_box(p):
    dx0, dx1, dz0, dz1, dy0, dy1 = rot_box(pname(p), p['rotation'][1])
    x, y, z = p['position']
    return (x + dx0, y + dy0, z + dz0, x + dx1, y + dy1, z + dz1)


ALL_PROPS = [(rid, p) for rid in ORDER for p in ROOMS[rid]['props']]
SOLID_BOXES = [world_box(p) for rid, p in ALL_PROPS if pname(p) in SOLID]
FORBIDDEN_HITS = [pname(p) + ' in ' + rid for rid, p in ALL_PROPS if is_forbidden(pname(p))]
for hit in FORBIDDEN_HITS:
    FAIL.append('forbidden wall-type module: ' + hit)


def solid_at(axis, plane, u, y):
    for x0, y0, z0, x1, y1, z1 in SOLID_BOXES:
        if axis == 'z':
            a0, a1, b0, b1 = z0, z1, x0, x1
        else:
            a0, a1, b0, b1 = x0, x1, z0, z1
        if a0 - 0.05 <= plane <= a1 + 0.05 and b0 - 0.01 <= u <= b1 + 0.01 and y0 - 0.01 <= y <= y1 + 0.01:
            return True
    return False


SHELL_SAMPLES = 0
SHELL_FAILS = []
for axis, plane, lo, hi, exempt in (
        ('z', 0.0, -12.5, 12.5, lambda u, y: abs(u) <= 2.5 and y < 3.0),
        ('z', 25.0, -12.5, 12.5, lambda u, y: False),
        ('x', -12.5, 0.0, 25.0, lambda u, y: False),
        ('x', 12.5, 0.0, 25.0, lambda u, y: False)):
    for i in range(int(round((hi - lo) / 0.5)) + 1):
        u = lo + 0.5 * i
        for y in (0.5, 1.6, 2.5, 3.5, 4.5, 5.5):
            if exempt(u, y):
                continue
            SHELL_SAMPLES += 1
            if not solid_at(axis, plane, u, y):
                SHELL_FAILS.append('%s=%.1f u=%.1f y=%.1f' % (axis, plane, u, y))
if SHELL_FAILS:
    FAIL.append('shell not solid at %d samples, first: %s' % (len(SHELL_FAILS), SHELL_FAILS[:6]))
if solid_at('z', 0.0, 0.0, 1.0):
    FAIL.append('entrance opening blocked at x=0 z=0')

MOUNT_FAILS = []
for m in MOUNTED:
    if not solid_at(m['axis'], m['plane'], m['u'], m['h'] + 0.05):
        MOUNT_FAILS.append(m['name'])
        FAIL.append('mount without solid backing: %s u=%.2f h=%.2f' % (m['name'], m['u'], m['h']))

MOUNTED_BOXES = [(pname(p), world_box(p)) for rid, p in ALL_PROPS if p.get('mounted')]
for i in range(len(MOUNTED_BOXES)):
    for j in range(i + 1, len(MOUNTED_BOXES)):
        na, a = MOUNTED_BOXES[i]
        nb, b = MOUNTED_BOXES[j]
        if all(a[k] < b[k + 3] - 0.02 and b[k] < a[k + 3] - 0.02 for k in range(3)):
            FAIL.append('mounted fixtures overlap: %s <-> %s' % (na, nb))
print('SOLID_WALL_MODULES:', len(SOLID_BOXES))
print('FORBIDDEN_WALL_MODULES:', len(FORBIDDEN_HITS))
print('SHELL_SAMPLES:', SHELL_SAMPLES, 'SHELL_FAILS:', len(SHELL_FAILS))
print('MOUNT_BACKING_FAILS:', len(MOUNT_FAILS))

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
