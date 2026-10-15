"""Sealed, matched API-task comparison of GAC and an offline AWM adaptation."""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import sys
import time
from collections import Counter
from dataclasses import asdict, replace
from importlib.metadata import version
from itertools import permutations
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'paper/scripts'))
import awm_api_adapter as awm
import fresh_safeguard_comparison as shared
import github_live_study as fixed
from complete_live_recovery import usage_account, price_usage
from recovery_observation import ObservedModel, safe_error

OUT = ROOT / 'experiments/matched_reuse_baseline'
ARMS = ('baseline', 'gac', 'awm_offline_adapted')
SEED = 20261019
CAP = 400.0
CONCURRENCY = 4
FIELDS = ('category_correct', 'issue_number_correct', 'evidence_label_correct',
          'title_exact', 'state_exact', 'comment_count_exact', 'evidence_excerpt_exact')
DEPS = ('openai', 'openai-agents', 'pydantic', 'numpy', 'scipy', 'pandas', 'pyarrow', 'scikit-learn')
METRICS = ('requests', 'total_tool_calls', 'total_tokens', 'estimated_cost_usd', 'wall_latency_ms')


def task(number):
    return f'Triage this public GitHub issue snapshot record. issue_number={number}'


def settings():
    from agents import ModelSettings
    from agents.model_settings import ModelRetrySettings
    from openai.types.shared import Reasoning
    return ModelSettings(reasoning=Reasoning(effort='low'), verbosity='low',
                         parallel_tool_calls=False, store=False, max_tokens=2048,
                         retry=ModelRetrySettings(max_retries=0))


def schedule(pilot, primary):
    orders = list(permutations(ARMS))
    return [dict(index=i, **job) for i, job in enumerate(
        {'group': group, 'issue_number': number, 'arm': arm}
        for group, numbers in [('pilot', pilot), ('primary', primary)]
        for pos, number in enumerate(numbers) for arm in orders[pos % 6])]


def select(store, excluded):
    eligible = [n for n, row in store.items() if n not in excluded and not row.get('pull_request')]
    eligible.sort(key=lambda n: shared.object_digest(['matched-reuse', SEED, n]))
    if len(eligible) < 126:
        raise ValueError('insufficient unused records; no reuse')
    return eligible[:6], eligible[6:126], len(eligible)


def discovery_examples(checkpoint):
    eligible = [row for row in checkpoint['results'] if fixed.compiler_eligible(SimpleNamespace(**row), shared.TASK)]
    if len(eligible) != 130:
        raise ValueError('discovery eligibility changed')
    return [{'confirmed_task': task(row['issue_number']), 'action_reprs':
             [tool + '(' + json.dumps(args, sort_keys=True) + ')'
              for tool, args in zip(row['tool_sequence'], row['tool_arguments'])]} for row in eligible]


def hashes():
    paths = list((ROOT/'src').rglob('*.py')) + list((ROOT/'paper/scripts').glob('*.py'))
    paths += list((OUT/'vendor').rglob('*')) + [OUT/'README.md', ROOT/'demos/live_runtime.py']
    return {str(p.relative_to(ROOT)): shared.digest(p) for p in sorted(paths) if p.is_file()}


def budget_sources():
    recovery = ROOT/'experiments/live_recovery_completion'
    fresh = ROOT/'experiments/fresh_safeguards/artifacts'
    previous = json.loads((recovery/'analysis.json').read_text())
    if previous['checkpoint_sha256'] != shared.digest(recovery/'checkpoint.json'):
        raise ValueError('prior recovery checkpoint drift')
    for path in [recovery/'checkpoint.json', fresh/'checkpoint.json']:
        if json.loads(path.read_text())['pending']:
            raise ValueError('unresolved prior attempt')
    fresh_checkpoint = json.loads((fresh/'checkpoint.json').read_text())
    summary = json.loads((fresh/'summary.json').read_text())
    fresh_cost = sum(a['recorded_resource_totals']['estimated_cost_usd'] for a in summary['arms'].values())
    if any(a['failed'] or not a['resource_accounting_complete'] for a in summary['arms'].values()):
        raise ValueError('prior fresh costs require reconciliation')
    if (fresh_checkpoint['unknown_cost_reserve_usd'] != 0
            or not math.isclose(sum(r['metrics']['estimated_cost_usd'] for r in fresh_checkpoint['rows']), fresh_cost, abs_tol=1e-10)
            or not math.isclose(fresh_cost, .26863865, abs_tol=1e-10)):
        raise ValueError('unexpected prior fresh cost')
    paths = [recovery/'analysis.json', recovery/'checkpoint.json', recovery/'VALIDATION.md',
             fresh/'summary.json', fresh/'checkpoint.json']
    return {'source_hashes': {str(p.relative_to(ROOT)): shared.digest(p) for p in paths},
            'recovery_estimate_and_reserve_usd': previous['aggregate_estimate_and_reserve_usd'],
            'fresh_estimate_usd': fresh_cost,
            'prior_estimate_and_reserve_usd': previous['aggregate_estimate_and_reserve_usd']+fresh_cost}


