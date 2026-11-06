"""Trusted provider-free checks of a common preauthenticated development entry.

No model-generated Python and no reference/test access. Host-supplied public calls
are isolated controls, not a new adaptive trajectory or an admitted GAC artifact.
"""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys


def tree(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(path).rglob('*')) if p.is_file()}


def public_call(world, public, command):
    if set(command) != {'tool', 'arguments'} or not isinstance(command['arguments'], dict):
        raise ValueError('invalid command')
    name = command['tool']
    if name not in public:
        raise ValueError('unknown or private API')
    if set(command['arguments']) & {'_app_name', '_api_name', 'client', 'track', 'show', 'raise_on_failure'}:
        raise ValueError('reserved requester argument')
    app, api = name.split('.', 1)
    return world.requester.request(app, api, **command['arguments'])


def main():
    os.environ['APPWORLD_ROOT'] = '/work'
    Path('/work/data').symlink_to('/opt/world/data', target_is_directory=True)
    from appworld import AppWorld, load_task_ids
    from appworld.evaluator import evaluate_task
    request = json.loads(sys.stdin.readline())
    task = request['task_id']
    if task not in load_task_ids('train'):
        raise ValueError('official train development only')
    if len(request['commands']) > 300:
        raise ValueError('control API limit')
    with contextlib.redirect_stdout(io.StringIO()):
        world = AppWorld(task_id=task, experiment_name='entry_control', load_ground_truth=False,
            ground_truth_mode='minimal', random_seed=20261106, max_api_calls_per_interaction=1000,
            timeout_seconds=30, raise_on_failure=False)
    public = {app+'.'+api for app, docs in world.task.api_docs.items() for api in docs}
    setup, calls, tokens = [], [], {}
    try:
        def call(tool, arguments, rows):
            command = {'tool': tool, 'arguments': arguments}
            with contextlib.redirect_stdout(io.StringIO()):
                result = public_call(world, public, command)
            rows.append(command | {'result': result})
            return result
        profile = call('supervisor.show_profile', {}, setup)
        passwords = {r['account_name']: r['password'] for r in call('supervisor.show_account_passwords', {}, setup)}
        # Same rule for every task/arm; no oracle chooses which apps to authenticate.
        apps = sorted(name.split('.')[0] for name in public if name.endswith('.login'))
        for app in apps:
            result = call(app+'.login', {'username': profile['phone_number' if app == 'phone' else 'email'],
                'password': passwords[app]}, setup)
            if not isinstance(result, dict) or not isinstance(result.get('access_token'), str):
                raise ValueError('common entry authentication failed')
            tokens[app] = result['access_token']
        with contextlib.redirect_stdout(io.StringIO()):
            world.save()
        before = tree(Path(world.output_db_home_path_on_disk))
        for command in request['commands']:
            tool = command['tool']
            if tool.endswith('.login') or tool in {'supervisor.show_profile', 'supervisor.show_account_passwords'}:
                raise ValueError('control must start after common entry; no hidden reinitialization')
            arguments = dict(command['arguments'])
            if 'access_token' in arguments:
                # Bind this control to its actual common entry, never an oracle token.
                arguments['access_token'] = tokens[tool.split('.')[0]]
            call(tool, arguments, calls)
        with contextlib.redirect_stdout(io.StringIO()):
            world.save()
        after = tree(Path(world.output_db_home_path_on_disk))
    finally:
        with contextlib.redirect_stdout(io.StringIO()):
            world.close()
    with contextlib.redirect_stdout(io.StringIO()):
        tracker = evaluate_task(task_id=task, experiment_name='entry_control', suppress_errors=True)
    print(json.dumps({'task_id': task, 'status': 'completed', 'setup': setup, 'setup_apps': apps,
        'calls': calls, 'saved_state_before': before, 'saved_state_after': after,
        'saved_state_unchanged': before == after, 'success': tracker.success,
        'tests': tracker.num_tests, 'passed_tests': tracker.pass_count}, default=str))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'status': 'failed', 'error': type(exc).__name__, 'detail': str(exc)[:500]}))
        raise
