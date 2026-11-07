"""Trusted driver: runs each query's tool code in a sandbox-exec child with a wall-clock
timeout; on a hang, marks the hung step and reruns the query skipping it."""
import json, subprocess, sys, concurrent.futures as cf

SP = '/private/tmp/claude-501/-Users-rezarahimi-Documents-GitHub-personal-guarded-agentic-compaction/e32926e6-9b43-4050-9573-91248c35ba99/scratchpad'
PY = '/Users/rezarahimi/Documents/GitHub/personal/guarded-agentic-compaction/.venv/bin/python'
DATA = sys.argv[1]
OUT = sys.argv[2]
TIMEOUT = 40


def run_query(qid):
    skip = []
    steps = {}
    n = None
    for attempt in range(8):
        cmd = ['sandbox-exec', '-f', SP + '/sb.sb', PY, '-I', SP + '/runner.py', DATA, str(qid), str(qid + 1), ','.join(map(str, skip))]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, stdin=subprocess.DEVNULL)
            out = p.stdout; hung = False
        except subprocess.TimeoutExpired as e:
            out = (e.stdout or b'').decode() if isinstance(e.stdout, bytes) else (e.stdout or ''); hung = True
        last_start = None
        for line in out.splitlines():
            try:
                r = json.loads(line)
            except Exception:
                continue
            if 'n' in r and 'step' not in r and 'start' not in r:
                n = r['n']
            elif 'start' in r:
                last_start = r['start']
            elif 'step' in r:
                steps[r['step']['i']] = r['step']
                last_start = None
        if not hung:
            break
        if last_start is None:
            break
        skip.append(last_start)
    return {'id': qid, 'n': n, 'steps': [steps[k] for k in sorted(steps)], 'hang_steps': skip}


if __name__ == '__main__':
    with cf.ThreadPoolExecutor(max_workers=14) as ex, open(OUT, 'w') as f:
        for res in ex.map(run_query, range(995)):
            f.write(json.dumps(res, ensure_ascii=False) + '\n'); f.flush()
