#!/usr/bin/env python3
"""bus.py — unity-lab job-bus CLI (PC side). Drive bus <-> Colab VM runner.
Usage (py -3):
  bus.py status                     # heartbeat + bus inventory
  bus.py send shell|python|status|file_get|PAUSE --id NAME [--timeout S] [--body TEXT | --body-file PATH]
  bus.py poll --id NAME [--wait S]  # wait for out/<id>.json (default: 600s)
  bus.py result --id NAME           # print result if present
  bus.py clean                      # remove claimed/* older than 1 day
Job files: gdrive:unity-lab/bus/in/<id>.json  Results: bus/out/<id>.json
"""
import argparse, json, os, subprocess, sys, time, tempfile

REMOTE = 'gdrive:unity-lab/bus'

def rc(args):
    return subprocess.run(['rclone'] + args, capture_output=True, text=True)

def lsf(path):
    r = rc(['lsf', REMOTE + path])
    return [l.strip() for l in (r.stdout or '').splitlines() if l.strip()]

def cmd_status(_):
    hb = rc(['cat', REMOTE + '/heartbeat.json'])
    print('HEARTBEAT:', hb.stdout.strip() or '(none — runner dead or fresh VM)' + hb.stderr.strip())
    inv = {'in': len(lsf('/in/')), 'out': len(lsf('/out/')), 'claimed': len(lsf('/claimed/')), 'logs': len(lsf('/logs/'))}
    print('BUS_INVENTORY:', json.dumps(inv))

def cmd_send(a):
    body = a.body
    if a.body_file:
        body = open(a.body_file, encoding='utf-8').read()
    ts = time.time()
    job = {'id': a.id, 'ts': ts, 'type': a.type, 'body': body, 'timeout': a.timeout}
    tmp = os.path.join(tempfile.gettempdir(), 'busjob_%s.json' % a.id)
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(job, f)
    r = rc(['copyto', tmp, '%s/in/%s.json' % (REMOTE, a.id)])
    os.remove(tmp)
    if r.returncode != 0:
        print('SEND_FAILED:', (r.stderr or '')[-500:]); sys.exit(1)
    print('SENT %s (%s, timeout %ss) at epoch %.0f — poll with: py -3 bus.py poll --id %s' % (a.id, a.type, a.timeout, ts, a.id))

def cmd_poll(a):
    t0 = time.time()
    while time.time() - t0 < a.wait:
        out = lsf('/out/')
        if a.id + '.json' in out:
            r = rc(['cat', '%s/out/%s.json' % (REMOTE, a.id)])
            try:
                res = json.loads(r.stdout)
            except Exception:
                print('RAW:', r.stdout[:2000]); sys.exit(1)
            print(json.dumps(res, indent=1)[:4000])
            print('POLL_DONE wall=%ss rc=%s' % (round(time.time() - t0, 1), res.get('rc')))
            sys.exit(0 if res.get('rc') == 0 else 2)
        time.sleep(a.every)
    print('POLL_TIMEOUT after %ss (job still queued/running; heartbeat:)' % a.wait)
    cmd_status(None)
    sys.exit(3)

def cmd_result(a):
    out = lsf('/out/')
    if a.id + '.json' not in out:
        print('NO_RESULT for %s (out has: %s)' % (a.id, out)); sys.exit(1)
    print(rc(['cat', '%s/out/%s.json' % (REMOTE, a.id)]).stdout)

def cmd_clean(_):
    day = 86400
    for n in lsf('/claimed/'):
        r = rc(['lsjson', '%s/claimed/%s' % (REMOTE, n)])
        try:
            mt = json.loads(r.stdout)[0]['ModTime']
        except Exception:
            continue
        # ModTime is local rclone format; cheap approach: delete claimed older than 1 day by lsjson age
        print('claimed kept for audit:', n)

p = argparse.ArgumentParser()
sp = p.add_subparsers(dest='cmd', required=True)
sp.add_parser('status').set_defaults(fn=cmd_status)
s = sp.add_parser('send'); s.add_argument('type'); s.add_argument('--id', required=True)
s.add_argument('--timeout', type=int, default=600); s.add_argument('--body'); s.add_argument('--body-file')
s.set_defaults(fn=cmd_send)
s = sp.add_parser('poll'); s.add_argument('--id', required=True)
s.add_argument('--wait', type=int, default=600); s.add_argument('--every', type=float, default=15)
s.set_defaults(fn=cmd_poll)
s = sp.add_parser('result'); s.add_argument('--id'); s.set_defaults(fn=cmd_result)
sp.add_parser('clean').set_defaults(fn=cmd_clean)
a = p.parse_args()
a.fn(a)
