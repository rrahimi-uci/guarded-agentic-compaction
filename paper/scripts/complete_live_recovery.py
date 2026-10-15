"""Prospective completion study; historical pilot and diagnostic stay immutable."""
from __future__ import annotations
import argparse
import asyncio
import json
import math
import os
import sys
import time
from itertools import permutations
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import live_safeguard_recovery as old
from recovery_observation import ObservedModel, safe_error

ROOT = old.ROOT
OUT = ROOT / 'experiments/live_recovery_completion'
PROTOCOL = OUT / 'README.md'
CONCURRENCY = 4
CAP = 200.0
BOOTSTRAPS = 10000
SEED = 20261018


def price_usage(raw, prices):
    keys = ('input_tokens', 'output_tokens', 'cached_input_tokens', 'cache_write_tokens', 'total_tokens')
    if any(type(raw.get(k)) is not int or raw[k] < 0 for k in keys):
        raise ValueError('invalid usage integer')
    i, o, c, w, t = (raw[k] for k in keys)
    if i <= 0 or c + w > i or t != i + o:
        raise ValueError('inconsistent token partitions')
    return {**{k: raw[k] for k in keys}, 'estimated_cost_usd':
            ((i-c-w)*prices['input'] + c*prices['cached_input'] + w*prices['cache_write'] + o*prices['output'])/1e6}


def inputs():
    prior, store, artifact = old.verify(old.OUT)
    pilot = json.loads((old.OUT / 'checkpoint.json').read_text())
    diagnostic = json.loads((OUT / 'diagnostic.json').read_text())
    if diagnostic['pending'] is not None or pilot['pending'] is not None:
        raise ValueError('unresolved prior attempt')
    if diagnostic['prior_checkpoint_sha256'] != old.digest(old.OUT / 'checkpoint.json'):
        raise ValueError('diagnostic/pilot provenance mismatch')
    if diagnostic['script_sha256'] != old.digest(OUT / 'diagnostic_driver.py.txt'):
        raise ValueError('archived diagnostic driver mismatch')
    offline_seal = json.loads((old.PRIOR / 'seal.json').read_text())
    replication = prior['cohort']
    confirmation = sorted(set(offline_seal['splits']['test']) - set(replication),
                          key=lambda n: old.object_digest(['confirmation', SEED, n]))
    if len(confirmation) != 72 or len(replication) != 24:
        raise ValueError('unexpected cohort sizes')
    return prior, store, artifact, confirmation, replication, diagnostic


def schedule(confirmation, replication):
    orders = list(permutations(old.ARMS))
    result = []
    for group, numbers in [('confirmation', confirmation), ('replication', replication)]:
        for index, number in enumerate(numbers):
            for variant, case in enumerate(old.offline.cases([number])):
                for arm in orders[(index + variant) % 24]:
                    result.append({'index': len(result), 'group': group, 'issue_number': number,
                                   'case_id': case['case_id'], 'arm': arm})
    return result


def make_seal():
    prior, store, artifact, confirmation, replication, diagnostic = inputs()
    paths = [Path(__file__), ROOT/'paper/scripts/recovery_observation.py', PROTOCOL,
             OUT/'diagnostic.json', OUT/'diagnostic_driver.py.txt', old.OUT/'checkpoint.json', old.OUT/'seal.json']
    hashes = {str(p.relative_to(ROOT)): old.digest(p) for p in paths}
    cases = old.offline.cases(confirmation + replication)
    return {'schema': 'live-recovery-completion/v1', 'hashes': {**old.code_hashes(), **hashes},
        'environment': old.environment(), 'configuration': old.configuration(),
        'confirmation': confirmation, 'replication': replication, 'cases': cases,
        'schedule': schedule(confirmation, replication), 'prefetch': old.preflight(cases, artifact, store),
        'concurrency': CONCURRENCY, 'approved_aggregate_cap_usd': CAP,
        'prior_estimate_and_reserve_usd': diagnostic['aggregate_estimate_and_reserve_usd'],
        'bootstrap_draws': BOOTSTRAPS, 'bootstrap_seed': SEED}, store, artifact


