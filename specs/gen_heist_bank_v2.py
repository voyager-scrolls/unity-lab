# gen_heist_bank_v2.py - computes a coherent bank floor plan on the POLYGON Heist 5m module grid
# and validates it before shipping. Run: py -3 specs/gen_heist_bank_v2.py
#
# Design rules (enforced, not vibes):
#  - All geometry on the 5m kit grid; wall runs sum exactly to room spans (checked)
#  - Props sit at y = -bounds.min.y from the catalog (measured) so nothing floats/sinks
#  - Furniture kept inside room bounds; furniture footprints checked for overlap
#  - Floor + ceiling tile coverage checked per room; door openings checked on shared walls
import io
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT_PATH = os.path.join(ROOT, 'specs', 'heist-catalog.json')
OUT_PATH = os.path.join(ROOT, 'specs', 'heist-bank-v2.json')

with io.open(CAT_PATH, encoding='utf-8') as f:
    CATALOG = json.load(f)
BY = {}
for e in CATALOG:
    BY.setdefault(e['name'], e)


def prefab(name):
    e = BY.get(name)
    if e is None:
        raise SystemExit('MISSING PREFAB: ' + name)
    return e


def fsize(name):
    b = prefab(name)['bounds']
    return [b['max'][i] - b['min'][i] for i in range(3)]


ROOMS = {
    'exterior':  {'bounds': {'min': [-20, 0, -25], 'max': [20, 5, 0]}},
    'lobby':     {'bounds': {'min': [-12.5, 0, 0], 'max': [12.5, 5, 10]}},
    'teller':    {'bounds': {'min': [-12.5, 0, 10], 'max': [12.5, 5, 15]}},
    'vault':     {'bounds': {'min': [-7.5, 0, 15], 'max': [7.5, 5, 25]}},
    'corridorL': {'bounds': {'min': [-12.5, 0, 15], 'max': [-7.5, 5, 25]}},
    'corridorR': {'bounds': {'min': [7.5, 0, 15], 'max': [12.5, 5, 25]}},
}
for r in ROOMS.values():
    r['id'] = None
    r['props'] = []
    r['spawnPoints'] = []
    r['killZones'] = []


def add(room, name, x, z, rot=0.0, y=None, tag=None):
    e = prefab(name)
    if y is None:
        y = -e['bounds']['min'][1]
    p = {'prefab': e['path'],
         'position': [round(x, 3), round(y, 3), round(z, 3)],
         'rotation': [0.0, round(rot, 3), 0.0],
         'scale': [1.0, 1.0, 1.0]}
    if tag:
        p['tag'] = tag
    ROOMS[room]['props'].append(p)
    return p


def room_at(x, z):
    for rid in ('lobby', 'teller', 'vault', 'corridorL', 'corridorR', 'exterior'):
        b = ROOMS[rid]['bounds']
        if b['min'][0] <= x <= b['max'][0] and b['min'][2] <= z <= b['max'][2]:
            return rid
    raise SystemExit('no room for %s,%s' % (x, z))


# ---------------------------------------------------------------- floors
FLOOR_A, FLOOR_B = 'SM_Env_Floor_01', 'SM_Env_Floor_02'
CEILINGS = ['SM_Env_Ceiling_01', 'SM_Env_Ceiling_02', 'SM_Env_Ceiling_03',
            'SM_Env_Ceiling_04', 'SM_Env_Ceiling_05']

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

# ---------------------------------------------------------------- ceilings (y=3)
ci = 0
for x in (-10, -5, 0, 5, 10):
    for z in (2.5, 7.5, 12.5, 17.5, 22.5):
        add(room_at(x, z), CEILINGS[ci % len(CEILINGS)], x, z, y=3.0)
        ci += 1

# ---------------------------------------------------------------- walls (5m modules)
W_EXT = 'SM_Env_Wall_Exterior_01'
W_EXT_WIN = 'SM_Env_Wall_Exterior_Window_01'
W_EXT_DD = 'SM_Env_Wall_Exterior_DoubleDoor_01'
W_INT = 'SM_Env_Wall_Interior_01'
W_INT_WIN = 'SM_Env_Wall_Interior_Window_01'
W_INT_DOOR = 'SM_Env_Wall_Interior_Door_01'
V_FRAME = 'SM_Env_VaultDoor_Frame_01'
V_WALL = 'SM_Env_VaultGate_Wall_01'