def prepare(out=OUT):
    if any((out/name).exists() for name in ('seal.json', 'checkpoint.json', 'memory_seal.json')):
        raise ValueError('study already sealed; use verify')
    started = time.perf_counter()
    runtime = shared.runtime()
    reconstruction_ms = (time.perf_counter()-started)*1000
    store, source, tools, catalog, manifest, registry, _ = runtime
    excluded, exclusions = shared.exclusion_audit(ROOT/'paper/results')
    for name in ('fresh_safeguards', 'safeguard_mechanisms', 'live_safeguard_recovery', 'live_recovery_completion'):
        for p in sorted((ROOT/'experiments'/name).rglob('*.json')):
            ids = shared.used_ids(json.loads(p.read_text()))
            if ids:
                excluded.update(ids)
                exclusions[str(p.relative_to(ROOT))] = shared.digest(p)
    pilot, primary, available = select(store, excluded)
    discovery_path = ROOT/'paper/results/github_natural_replication/discovery_checkpoint.json'
    discovery = json.loads(discovery_path.read_text())
    if set(pilot+primary) & {r['issue_number'] for r in discovery['results']}:
        raise ValueError('discovery/evaluation leakage')
    examples = discovery_examples(discovery)
    request = awm.induction_request(examples, shared.MODEL,
        [{'name': t.name, 'description': t.description, 'parameters': t.params_json_schema} for t in tools])
    from demos.live_runtime import MODEL_PRICES
    probe = shared.probe(pilot+primary, store, catalog, manifest, {'gac': registry})
    # The reused probe also emits a recurrence-only diagnostic; it is not an arm here.
    probe['outcomes'].pop('recurrence_only')
    for row in probe['records']:
        row['arms'].pop('recurrence_only')
    frozen = {'schema': 'matched-reuse-baseline/v1', 'provider_calls_executed': 0,
        'model': shared.MODEL, 'task': shared.TASK, 'seed': SEED,
        'code_hashes': hashes(), 'environment': {p: version(p) for p in DEPS},
        'source': source, 'vendor': awm.verify_vendor(), 'available_unused_issues': available,
        'excluded_ids': sorted(excluded), 'exclusion_source_hashes': exclusions,
        'pilot_numbers': pilot, 'primary_numbers': primary, 'schedule': schedule(pilot, primary),
        'manifest_compatibility_key': manifest.compatibility_key(), 'artifact': registry.artifacts[0].to_dict(),
        'reconstruction_wall_latency_ms': reconstruction_ms,
        'discovery_sha256': shared.digest(discovery_path), 'eligible_discovery_traces': len(examples),
        'induction_request': request, 'probe': probe, 'price_table': asdict(MODEL_PRICES[shared.MODEL]),
        'settings': settings().to_json_dict(), 'max_turns': 8, 'timeout_seconds': 120,
        'concurrency': CONCURRENCY, 'approved_aggregate_cap_usd': CAP, 'budget': budget_sources()}
    shared.write_json(out/'seal.json', frozen)
    return frozen


def verify(out=OUT):
    frozen = json.loads((out/'seal.json').read_text())
    if frozen['code_hashes'] != hashes() or frozen['environment'] != {p: version(p) for p in DEPS}:
        raise ValueError('sealed source or environment drift')
    for group in ('exclusion_source_hashes',):
        for relative, expected in frozen[group].items():
            if shared.digest(ROOT/relative) != expected:
                raise ValueError('sealed exclusion source drift')
    if frozen['budget'] != budget_sources() or frozen['settings'] != settings().to_json_dict():
        raise ValueError('budget or model configuration drift')
    runtime = shared.runtime()
    store, source, _, _, manifest, registry, _ = runtime
    if (source != frozen['source'] or manifest.compatibility_key() != frozen['manifest_compatibility_key']
            or registry.artifacts[0].to_dict() != frozen['artifact']):
        raise ValueError('runtime reproduction changed')
    pilot, primary, available = select(store, set(frozen['excluded_ids']))
    if (pilot != frozen['pilot_numbers'] or primary != frozen['primary_numbers']
            or available != frozen['available_unused_issues'] or schedule(pilot, primary) != frozen['schedule']):
        raise ValueError('cohort/schedule drift')
    return frozen, runtime