def verify(out=OUT):
    expected, store, artifact = make_seal()
    actual = json.loads((out/'seal.json').read_text())
    if actual != expected:
        raise ValueError('prospective seal mismatch')
    return actual, store, artifact


def usage_account(record, prices):
    usage, invalid = [], []
    for index, raw in enumerate(record['usage_observations']):
        try:
            usage.append(price_usage(raw, prices))
        except ValueError:
            invalid.append(index)
    totals = {k: sum(r[k] for r in usage) for k in
              ('input_tokens','output_tokens','cached_input_tokens','cache_write_tokens','total_tokens','estimated_cost_usd')}
    totals.update(requests=record['requests_started'], responses=len(record['usage_observations']),
        prefetch_tool_calls=len(record.get('prefetch_calls', [])),
        continuation_tool_calls=len(record['continuation_calls']))
    totals['total_tool_calls'] = totals['prefetch_tool_calls'] + totals['continuation_tool_calls']
    return usage, invalid, totals


async def execute(case, arm, artifact, store, client, prices):
    from agents import Agent, RunConfig, Runner
    from agents.models.openai_provider import OpenAIProvider
    record = {'case_id': case['case_id'], 'arm': arm, 'stage': 'prefetch',
              'requests_started': 0, 'usage_observations': [], 'continuation_calls': []}
    started = time.perf_counter()
    try:
        context, backend = old.initial_context(case, arm, artifact, store)
        record.update(context['metadata'], model_input_digest=old.object_digest(context['model_input']))
        model = ObservedModel(OpenAIProvider(openai_client=client).get_model(old.MODEL), record)
        agent = Agent(name='comment-window-recovery', instructions=old.PROMPT, model=model,
            model_settings=old.settings(), tools=old.recovery_tools(backend, case, record['continuation_calls']), output_type=old.Answer)
        result = await asyncio.wait_for(Runner.run(agent, context['model_input'], max_turns=old.MAX_TURNS,
            run_config=RunConfig(tracing_disabled=True)), timeout=old.TIMEOUT)
        record['stage'] = 'answer_validation'
        record['answer'] = old.Answer.model_validate(result.final_output).model_dump()
        record['correct'] = record['answer'] == old.offline.source_answer(case, store)
        record['stage'] = 'usage_validation'
        if len(result.raw_responses) != record['requests_started'] or not result.raw_responses:
            raise ValueError('missing completed response accounting')
        for raw in record['usage_observations']:
            price_usage(raw, prices)
        record['status'] = 'completed'
    except Exception as exc:
        record.update(status='failed', error=safe_error(exc, record['stage']))
    usage, invalid, totals = usage_account(record, prices)
    totals['wall_latency_ms'] = (time.perf_counter()-started)*1000
    record.update(usage=usage, invalid_usage_indices=invalid, metrics=totals,
                  unknown_cost_reserve_usd=1.0 if record['status']=='failed' else 0.0)
    return record


def audit(frozen, store, artifact, state):
    if state['seal_sha256'] != old.object_digest(frozen) or state['approved_aggregate_cap_usd'] != CAP:
        raise ValueError('checkpoint identity mismatch')
    cases = {c['case_id']:c for c in frozen['cases']}
    indices = [r['index'] for r in state['rows']]
    if len(set(indices)) != len(indices):
        raise ValueError('duplicate episode')
    for row in state['rows']:
        if any(row[k] != v for k,v in frozen['schedule'][row['index']].items()):
            raise ValueError('schedule mismatch')
        if row['status'] not in ('completed','failed'):
            raise ValueError('unknown status')
        case = cases[row['case_id']]
        if 'answer' in row:
            old.Answer.model_validate(row['answer'])
            if row['correct'] != (row['answer'] == old.offline.source_answer(case, store)):
                raise ValueError('source grade mismatch')
        context, backend = old.initial_context(case, row['arm'], artifact, store)
        if row.get('model_input_digest') != old.object_digest(context['model_input']):
            raise ValueError('initial input mismatch')
        if any(row[k] != v for k,v in context['metadata'].items()):
            raise ValueError('prefetch evidence mismatch')
        for call in row['continuation_calls']:
            if call['status']=='ok':
                result = backend(call['tool'], call['arguments'])
                if old.object_digest(result) != call['output_digest']:
                    raise ValueError('tool replay mismatch')
        usage, invalid, totals = usage_account(row, frozen['configuration']['price_table'])
        if usage != row['usage'] or invalid != row['invalid_usage_indices']:
            raise ValueError('usage/cost mismatch')
        if any(not math.isclose(row['metrics'][k], v, abs_tol=1e-12, rel_tol=1e-12) for k,v in totals.items()):
            raise ValueError('metric mismatch')
        if row['status']=='completed' and (invalid or not row.get('answer') or len(usage)!=row['requests_started'] or not usage):
            raise ValueError('incomplete successful accounting')
        if row['unknown_cost_reserve_usd'] != (1 if row['status']=='failed' else 0):
            raise ValueError('failure reserve mismatch')
    return True