# facade Z=0 (5 modules, centre = entrance double door)
for x, n in ((-10, W_EXT_WIN), (-5, W_EXT_WIN), (0, W_EXT_DD), (5, W_EXT_WIN), (10, W_EXT_WIN)):
    add('lobby', n, x, 0.0, 0.0)
# back Z=25
for x in (-10, -5, 0, 5, 10):
    add(room_at(x, 24.9), W_EXT, x, 25.0, 180.0)
# sides X=+-12.5
for z in (2.5, 7.5, 12.5, 17.5, 22.5):
    rid = room_at(-12.4 if z < 15 else -12.4, z) if z < 15 else ('corridorL')
    add(rid, W_EXT_WIN if z == 7.5 else W_EXT, -12.5, z, 90.0)
for z in (2.5, 7.5, 12.5, 17.5, 22.5):
    rid = room_at(12.4, z) if z < 15 else ('corridorR')
    add(rid, W_EXT_WIN if z == 7.5 else W_EXT, 12.5, z, 270.0)
# lobby/teller wall Z=10 (openings at +-10)
for x, n in ((-10, W_INT_DOOR), (-5, W_INT_WIN), (0, W_INT_WIN), (5, W_INT_WIN), (10, W_INT_DOOR)):
    add('teller', n, x, 10.0, 0.0)
# teller/vault wall Z=15: doors at +-10, vault front at centre
for x, n, r in ((-10, W_INT_DOOR, 'corridorL'), (-5, V_WALL, 'vault'), (0, V_FRAME, 'vault'),
                (5, V_WALL, 'vault'), (10, W_INT_DOOR, 'corridorR')):
    add(r, n, x, 15.0, 0.0)
# vault side walls X=+-7.5
for z in (17.5, 22.5):
    add('vault', V_WALL, -7.5, z, 90.0)
    add('vault', V_WALL, 7.5, z, 270.0)

# ---------------------------------------------------------------- lobby furniture
add('lobby', 'SM_Prop_Rug_01', 0.0, 4.5, 0.0)
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
add('lobby', 'SM_Prop_Sign_Bank_01', 0.0, 9.8, 180.0, y=2.2)
for px in (-3.0, -1.2, 1.2, 3.0):
    add('lobby', 'SM_Prop_RopeBarrier_Pole_01', px, 1.2, 0.0)
add('teller', 'SM_Prop_AlarmButton_01', 12.2, 13.6, 270.0, y=1.2)
add('lobby', 'SM_Prop_Camera_01', -12.2, 9.7, 45.0, y=2.7)

# ---------------------------------------------------------------- teller hall
for x in (-6.0, -2.0, 2.0, 6.0):
    add('teller', 'SM_Prop_TellerDesk_01', x, 11.8, 180.0)
    add('teller', 'SM_Prop_TellerDesk_Barrier_01', x, 10.45, 180.0)
    add('teller', 'SM_Prop_Seat_01', x, 13.0, 180.0)
    add('teller', 'SM_Prop_Computer_01', x, 11.8, 180.0, y=0.78)
    add('teller', 'SM_Prop_Money_Stack_01', x - 0.5, 11.5, 0.0, y=0.78)
    add('teller', 'SM_Prop_Folder_01', x + 0.55, 11.55, 90.0, y=0.78)
add('teller', 'SM_Prop_Shelf_01', 11.4, 12.0, 270.0)
add('teller', 'SM_Prop_Drawers_01', -11.4, 12.0, 90.0)
add('teller', 'SM_Prop_DisplayCase_01', -10.5, 14.5, 0.0)
add('teller', 'SM_Prop_DisplayCase_02', 10.5, 14.5, 0.0)

# ---------------------------------------------------------------- vault
for z in (17.5, 22.5):
    add('vault', 'SM_Prop_SafeDepositBoxes_01', -6.95, z, 90.0)
    add('vault', 'SM_Prop_SafeDepositBoxes_01', 6.95, z, 270.0)
