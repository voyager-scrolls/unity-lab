#!/usr/bin/env python3
# runner.py — unity-lab Drive job-bus runner (VM side). Canonical copy: bus-jobs/runner.py
# Fetched live from /content/runner.py via the bus itself (file_get + line-range jobs).
# Embedded into unity-lab.ipynb bridge cell by the builder (P3.5).
import os, sys, json, time, socket, hashlib, subprocess, glob, shutil

BUS = '/content/drive/MyDrive/unity-lab/bus'
IN, CLAIMED, OUT, LOGS = [os.path.join(BUS, d) for d in ('in', 'claimed', 'out', 'logs')]
VERSION, POLL = 'runner-v1', 10

ERR = open('/content/bus_runner.err', 'a', buffering=1)
sys.stdout = open('/content/bus_runner.log', 'a', buffering=1)
sys.stderr = ERR


def fp():
    return hashlib.sha1((socket.gethostname() + ':unity-lab').encode()).hexdigest()[:12]


def tail(s, n=1500):
    s = s or ''
    return s[-n:]


def write_json(path, obj):
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(obj, f)
    os.replace(tmp, path)


def heartbeat(busy):
    hb = {'version': VERSION, 'fp': fp(), 'ts': time.time(), 'busy': busy,
          'paused': os.path.exists('/content/bus_paused'),
          'disk_gb': round(os.statvfs('/content').f_bavail * os.statvfs('/content').f_frsize / 1e9, 1)}
    write_json(os.path.join(BUS, 'heartbeat.json'), hb)


def write_out(jid, payload):
    payload['version'] = VERSION
    write_json(os.path.join(OUT, jid + '.json'), payload)
    with open(os.path.join(BUS, 'audit.jsonl'), 'a') as f:
        f.write(json.dumps(payload) + '\n')


def run_job(path):
    name = os.path.basename(path)
    claim = os.path.join(CLAIMED, name)
    try:
        os.rename(path, claim)
    except OSError:
        return
    try:
        job = json.load(open(claim, errors='ignore'))
    except Exception as e:
        write_out(name.replace('.json', ''), {'id': name, 'rc': 4, 'err': 'bad json %r' % e, 'ts': time.time()})
        return
    jid = str(job.get('id', name.replace('.json', '')))
    t0, typ, body = time.time(), str(job.get('type', 'shell')), str(job.get('body', ''))
    to = int(job.get('timeout', 600))
    res = {'id': jid, 'type': typ, 'ts': t0}
    try:
        if typ in ('shell', 'python'):
            cmd = ['bash', '-lc', body] if typ == 'shell' else [sys.executable, '-c', body]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=to)
            res.update(rc=r.returncode, out=tail(r.stdout), err=tail(r.stderr))
        elif typ == 'status':
            res.update(rc=0, out='RUNNER_ALIVE %s' % VERSION, err='')
        elif typ == 'file_get':
            p = body
            if os.path.exists(p):
                sz = os.path.getsize(p)
                if sz <= 200000:
                    res.update(rc=0, out=open(p, errors='ignore').read(), err='size=%d' % sz)
                else:
                    shutil.copyfile(p, os.path.join(LOGS, jid + '.bin'))
                    res.update(rc=0, out='TOO_BIG_SEE_LOGS/%s.bin' % jid, err='size=%d' % sz)
            else:
                res.update(rc=2, out='', err='no such file: %s' % p)
        elif typ == 'PAUSE':
            if body.strip() == 'off':
                os.remove('/content/bus_paused')
                res.update(rc=0, out='UNPAUSED', err='')
            else:
                open('/content/bus_paused', 'w').write('1')
                res.update(rc=0, out='PAUSED', err='')
        else:
            res.update(rc=3, out='', err='unknown type %s' % typ)
    except subprocess.TimeoutExpired as e:
        res.update(rc=124, out=tail((e.stdout or b'').decode(errors='ignore') if isinstance(e.stdout, bytes) else str(e.stdout or '')), err='TIMEOUT %ss' % to)
    except Exception as e:
        res.update(rc=1, out='', err='EXC %r' % e)
    res['wall'] = round(time.time() - t0, 1)
    write_out(jid, res)


busy = False
while True:
    try:
        if os.path.exists('/content/bus_paused'):
            heartbeat(busy)
        else:
            jobs = sorted(glob.glob(os.path.join(IN, '*.json')))
            busy = bool(jobs)
            heartbeat(busy)
            for j in jobs:
                busy = True
                run_job(j)
    except Exception as e:
        print('LOOP_EXC %r' % e, file=sys.stderr)
    time.sleep(POLL)