def budget_total(frozen, state, include_pending=True):
    return (frozen['prior_estimate_and_reserve_usd'] +
        sum(r['metrics']['estimated_cost_usd'] + r['unknown_cost_reserve_usd'] for r in state['rows']) +
        (len(state['pending']) if include_pending else 0))


async def run(out=OUT, env_file=None):
    lock = out/'run.lock'
    fd = os.open(lock, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        frozen, store, artifact = verify(out)
        path = out/'checkpoint.json'
        state = json.loads(path.read_text()) if path.exists() else {
            'seal_sha256': old.object_digest(frozen), 'approved_aggregate_cap_usd': CAP,
            'rows': [], 'pending': {}, 'halt_reason': None}
        if state['pending']:
            raise ValueError('interrupted attempts require explicit reconciliation; no automatic replay')
        audit(frozen, store, artifact, state)
        if state['halt_reason']:
            raise ValueError('halted run; automatic resume refused')
        if len(state['rows']) == len(frozen['schedule']):
            return progress(frozen, state)
        from dotenv import load_dotenv
        from openai import AsyncOpenAI
        if env_file:
            load_dotenv(env_file)
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError('API credential unavailable')
        done = {r['index'] for r in state['rows']}
        cases = {c['case_id']:c for c in frozen['cases']}
        groups = asyncio.Queue()
        for number in frozen['confirmation'] + frozen['replication']:
            jobs = [r for r in frozen['schedule'] if r['issue_number']==number and r['index'] not in done]
            if jobs:
                groups.put_nowait(jobs)
        consecutive_failures = 0
        async with AsyncOpenAI(max_retries=0) as client:
            async def worker():
                nonlocal consecutive_failures
                while not groups.empty() and not state['halt_reason']:
                    jobs = groups.get_nowait()
                    for planned in jobs:
                        if state['halt_reason']:
                            break
                        if budget_total(frozen, state) + 1 > CAP:
                            state['halt_reason'] = 'budget_guard'
                            old.write_json(path, state)
                            break
                        key = str(planned['index'])
                        state['pending'][key] = planned
                        old.write_json(path, state)
                        row = await execute(cases[planned['case_id']], planned['arm'], artifact, store, client,
                                            frozen['configuration']['price_table'])
                        row.update(planned)
                        state['rows'].append(row)
                        state['rows'].sort(key=lambda r:r['index'])
                        del state['pending'][key]
                        consecutive_failures = consecutive_failures+1 if row['status']=='failed' else 0
                        if consecutive_failures >= 5:
                            state['halt_reason'] = 'five_consecutive_execution_failures'
                        old.write_json(path, state)
                        print(json.dumps(progress(frozen,state)), flush=True)
                    groups.task_done()
            await asyncio.gather(*(worker() for _ in range(CONCURRENCY)))
        old.write_json(path, state)
        return progress(frozen, state)
    finally:
        lock.unlink()


def progress(frozen, state):
    return {'attempted': len(state['rows']), 'scheduled': len(frozen['schedule']),
        'completed': sum(r['status']=='completed' for r in state['rows']),
        'correct': sum(r['status']=='completed' and r['correct'] for r in state['rows']),
        'estimated_spend_usd': sum(r['metrics']['estimated_cost_usd'] for r in state['rows']),
        'aggregate_estimate_and_reserve_usd': budget_total(frozen,state,False),
        'pending': len(state['pending']), 'halt_reason': state['halt_reason']}


def cluster_interval(values):
    """Descriptive paired percentile bootstrap over issues, never over variants."""
    values = np.asarray(values, dtype=float)
    if not len(values):
        return None
    rng = np.random.default_rng(SEED)
    samples = values[rng.integers(0,len(values),size=(BOOTSTRAPS,len(values)))].mean(axis=1)
    return {'mean': float(values.mean()), 'ci95': [float(x) for x in np.quantile(samples,[.025,.975])],
            'issue_groups':len(values)}


def analyze(out=OUT):
    frozen, store, artifact = verify(out)
    state = json.loads((out/'checkpoint.json').read_text())
    if state['pending']:
        raise ValueError('unresolved pending attempts')
    audit(frozen, store, artifact, state)
    index = {(r['case_id'],r['arm']):r for r in state['rows']}
    result = {**progress(frozen,state), 'checkpoint_sha256':old.digest(out/'checkpoint.json'),
              'audit_passed':True, 'all_scheduled_attempted':len(index)==len(frozen['schedule']), 'groups':{},
              'incorrect_answers':[{**{k:r[k] for k in ('group','case_id','arm','answer')},
                    'expected':old.offline.source_answer(next(c for c in frozen['cases'] if c['case_id']==r['case_id']),store),
                    'dispatched':r.get('dispatched',False)} for r in state['rows']
                    if 'answer' in r and not r['correct']]}
    for group in ('confirmation','replication'):
        numbers = frozen[group]
        result['groups'][group] = {}
        for suite in old.offline.SUITES:
            cases = [c for c in frozen['cases'] if c['issue_number'] in numbers and c['suite']==suite]
            arms = {}
            for arm in old.ARMS:
                rows = [index[c['case_id'],arm] for c in cases if (c['case_id'],arm) in index]
                good = [r for r in rows if r['status']=='completed']
                incomplete = []
                for c in cases:
                    context,_ = old.initial_context(c,arm,artifact,store)
                    if not context['metadata']['dispatched']:
                        continue
                    observations = json.loads(context['model_input'])['initial_observations']
                    positions = {item['position'] for obs in observations if obs['tool']=='comments.page'
                                 for item in obs['result']['items']}
                    needed = set(range(1,min(c['requested_limit'],len(store[c['issue_number']]['comments']))+1))
                    if not needed.issubset(positions):
                        incomplete.append(c['case_id'])
                exposed = [r for r in rows if r['case_id'] in incomplete]
                arms[arm] = {'scheduled':len(cases),'attempted':len(rows),'completed':len(good),
                    'failed':len(rows)-len(good),'not_attempted':len(cases)-len(rows),
                    'correct':sum(r['correct'] for r in good),
                    'dispatched':sum(r.get('dispatched',False) for r in rows),
                    'wrong_after_dispatch':sum(r.get('dispatched',False) and not r.get('correct',False) for r in rows),
                    'episodes_with_calls_after_dispatch':sum(r.get('dispatched',False) and bool(r['continuation_calls']) for r in rows),
                    'resource_accounting_complete':len(good)==len(cases),
                    'completed_means':{k:sum(r['metrics'][k] for r in good)/len(good) if good else None for k in
                        ('requests','total_tokens','total_tool_calls','continuation_tool_calls','prefetch_tool_calls','wall_latency_ms','estimated_cost_usd')},
                    'cache_write_tokens':sum(r['metrics']['cache_write_tokens'] for r in rows),
                    'incomplete_accepted_prefetch':{'scheduled':len(incomplete),'attempted':len(exposed),
                        'correct':sum(r['status']=='completed' and r['correct'] for r in exposed),
                        'with_continuation_reads':sum(bool(r['continuation_calls']) for r in exposed),
                        'issue_groups':len({c.split(':')[0] for c in incomplete})}}
            pairs = {}
            for arm in old.ARMS:
                if arm=='full': continue
                matched = [(c,index[c['case_id'],'full'],index[c['case_id'],arm]) for c in cases
                           if (c['case_id'],'full') in index and (c['case_id'],arm) in index]
                ok = lambda r: int(r['status']=='completed' and r['correct'])
                wins = [c for c,a,b in matched if ok(a)>ok(b)]
                losses = [c for c,a,b in matched if ok(a)<ok(b)]
                comparisons = {'attempted_pairs':len(matched), 'full_only_correct':len(wins),
                    'other_only_correct':len(losses),
                    'full_only_correct_groups':len({c['issue_number'] for c in wins}),
                    'other_only_correct_groups':len({c['issue_number'] for c in losses}),
                    'paired_intervals':{}}
                if len(matched)==len(cases):
                    values = [sum(ok(a)-ok(b) for c,a,b in matched if c['issue_number']==n)/3 for n in numbers]
                    comparisons['paired_intervals']['accuracy_full_minus_other'] = cluster_interval(values)
                    if all(a['status']==b['status']=='completed' for _,a,b in matched):
                        for metric in ('requests','total_tool_calls','estimated_cost_usd','wall_latency_ms'):
                            values = [sum(a['metrics'][metric]-b['metrics'][metric] for c,a,b in matched if c['issue_number']==n)/3 for n in numbers]
                            comparisons['paired_intervals'][metric+'_full_minus_other'] = cluster_interval(values)
                pairs[arm] = comparisons
            result['groups'][group][suite] = {'issue_groups':len(numbers),'arms':arms,'paired_vs_full':pairs,
                'cases_with_more_than_two_source_comments':sum(min(c['requested_limit'],len(store[c['issue_number']]['comments']))>2 for c in cases)}
    old.write_json(out/'analysis.json',result)
    lines = ['# Live recovery completion: observed results','',
        f"Attempted {result['attempted']}/{result['scheduled']}; completed {result['completed']}; correct {result['correct']}.",
        f"Estimated run spend ${result['estimated_spend_usd']:.6f}; aggregate estimate plus retained reserves ${result['aggregate_estimate_and_reserve_usd']:.6f} / $200.",
        '', 'Frozen repository rates are estimates, not provider invoices. Failed attempts remain in denominators.',
        'Confirmation and replication are separate; variants are clustered by issue. Intervals are descriptive, unadjusted for multiple comparisons.', '']
    for group,suites in result['groups'].items():
        for suite, data in suites.items():
            lines += [f'## {group}: {suite}','', '| Arm | Correct / scheduled | Failed | Requests* | Total tools* | Cost* |',
                      '| --- | ---: | ---: | ---: | ---: | ---: |']
            for arm,row in data['arms'].items():
                m=row['completed_means']
                fmt=lambda k: 'NA' if m[k] is None else f'{m[k]:.6f}'
                lines.append(f"| {arm} | {row['correct']}/{row['scheduled']} | {row['failed']} | {fmt('requests')} | {fmt('total_tool_calls')} | {fmt('estimated_cost_usd')} |")
            lines += ['', '*Completed-episode means. Overall resource comparisons require complete accounting.', '']
    (out/'results.md').write_text('\n'.join(lines)+'\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=('prepare','verify','run','analyze'))
    p.add_argument('--env-file',type=Path)
    args=p.parse_args()
    if args.command=='prepare':
        frozen,_,_=make_seal()
        old.offline.save_new(OUT/'seal.json',frozen)
        result={'sealed':True,'episodes':len(frozen['schedule'])}
    elif args.command=='verify':
        frozen,_,_=verify()
        result={'verified':True,'episodes':len(frozen['schedule'])}
    elif args.command=='run':
        result=asyncio.run(run(env_file=args.env_file))
    else: result=analyze()
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=='__main__': main()