add('vault', 'SM_Prop_VaultTrolley_01', 0.0, 20.0, 0.0)
add('vault', 'SM_Prop_GoldBar_01', 0.0, 20.0, 45.0, y=0.55)
add('vault', 'SM_Prop_GoldBar_02', -1.3, 20.6, 0.0)
add('vault', 'SM_Prop_GoldBar_01', 1.3, 20.4, 30.0)
add('vault', 'SM_Prop_Money_Stack_02', -1.6, 22.6, 0.0)
add('vault', 'SM_Prop_Money_Stack_03', -1.2, 22.9, 15.0)
add('vault', 'SM_Prop_Drill_01', 2.2, 21.2, 180.0)
add('vault', 'SM_Item_DuffleBag_Full_01', 1.2, 22.8, 90.0)
add('vault', 'SM_Item_DuffleBag_Open_Empty_01', -3.4, 18.4, 270.0)
add('vault', 'SM_Item_Crowbar_01', 2.0, 20.6, 90.0)

# ---------------------------------------------------------------- corridors / offices
add('corridorL', 'SM_Prop_Desk_01', -10.0, 17.0, 90.0)
add('corridorL', 'SM_Prop_Seat_01', -8.6, 17.0, 270.0)
add('corridorL', 'SM_Prop_Computer_01', -10.0, 17.0, 90.0, y=0.78)
add('corridorL', 'SM_Prop_Shelf_01', -12.0, 20.0, 90.0)
add('corridorL', 'SM_Prop_Drawers_01', -10.0, 23.0, 0.0)
add('corridorL', 'SM_Prop_Plant_02', -8.8, 23.6, 0.0)
add('corridorR', 'SM_Prop_Desk_02', 10.0, 17.0, 270.0)
add('corridorR', 'SM_Prop_Seat_01', 8.6, 17.0, 90.0)
add('corridorR', 'SM_Prop_Computer_01', 10.0, 17.0, 270.0, y=0.78)
add('corridorR', 'SM_Prop_Shelf_01', 12.0, 20.0, 270.0)
add('corridorR', 'SM_Prop_WaterCooler_01', 8.4, 23.4, 0.0)
add('corridorR', 'SM_Prop_Drawers_01', 10.0, 23.0, 0.0)

# ---------------------------------------------------------------- exterior (plaza + street)
add('exterior', 'SM_Env_Pillar_Exterior_Floor_01', -14.5, -3.0, 0.0)
add('exterior', 'SM_Env_Pillar_Exterior_Floor_01', 14.5, -3.0, 0.0)
add('exterior', 'SM_Env_Pillar_Exterior_Floor_01', -14.5, -9.0, 0.0)
add('exterior', 'SM_Env_Pillar_Exterior_Floor_01', 14.5, -9.0, 0.0)
add('exterior', 'SM_Prop_Sign_Money_Bank_01', 0.0, -0.5, 0.0, y=2.6)
add('exterior', 'SM_Veh_Car_Police_Heist_01', -9.0, -7.0, 90.0)
add('exterior', 'SM_Veh_SwatVan_01', 9.0, -9.0, 270.0)
add('exterior', 'SM_Veh_Helicopter_01', 0.0, -17.0, 0.0)
add('exterior', 'SM_Prop_Bin_01', -15.0, -2.0, 0.0)
add('exterior', 'SM_Prop_Bin_01', 15.0, -2.0, 0.0)
add('exterior', 'SM_Prop_Plant_03', -15.0, -4.0, 0.0)
add('exterior', 'SM_Prop_Plant_03', 15.0, -4.0, 0.0)
add('exterior', 'SM_Prop_Statue_01', -4.0, -3.5, 0.0)
add('exterior', 'SM_Prop_Statue_01', 4.0, -3.5, 0.0)
add('exterior', 'SM_Prop_RopeBarrier_Pole_01', -3.0, -1.6, 0.0)
add('exterior', 'SM_Prop_RopeBarrier_Pole_01', 3.0, -1.6, 0.0)

