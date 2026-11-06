"""Provider-free validation and diagnostic regrading after a persistence defect.

Never invokes a model. Frozen originals remain untouched. Replayed traces are
not fresh adaptive trials and cannot rescue this interrupted comparison.
"""
import argparse
import asyncio
import json
import time

from adaptive_pilot import ROOT, digest, write
from appworld_adaptive_viability import BASE, CACHE, WORKER, worker, verify_records

REPAIR = BASE / 'persistence_repair'


def reference_commands(record):
    commands = []
    for call in record['calls']:
        arguments = dict(call['kwargs'])
        positional = call['args']
        app = arguments.pop('_app_name', positional[0] if positional else None)
        api = arguments.pop('_api_name', positional[1] if len(positional) > 1 else None)
        for key in ('client', 'track', 'show', 'raise_on_failure'):
            arguments.pop(key, None)
        if not app or not api:
            raise ValueError('reference call identity missing')
        commands.append({'app': app, 'api': api, 'arguments': arguments})
    return commands


def freeze():
    verify_records()
    path = REPAIR / 'plan.json'
    if path.exists():
        raise ValueError('repair plan already sealed')
    completed = sorted(str(p.relative_to(BASE)) for p in (CACHE / 'episodes').glob('*/*.json')
                       if json.loads(p.read_text())['status'] == 'completed')
    reference = BASE / 'diagnostics/compatibility.json'
    sources = [WORKER, ROOT / 'paper/scripts/appworld_adaptive_viability.py', ROOT / 'paper/scripts/repair_appworld_viability.py']
    plan = {'schema': 'appworld-persistence-repair-v1', 'created_unix': time.time(),
        'reason': 'Confirmed persistence defect: identical known-correct public API calls pass 0/6 before explicit save and 6/6 with save. world.execute saved reference controls; direct Requester calls did not save agent state.',
        'original_seal_sha256': digest(CACHE / 'seal.json'),
        'stop_sha256': digest(CACHE / 'execution_stop.json'),
        'source_hashes': {str(p.relative_to(ROOT)): digest(p) for p in sources},
        'completed_records': {rel: digest(BASE / rel) for rel in completed},
        'positive_control_task': 'c901732_2', 'reference_calls_sha256': digest(reference),
        'policy': 'No paid retries or continuation. Validate the corrected actual agent path with a known-correct sequence and empty/false-completion controls. Replay all completed histories once, verify public context and every API result exactly, and grade saved state. Replays are diagnostic only; retain failed/interrupted/unstarted arms and original grades. No comparative quality inference.'}
    write(path, plan)
    for p in sources:
        target = REPAIR / 'sealed_sources' / p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(p.read_bytes())


async def replay(task, commands, path, *, original=None, expected_success=None, expected_outputs=None):
    if path.exists():
        return
    row = {'task_id': task, 'status': 'started', 'commands': commands, 'messages': []}
    write(path, row)
    start = time.monotonic()
    try:
        async with worker({'mode': 'agent', 'task_id': task}, path) as (send, receive):
            context = await receive()
            if context.get('type') != 'context':
                raise ValueError('missing context')
            row['context'] = context
            row['results'] = []
            for command in commands:
                await send({'type': 'call', **command})
                result = await receive()
                if result.get('type') != 'result':
                    raise ValueError('missing API result')
                row['results'].append(result)
            await send({'type': 'finish'})
            evaluation = await receive()
            if evaluation.get('type') != 'evaluation' or evaluation['tests'] <= 0:
                raise ValueError('missing nonempty evaluation')
            row['evaluation'] = evaluation
        observed = [r['result'] for r in row['results']]
        row['observations_match'] = expected_outputs is None or observed == expected_outputs
        row['context_matches'] = original is None or context == original['context']
        row['control_passed'] = expected_success is None or evaluation['success'] is expected_success
        row['status'] = 'completed'
        row['diagnostic_valid'] = row['observations_match'] and row['context_matches'] and row['control_passed']
    except Exception as exc:
        row.update(status='failed', diagnostic_valid=False, error=type(exc).__name__, detail=str(exc))
        raise
    finally:
        row['seconds'] = time.monotonic() - start
        write(path, row)
    print(json.dumps({k: row[k] for k in ('task_id', 'status', 'diagnostic_valid')} | {'success': evaluation['success']}), flush=True)


async def run():
    plan = json.loads((REPAIR / 'plan.json').read_text())
    verify_records()
    if digest(CACHE / 'seal.json') != plan['original_seal_sha256'] or digest(CACHE / 'execution_stop.json') != plan['stop_sha256']:
        raise ValueError('original attempt drift')
    for rel, sha in plan['source_hashes'].items():
        if digest(ROOT / rel) != sha:
            raise ValueError('repair source drift')
    reference = BASE / 'diagnostics/compatibility.json'
    if digest(reference) != plan['reference_calls_sha256']:
        raise ValueError('reference trace drift')
    record = json.loads(reference.read_text())
    task = plan['positive_control_task']
    for name, commands, expected, outputs in [
        ('reference_public_calls', reference_commands(record), True, [c['response'] for c in record['calls']]),
        ('empty', [], False, []),
        ('false_completion', [{'app': 'supervisor', 'api': 'complete_task', 'arguments': {'answer': 'UNSUPPORTED ANSWER'}}], False, None),
    ]:
        path = REPAIR / 'controls' / (name + '.json')
        await replay(task, commands, path, expected_success=expected, expected_outputs=outputs)
        if not json.loads(path.read_text()).get('diagnostic_valid'):
            raise ValueError('direct-path control failed; no diagnostic regrading')
    for rel, sha in plan['completed_records'].items():
        path = BASE / rel
        if digest(path) != sha:
            raise ValueError('original completed record changed')
        original = json.loads(path.read_text())
        commands = [{'app': c['tool'].split('.', 1)[0], 'api': c['tool'].split('.', 1)[1], 'arguments': c['arguments']} for c in original['calls']]
        await replay(original['task_id'], commands, REPAIR / 'regrades' / original['task_id'] / (original['arm'] + '.json'),
                     original=original, expected_outputs=[c['result'] for c in original['calls']])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['freeze', 'run'])
    args = parser.parse_args()
    if args.command == 'freeze':
        freeze()
    else:
        asyncio.run(run())