def record():
    return {'stage': 'start', 'requests_started': 0, 'usage_observations': [], 'continuation_calls': []}


def finish(row, prices, started):
    usage, invalid, totals = usage_account(row, prices)
    totals['wall_latency_ms'] = (time.perf_counter()-started)*1000
    row.update(usage=usage, invalid_usage_indices=invalid, metrics=totals,
               unknown_cost_reserve_usd=1.0 if row['status']=='failed' else 0.0)
    return row


def observed_tools(tools, row):
    result = []
    for tool in tools:
        async def invoke(context, args_json, *, original=tool.on_invoke_tool, name=tool.name):
            call = {'tool': name, 'arguments': json.loads(args_json), 'status': 'started'}
            row['continuation_calls'].append(call)
            row['stage'] = 'tool_execution'
            try:
                value = await original(context, args_json)
                call.update(status='ok', output_digest=shared.object_digest(json.loads(value)))
                return value
            except Exception:
                call['status'] = 'failed'
                raise
        result.append(replace(tool, on_invoke_tool=invoke))
    return result


def quality(number, answer, calls, store):
    source = store[number]
    scenario = fixed.Scenario(number, fixed.category_for(source['labels']), tuple(source['labels']),
                              source['html_url'], source['day'], source['state'])
    graded = fixed.grade(scenario, answer, [c['tool'] for c in calls], [c['arguments'] for c in calls],
                        task_design=shared.TASK, source_record=source)
    return graded


def model_input(number, arm, memory):
    return (awm.memory_messages(memory) if arm == 'awm_offline_adapted' else []) + [
        {'role': 'user', 'content': task(number)}]


async def execute(job, runtime, memory, prices, provider_model):
    from agents import RunConfig, Runner
    from guarded_agentic_compaction.runtime.model_provider import CompactingModel
    store, _, tools, catalog, manifest, registry, _ = runtime
    row = {**record(), **job}
    started = time.perf_counter()
    compacting = None
    try:
        inp = model_input(job['issue_number'], job['arm'], memory)
        row['model_input_digest'] = shared.object_digest(inp)
        model = ObservedModel(provider_model, row)
        if job['arm']=='gac':
            compacting = CompactingModel(model, registry=registry, catalog=catalog, manifest=manifest,
                mode='live', entry_state_fn=lambda _: {'issue_number': job['issue_number']},
                partition_fn=lambda _input, _entry: {})
            model = compacting
        agent = fixed.make_agent(model, observed_tools(tools, row), shared.TASK)
        agent.model_settings = settings()
        result = await asyncio.wait_for(Runner.run(agent, inp, max_turns=8,
            run_config=RunConfig(tracing_disabled=True)), timeout=120)
        row['stage'] = 'answer_validation'
        row['answer'] = fixed.ExtractiveIssueTriageAnswer.model_validate(result.final_output).model_dump()
        row['quality'] = quality(job['issue_number'], row['answer'], row['continuation_calls'], store)
        row['correct'] = all(row['quality'][field] for field in FIELDS)
        row['stage'] = 'usage_validation'
        if not row['usage_observations'] or len(row['usage_observations']) != row['requests_started']:
            raise ValueError('missing response accounting')
        for raw in row['usage_observations']:
            price_usage(raw, prices)
        row['status'] = 'completed'
    except Exception as exc:
        row.update(status='failed', error=safe_error(exc, row['stage']))
    if compacting:
        row['dispatch'] = compacting.dispatcher.telemetry.as_dict()
    return finish(row, prices, started)


