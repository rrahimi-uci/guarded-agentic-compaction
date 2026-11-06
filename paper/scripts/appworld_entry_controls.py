"""Freeze and run provider-free common-entry controls; never invokes a model."""
import argparse
import json
from pathlib import Path
import subprocess
import time

from adaptive_pilot import ROOT, digest, write
from appworld_entry_preflight import BASE, CACHE, IMAGE

CONTROL = BASE / 'entry_controls'
WORKER = ROOT / 'experiments/appworld_entry_preflight/entry_worker.py'
PREFIXES = {'songs': 'spotify.show_song_library', 'playlists': 'spotify.show_playlist_library'}


def commands_for(row, mode):
    if mode == 'reference':
        return [{'tool': c['tool'], 'arguments': c['arguments']} for c in row['calls']
                if not c['tool'].endswith('.login') and c['tool'] not in {'supervisor.show_profile', 'supervisor.show_account_passwords'}]
    if mode == 'empty':
        return []
    if mode == 'false_completion':
        return [{'tool': 'supervisor.complete_task', 'arguments': {'answer': 'UNSUPPORTED ANSWER'}}]
    if mode in PREFIXES:
        return [{'tool': PREFIXES[mode], 'arguments': {'access_token': 'BOUND_FROM_ENTRY', 'page_index': i}} for i in (0, 1)]
    raise ValueError('unsealed control')


def freeze():
    path = CONTROL / 'seal.json'
    if path.exists():
        raise ValueError('control seal already exists')
    prior = json.loads((CACHE / 'seal.json').read_text())
    records = {task: CACHE / 'references' / (task+'.json') for task in prior['tasks']}
    if not all(json.loads(p.read_text()).get('reference_success') is True for p in records.values()):
        raise ValueError('all unchanged references must pass first')
    files = [Path(__file__).resolve(), WORKER]
    seal = {'schema': 'appworld-common-entry-controls-v1', 'created_unix': time.time(), 'image': IMAGE,
        'tasks': prior['tasks'], 'modes': ['reference', 'empty', 'false_completion', 'songs', 'playlists'],
        'source_hashes': {str(p.relative_to(ROOT)): digest(p) for p in files},
        'reference_hashes': {task: digest(p) for task, p in records.items()},
        'entry': 'Two actual supervisor reads, followed by login to every publicly exposed app with login API in sorted order. Phone uses phone_number; others use email. Credentials come only from public supervisor responses. Every future arm would receive identical setup and its costs.',
        'interpretation': 'Reference controls validate saved-state grading under a new common entry; they are not model trajectories. Song/playlist probes use two fixed pages and compare all saved DB files. Sampled state equality is not a universal effect proof. No compiler artifact, calibration, final test or paid execution is authorized by this result.'}
    write(path, seal)
    for p in files:
        target = CONTROL / 'sealed_sources' / p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(p.read_bytes())


def run():
    seal = json.loads((CONTROL / 'seal.json').read_text())
    for rel, sha in seal['source_hashes'].items():
        if digest(ROOT / rel) != sha:
            raise ValueError('control source drift')
    for task in seal['tasks']:
        source = CACHE / 'references' / (task+'.json')
        if digest(source) != seal['reference_hashes'][task]:
            raise ValueError('reference input drift')
        row = json.loads(source.read_text())
        for mode in seal['modes']:
            path = CONTROL / 'results' / task / (mode+'.json')
            if path.exists():
                continue
            commands = commands_for(row, mode)
            write(path, {'task_id': task, 'mode': mode, 'status': 'started'})
            command = ['docker', 'run', '--rm', '-i', '--network', 'none', '--read-only', '--cap-drop', 'ALL',
                '--security-opt', 'no-new-privileges', '--memory', '4g', '--cpus', '2', '--pids-limit', '128', '--user', '65534:65534',
                '--tmpfs', '/work:rw,nosuid,size=2g,mode=1777', '--tmpfs', '/tmp:rw,nosuid,size=512m',
                '-v', str(WORKER)+':/worker.py:ro', IMAGE, '-I', '/worker.py']
            result = subprocess.run(command, input=json.dumps({'task_id': task, 'commands': commands})+'\n',
                text=True, capture_output=True, timeout=120)
            path.with_suffix('.stdout').write_text(result.stdout)
            path.with_suffix('.stderr').write_text(result.stderr)
            try:
                record = json.loads(result.stdout)
            except ValueError:
                record = {'status': 'failed', 'error': 'invalid worker output'}
            passed = result.returncode == 0 and record.get('status') == 'completed' and record.get('tests', 0) > 0
            if mode in PREFIXES:
                passed = passed and record.get('saved_state_unchanged') is True and all(isinstance(c['result'], list) for c in record.get('calls', [])) and len(record.get('calls', [])) == 2
            else:
                passed = passed and record.get('success') is (mode == 'reference')
            record.update(task_id=task, mode=mode, returncode=result.returncode, passed=passed)
            write(path, record)
            print(json.dumps({'task_id': task, 'mode': mode, 'passed': passed}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['freeze', 'run'])
    args = parser.parse_args()
    freeze() if args.command == 'freeze' else run()