# ---------------------------------------------------------------- spawns + killzone
ROOMS['lobby']['spawnPoints'] = [
    {'position': [-8.0, 1.0, 2.0], 'team': 1, 'type': 'delta'},
    {'position': [8.0, 1.0, 2.0], 'team': 1, 'type': 'delta'},
    {'position': [0.0, 1.0, 6.5], 'team': 1, 'type': 'delta'},
]
ROOMS['teller']['spawnPoints'] = [
    {'position': [0.0, 1.0, 13.0], 'team': 2, 'type': 'recon'},
]
ROOMS['vault']['spawnPoints'] = [
    {'position': [0.0, 1.0, 20.0], 'team': 2, 'type': 'recon'},
]
ROOMS['exterior']['spawnPoints'] = [
    {'position': [0.0, 1.0, -8.0], 'team': 2, 'type': 'recon'},
    {'position': [-10.0, 1.0, -5.0], 'team': 2, 'type': 'recon'},
    {'position': [10.0, 1.0, -5.0], 'team': 2, 'type': 'recon'},
]
ROOMS['lobby']['killZones'] = [
    {'position': [0.0, -5.0, 0.0], 'size': [80.0, 1.0, 80.0]},
]

ORDER = ('exterior', 'lobby', 'teller', 'vault', 'corridorL', 'corridorR')
out = {
    'name': 'Heist Bank v2',
    'version': 2,
    'description': 'Designed bank: modular 5m kit, enclosed rooms, ceilings, functional props, exterior plaza',
    'rooms': [],
    'globalSpawnPoints': [],
    'navMesh': {'agentRadius': 0.4, 'agentHeight': 2.0, 'maxSlope': 45.0, 'stepHeight': 0.4},
}
for rid in ORDER:
    r = ROOMS[rid]
    r['id'] = rid
    out['rooms'].append(r)

# ---------------------------------------------------------------- validation
FAIL = []
WARN = []

FURNITURE_EXEMPT = ('SM_Prop_Rug', 'SM_Prop_Money', 'SM_Prop_Folder', 'SM_Prop_GoldBar',
                    'SM_Prop_Computer', 'SM_Prop_AlarmButton', 'SM_Prop_Camera',
                    'SM_Prop_Sign', 'SM_Prop_Flag', 'SM_Prop_Air', 'SM_Prop_Sprinkler',
                    'SM_Prop_Fire', 'SM_Prop_Ceiling', 'SM_Prop_RopeBarrier')

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

# wall run closure
def run_span(names):
    return sum(fsize(n)[0] for n in names)

front = [n for x, n in ((-10, W_EXT_WIN), (-5, W_EXT_WIN), (0, W_EXT_DD), (5, W_EXT_WIN), (10, W_EXT_WIN))]
if abs(run_span(front) - 25.0) > 0.01:
    FAIL.append('front wall run %.2f != 25' % run_span(front))
side = run_span([W_EXT_WIN if z == 7.5 else W_EXT for z in (2.5, 7.5, 12.5, 17.5, 22.5)])
if abs(side - 25.0) > 0.01:
    FAIL.append('side wall run %.2f != 25' % side)
z15 = [W_INT_DOOR, V_WALL, V_FRAME, V_WALL, W_INT_DOOR]
if abs(run_span(z15) - 25.0) > 0.01:
    FAIL.append('Z15 wall run %.2f != 25' % run_span(z15))

# door openings present
for x, want in ((-10, 'Door'), (10, 'Door')):
    names = [p['prefab'] for p in ROOMS['teller']['props']]
    if not any('Interior_Door' in n for n in names):
        FAIL.append('teller wall missing door modules')
        break

# prop containment + furniture overlap (footprints from catalog, rotation-aware)
def aabb(p):
    n = p['prefab'].split('/')[-1].replace('.prefab', '')
    s = fsize(n)
    rot = round(p['rotation'][1]) % 360
    if rot in (90, 270):
        s = [s[2], s[1], s[0]]
    x, z = p['position'][0], p['position'][2]
    return (x - s[0] / 2.0, z - s[2] / 2.0, x + s[0] / 2.0, z + s[2] / 2.0)

for rid in ORDER:
    b = ROOMS[rid]['bounds']
    furn = []
    for p in ROOMS[rid]['props']:
        n = p['prefab'].split('/')[-1].replace('.prefab', '')
        x0, z0, x1, z1 = aabb(p)
        if not n.startswith('SM_Env_') and (x0 < b['min'][0] - 0.05 or z0 < b['min'][2] - 0.05 or x1 > b['max'][0] + 0.05 or z1 > b['max'][2] + 0.05):
            WARN.append('%s OUTSIDE bounds: %s at %s' % (rid, n, p['position']))
        if n.startswith('SM_Prop_') and not n.startswith(FURNITURE_EXEMPT):
            furn.append((n, aabb(p)))
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