async def induce(frozen, client):
    row = record()
    started = time.perf_counter()
    try:
        row['stage'] = 'induction_request'
        row['requests_started'] = 1
        response = await asyncio.wait_for(client.responses.create(model=shared.MODEL,
            input=frozen['induction_request']['messages'], max_output_tokens=1024,
            reasoning={'effort': 'low'}, text={'verbosity': 'low'}, store=False), timeout=120)
        u = response.usage
        row['usage_observations'].append({'input_tokens': u.input_tokens, 'output_tokens': u.output_tokens,
            'total_tokens': u.total_tokens, 'cached_input_tokens': u.input_tokens_details.cached_tokens,
            'cache_write_tokens': getattr(u.input_tokens_details, 'cache_write_tokens', 0)})
        row['stage'] = 'induction_validation'
        row['response_status'] = response.status
        row['text'] = response.output_text
        if response.status != 'completed':
            raise ValueError('induction incomplete or truncated')
        row['memory'] = awm.filter_memory(row['text'])
        for raw in row['usage_observations']:
            price_usage(raw, frozen['price_table'])
        row['status'] = 'completed'
    except Exception as exc:
        row.update(status='failed', error=safe_error(exc, row['stage']))
    return finish(row, frozen['price_table'], started)


def budget_total(frozen, state):
    rows = state['rows'] + ([state['induction']] if state['induction'] else [])
    return frozen['budget']['prior_estimate_and_reserve_usd'] + len(state['pending']) + sum(
        r['metrics']['estimated_cost_usd'] + r['unknown_cost_reserve_usd'] for r in rows)


def reserve(frozen, state, key, planned):
    if not math.isfinite(frozen['approved_aggregate_cap_usd']) or frozen['approved_aggregate_cap_usd'] <= 0:
        raise ValueError('invalid cap')
    if key in state['pending']:
        raise ValueError('duplicate pending attempt')
    if budget_total(frozen, state) + 1 > frozen['approved_aggregate_cap_usd']:
        state['halt_reason'] = 'estimated_spend_guard'
        return False
    state['pending'][key] = planned
    return True


def progress(frozen, state):
    return {'attempted': len(state['rows']), 'scheduled': len(frozen['schedule']),
        'completed': sum(r['status']=='completed' for r in state['rows']),
        'pending': len(state['pending']), 'halt_reason': state['halt_reason'],
        'aggregate_estimate_and_reserve_usd': budget_total(frozen, state)}


def audit_usage(row, prices):
    usage, invalid, totals = usage_account(row, prices)
    if usage != row['usage'] or invalid != row['invalid_usage_indices']:
        raise ValueError('usage audit mismatch')
    if any(not math.isclose(row['metrics'][k], v, abs_tol=1e-12, rel_tol=1e-12) for k,v in totals.items()):
        raise ValueError('cost/metric audit mismatch')
    if row['status'] not in ('completed', 'failed') or row['unknown_cost_reserve_usd'] != (1 if row['status']=='failed' else 0):
        raise ValueError('invalid status/reserve')
    if row['status']=='completed' and (invalid or not usage or len(usage)!=row['requests_started']):
        raise ValueError('incomplete successful accounting')


def audit(frozen, runtime, state, out):
    if state['seal_sha256'] != shared.object_digest(frozen) or state['pending']:
        raise ValueError('checkpoint identity or unresolved pending attempt')
    memory = ''
    if state['induction']:
        audit_usage(state['induction'], frozen['price_table'])
        if state['induction']['status']=='completed':
            memory = awm.filter_memory(state['induction']['text'])
            expected = {'seal_sha256': shared.object_digest(frozen),
                        'induction_sha256': shared.object_digest(state['induction']), 'memory': memory}
            if (json.loads((out/'memory_seal.json').read_text()) != expected
                    or memory != state['induction']['memory']):
                raise ValueError('frozen memory drift')
    if state['rows'] and not memory:
        raise ValueError('evaluation before successful induction')
    seen = set()
    import recurrence_only_ablation as replay
    for row in state['rows']:
        index = row['index']
        if type(index) is not int or index < 0 or index >= len(frozen['schedule']) or index in seen:
            raise ValueError('invalid or duplicate schedule index')
        seen.add(index)
        if any(row[k]!=v for k,v in frozen['schedule'][index].items()):
            raise ValueError('schedule mismatch')
        if row.get('model_input_digest') != shared.object_digest(model_input(row['issue_number'], row['arm'], memory)):
            raise ValueError('input/memory mismatch')
        if 'answer' in row:
            fixed.ExtractiveIssueTriageAnswer.model_validate(row['answer'])
            q = quality(row['issue_number'], row['answer'], row['continuation_calls'], runtime[0])
            if row['quality'] != q or row['correct'] != all(q[field] for field in FIELDS):
                raise ValueError('grade mismatch')
        if row['status']=='completed' and 'answer' not in row:
            raise ValueError('missing completed answer')
        for call in row['continuation_calls']:
            if call['status']=='ok':
                value = replay.execute_issue_snapshot(runtime[0], call['tool'], call['arguments'])
                if shared.object_digest(value) != call['output_digest']:
                    raise ValueError('tool output replay mismatch')
        audit_usage(row, frozen['price_table'])
    return memory


