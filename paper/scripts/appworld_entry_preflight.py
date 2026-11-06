"""Seal and inventory all fixed development references, with no provider access."""
import argparse
import json
from pathlib import Path
import subprocess
import time

from adaptive_pilot import ROOT, digest, write
from appworld_adaptive_viability import IMAGE, CACHE as PRIOR

BASE = ROOT / 'benchmarks/.cache/appworld_entry_preflight'
CACHE = BASE / 'v2'
OUT = ROOT / 'paper/results/appworld_entry_preflight'
WORKER = ROOT / 'experiments/appworld_entry_preflight/reference_worker.py'


def freeze():
    path = CACHE / 'seal.json'
    if path.exists():
        raise ValueError('do not overwrite frozen preflight')
    previous = json.loads((PRIOR / 'seal.json').read_text())
    files = [Path(__file__).resolve(), WORKER]
    seal = {'schema': 'appworld-entry-preflight-v2', 'prior_seal_sha256': digest(BASE / 'seal.json'), 'amendment': 'Move source hashing outside sandbox execution; all 12 original reference instrumentation failures retained. No task or official grading changes. No model calls.', 'created_unix': time.time(), 'image': IMAGE,
        'tasks': previous['tasks'], 'previous_seal_sha256': digest(PRIOR / 'seal.json'),
        'source_hashes': {str(p.relative_to(ROOT)): digest(p) for p in files},
        'scope': 'Provider-free development reference inventory. All 12 tasks retained; no new model calls, holdout, compiled candidate or certificate.',
        'decision_rule': 'Inspect initial API sequences and source effects. Observed absence of SQL writes alone cannot establish read safety. Authentication remains a write. A preauthenticated entry must be separately validated under identical initialization for every arm; reference calls are not model traces or evidence of automatic compilation.',
        'future_paid_gate': 'No paid run until at least two meaningful recurrent read families have source-audited effects, exact-path positive/negative grading controls and identical entry setup. A new baseline competence pilot requires its own seal and cap.'}
    write(path, seal)
    for p in files:
        target = CACHE / 'sealed_sources' / p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(p.read_bytes())


def run():
    seal = json.loads((CACHE / 'seal.json').read_text())
    for rel, sha in seal['source_hashes'].items():
        if digest(ROOT / rel) != sha:
            raise ValueError('sealed source drift')
    for task in seal['tasks']:
        path = CACHE / 'references' / (task + '.json')
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        write(path, {'task_id': task, 'status': 'started'})
        command = ['docker', 'run', '--rm', '-i', '--network', 'none', '--read-only', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--memory', '4g', '--cpus', '2', '--pids-limit', '128', '--user', '65534:65534',
            '--tmpfs', '/work:rw,nosuid,size=2g,mode=1777', '--tmpfs', '/tmp:rw,nosuid,size=512m',
            '-v', str(WORKER) + ':/worker.py:ro', IMAGE, '-I', '/worker.py']
        completed = subprocess.run(command, input=json.dumps({'task_id': task})+'\n', text=True, capture_output=True, timeout=120)
        path.with_suffix('.stdout').write_text(completed.stdout)
        path.with_suffix('.stderr').write_text(completed.stderr)
        try:
            row = json.loads(completed.stdout)
        except ValueError:
            row = {'task_id': task, 'status': 'failed', 'error': 'invalid worker output'}
        row['returncode'] = completed.returncode
        write(path, row)
        print(json.dumps({'task_id': task, 'status': row['status'], 'reference_success': row.get('reference_success'), 'calls': len(row.get('calls', []))}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['freeze', 'run'])
    args = parser.parse_args()
    freeze() if args.command == 'freeze' else run()
