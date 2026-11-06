"""Provider-free development reference inventory; never exposed as an agent tool."""
import contextlib
import hashlib
import importlib
import inspect
import io
import json
import os
from pathlib import Path
import re
import sys


def main():
    os.environ['APPWORLD_ROOT'] = '/work'
    Path('/work/data').symlink_to('/opt/world/data', target_is_directory=True)
    from appworld import AppWorld, load_task_ids
    from appworld.evaluator import evaluate_task
    from appworld.requester import Requester
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    task = json.loads(sys.stdin.readline())['task_id']
    if task not in load_task_ids('train'):
        raise ValueError('official train development only')
    original = Requester.request
    calls, sources, active = [], {}, []
    def observed(conn, cursor, statement, parameters, context, executemany):
        sql = re.sub(r'/\*.*?\*/|--[^\n]*', ' ', statement, flags=re.S).lstrip()
        op = sql.split(None, 1)[0].upper() if sql else ''
        if active and op not in {'SELECT', 'EXPLAIN', 'BEGIN', 'COMMIT', 'ROLLBACK', 'SAVEPOINT', 'RELEASE'}:
            active[-1].append(op)
    def traced(self, *args, **kwargs):
        app = kwargs.get('_app_name', args[0] if args else None)
        api = kwargs.get('_api_name', args[1] if len(args) > 1 else None)
        name = str(app) + '.' + str(api)
        arguments = {k: v for k, v in kwargs.items() if k not in {'_app_name', '_api_name', 'client', 'track', 'show', 'raise_on_failure'}}
        operations = []
        active.append(operations)
        try:
            result = original(self, *args, **kwargs)
        finally:
            active.pop()
        calls.append({'tool': name, 'arguments': arguments, 'result': result, 'sql_operations': operations})
        return result
    Requester.request = traced
    event.listen(Engine, 'after_cursor_execute', observed)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            with AppWorld(task_id=task, experiment_name='entry_reference', load_ground_truth=True, ground_truth_mode='full',
                random_seed=20261106, max_api_calls_per_interaction=1000, timeout_seconds=30, raise_on_failure=False) as world:
                public = {app: sorted(docs) for app, docs in world.task.api_docs.items()}
                output = world.execute(world.task.ground_truth.compiled_solution_code + '\nsolution(apis, requester)')
            tracker = evaluate_task(task_id=task, experiment_name='entry_reference', suppress_errors=True)
        # Inspect trusted implementation only after the sandbox has finished.
        for name in sorted({c['tool'] for c in calls}):
            app, api = name.split('.', 1)
            module = importlib.import_module('appworld.apps.' + app + '.apis')
            function = getattr(module, api)
            source = inspect.getsource(function)
            module_path = Path(inspect.getfile(module))
            sources[name] = {'function': source, 'function_sha256': hashlib.sha256(source.encode()).hexdigest(),
                'module_sha256': hashlib.sha256(module_path.read_bytes()).hexdigest(), 'signature': str(inspect.signature(function))}
        print(json.dumps({'task_id': task, 'status': 'completed', 'reference_success': tracker.success,
            'tests': tracker.num_tests, 'passed_tests': tracker.pass_count, 'calls': calls, 'sources': sources,
            'public_apis': public, 'output': output}, default=str))
    finally:
        event.remove(Engine, 'after_cursor_execute', observed)
        Requester.request = original


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'status': 'failed', 'error': type(exc).__name__, 'detail': str(exc)[:500]}))
        raise