def pilot_valid(state):
    rows = [r for r in state['rows'] if r['group']=='pilot']
    return len(rows)==18 and all(r['status']=='completed' for r in rows) and any(
        r.get('dispatch', {}).get('compacted', 0) for r in rows)


async def run(out=OUT, env_file=None):
    lock = out/'run.lock'
    fd = os.open(lock, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        frozen, runtime = verify(out)
        path = out/'checkpoint.json'
        state = json.loads(path.read_text()) if path.exists() else {
            'seal_sha256': shared.object_digest(frozen), 'induction': None, 'rows': [],
            'pending': {}, 'halt_reason': None}
        memory = audit(frozen, runtime, state, out)
        if state['halt_reason']:
            raise ValueError('halted run; no automatic resume')
        if len(state['rows']) == len(frozen['schedule']):
            return progress(frozen, state)
        from dotenv import load_dotenv
        from openai import AsyncOpenAI
        from agents.models.openai_provider import OpenAIProvider
        if env_file:
            load_dotenv(env_file)
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError('API credential unavailable')
        async with AsyncOpenAI(max_retries=0) as client:
            if state['induction'] is None:
                if not reserve(frozen, state, 'induction', {'kind': 'induction'}):
                    shared.write_json(path, state)
                    return progress(frozen, state)
                shared.write_json(path, state)
                state['induction'] = await induce(frozen, client)
                state['pending'].pop('induction')
                if state['induction']['status']!='completed':
                    state['halt_reason'] = 'induction_failed'
                    shared.write_json(path, state)
                    return progress(frozen, state)
                memory = state['induction']['memory']
                shared.write_json(out/'memory_seal.json', {'seal_sha256': shared.object_digest(frozen),
                    'induction_sha256': shared.object_digest(state['induction']), 'memory': memory})
                shared.write_json(path, state)
            consecutive_failures = 0
            done = {r['index'] for r in state['rows']}
            for group in ('pilot', 'primary'):
                if group=='primary' and not pilot_valid(state):
                    state['halt_reason'] = 'pilot_execution_gate'
                    break
                queue = asyncio.Queue()
                for number in frozen[group+'_numbers']:
                    jobs = [j for j in frozen['schedule'] if j['issue_number']==number and j['index'] not in done]
                    if jobs:
                        queue.put_nowait(jobs)
                async def worker():
                    nonlocal consecutive_failures
                    while not queue.empty() and not state['halt_reason']:
                        jobs = queue.get_nowait()
                        for job in jobs:
                            if state['halt_reason'] or not reserve(frozen, state, str(job['index']), job):
                                break
                            shared.write_json(path, state)
                            provider = OpenAIProvider(openai_client=client).get_model(shared.MODEL)
                            row = await execute(job, runtime, memory, frozen['price_table'], provider)
                            state['rows'].append(row)
                            state['pending'].pop(str(job['index']))
                            consecutive_failures = consecutive_failures+1 if row['status']=='failed' else 0
                            if consecutive_failures >= 5:
                                state['halt_reason'] = 'five_consecutive_failures'
                            shared.write_json(path, state)
                            print(json.dumps(progress(frozen, state)), flush=True)
                        queue.task_done()
                await asyncio.gather(*(worker() for _ in range(CONCURRENCY)))
                if state['halt_reason']:
                    break
        shared.write_json(path, state)
        audit(frozen, runtime, state, out)
        return progress(frozen, state)
    finally:
        lock.unlink()


def interval(values):
    import numpy as np
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(SEED)
    draws = values[rng.integers(0, len(values), size=(10000, len(values)))].mean(axis=1)
    return {'mean': float(values.mean()), 'ci95': [float(v) for v in np.quantile(draws, [.025, .975])],
            'issue_groups': len(values)}


def analyze(out=OUT):
    from scipy.stats import binomtest
    frozen, runtime = verify(out)
    state = json.loads((out/'checkpoint.json').read_text())
    audit(frozen, runtime, state, out)
    result = {**progress(frozen, state), 'audit_passed': True,
        'checkpoint_sha256': shared.digest(out/'checkpoint.json'), 'groups': {},
        'induction': state['induction'], 'reconstruction_wall_latency_ms': frozen['reconstruction_wall_latency_ms']}
    for group in ('pilot', 'primary'):
        numbers = frozen[group+'_numbers']
        rows = {(r['issue_number'],r['arm']):r for r in state['rows'] if r['group']==group}
        arms = {}
        for arm in ARMS:
            rr = [rows[n,arm] for n in numbers if (n,arm) in rows]
            complete = [r for r in rr if r['status']=='completed']
            correct = sum(r.get('correct',False) for r in complete)
            ci = binomtest(correct, len(numbers)).proportion_ci()
            arms[arm] = {'scheduled': len(numbers), 'attempted': len(rr), 'completed': len(complete),
                'correct': correct, 'failed': len(rr)-len(complete), 'unattempted': len(numbers)-len(rr),
                'accuracy_ci95_exact': [ci.low, ci.high],
                'factuality_exact': sum(r['quality']['factuality_exact'] for r in complete),
                'tool_contract': sum(r['quality']['tool_contract'] for r in complete),
                'field_errors_completed': {f: sum(not r['quality'][f] for r in complete) for f in FIELDS},
                'observed_resource_totals': {k: sum(r['metrics'][k] for r in rr) for k in
                    (*METRICS, 'input_tokens','output_tokens','cached_input_tokens','cache_write_tokens')},
                'resource_accounting_complete': len(rr)==len(numbers) and all(
                    not r['invalid_usage_indices'] and r['requests_started']==len(r['usage']) for r in rr),
                'unknown_cost_reserve_usd': sum(r['unknown_cost_reserve_usd'] for r in rr)}
        contrasts = {}
        for a,b in (('gac','awm_offline_adapted'),('gac','baseline'),('awm_offline_adapted','baseline')):
            pairs = [(rows.get((n,a)),rows.get((n,b))) for n in numbers]
            ok = lambda r: bool(r and r['status']=='completed' and r.get('correct'))
            wins = sum(ok(x) and not ok(y) for x,y in pairs)
            losses = sum(not ok(x) and ok(y) for x,y in pairs)
            resource_pairs = [(x,y) for x,y in pairs if x and y and x['status']=='completed' and y['status']=='completed']
            contrasts[a+'-minus-'+b] = {'accuracy_difference': interval([int(ok(x))-int(ok(y)) for x,y in pairs]),
                'a_only_correct': wins, 'b_only_correct': losses,
                'mcnemar_exact_p': binomtest(wins,wins+losses).pvalue if wins+losses else 1.0,
                'completed_pairs': len(resource_pairs),
                'completed_pair_resource_differences': {k: interval([x['metrics'][k]-y['metrics'][k] for x,y in resource_pairs])
                                                       for k in METRICS} if resource_pairs else {}}
        adjusted = 0.0
        for i,(_,contrast) in enumerate(sorted(contrasts.items(), key=lambda item: item[1]['mcnemar_exact_p'])):
            adjusted = max(adjusted, min(1., (3-i)*contrast['mcnemar_exact_p']))
            contrast['mcnemar_holm_p'] = adjusted
        result['groups'][group] = {'arms': arms, 'contrasts': contrasts}
    if state['induction']:
        cost = state['induction']['metrics']['estimated_cost_usd']
        result['induction_cost_amortized_per_primary_task_usd'] = cost / len(frozen['primary_numbers'])
    shared.write_json(out/'analysis.json', result)
    return {k:v for k,v in result.items() if k not in ('groups','induction')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare','verify','run','analyze'])
    parser.add_argument('--env-file', type=Path)
    args = parser.parse_args()
    if args.command=='prepare':
        frozen = prepare()
        result = {'scheduled':len(frozen['schedule']), 'provider_calls_executed':0, 'seal_sha256':shared.object_digest(frozen)}
    elif args.command=='verify':
        frozen,_ = verify()
        result = {'verified': True, 'scheduled':len(frozen['schedule']), 'provider_calls_executed':0}
    elif args.command=='run':
        result = asyncio.run(run(env_file=args.env_file))
    else:
        result = analyze()
    print(json.dumps(result, indent=2))


if __name__=='__main__':
    main()
