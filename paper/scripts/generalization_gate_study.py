"""Prospective multi-family/model comparison and exact dispatcher ablation."""
from __future__ import annotations
import argparse
import asyncio
import copy
import json
import math
import os
import sys
import time
from collections import Counter
from dataclasses import asdict
from importlib.metadata import version
from itertools import permutations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'paper/scripts')]
import matched_reuse_baseline as prior
import fresh_safeguard_comparison as shared
import github_workflow_family_study as family
import second_model_replication as second
import recurrence_only_ablation as issue
from recovery_observation import ObservedModel, safe_error, safe_usage
from complete_live_recovery import price_usage

OUT = ROOT/'experiments/generalization_gate'
MODELS = ('gpt-5.6-luna', 'gpt-6-luna')
COUNTS = {'backlog_attention': 144, 'issue_type': 600, 'pr_outcome': 600}
ARMS = prior.ARMS
SEED = 20261020
CONCURRENCY = 8
CAP = 400.0


def source_paths():
    return {'issue_type': ROOT/'paper/results/github_natural_replication/discovery_checkpoint.json',
            'pr_outcome': family.OUT_ROOT/'pr_outcome/pilot_v1/discovery_checkpoint.json',
            'backlog_attention': family.OUT_ROOT/'backlog_attention/final/discovery_checkpoint.json'}


def task(name, number):
    return prior.task(number) if name == 'issue_type' else f'Audit public snapshot record_number={number}'


def build_runtime(name, model, stores):
    started = time.perf_counter()
    checkpoint = json.loads(source_paths()[name].read_text())
    store = stores[name == 'issue_type']
    if name == 'issue_type':
        tools, catalog = prior.fixed.make_tools(store), prior.fixed.make_catalog()
        manifest = prior.fixed.make_manifest(model, tools, catalog, shared.TASK)
        discovery = second.reconstruct_discovery(checkpoint, store=store, manifest=manifest)
        registry, compilation, manifest = second.compile_for_model(discovery, model=model, catalog=catalog, tools=tools)
        continuation = manifest
        examples = prior.discovery_examples(checkpoint)
    else:
        spec = family.FAMILIES[name]
        tools, catalog = family.make_tools(spec, store), family.make_catalog(spec)
        manifest = family.make_manifest(spec, model, tools, catalog, 'source')
        continuation = family.make_manifest(spec, model, (), catalog, 'pre-model')
        discovery = family.reconstruct_discovery(spec, checkpoint, store=store, manifest=manifest)
        registry, compilation = family.compile_artifact(spec, discovery, catalog=catalog,
            source_manifest=manifest, continuation_manifest=continuation)
        examples = [{'confirmed_task': task(name,r.issue_number), 'action_reprs':
            [t+'('+json.dumps(a,sort_keys=True)+')' for t,a in zip(r.tool_sequence,r.tool_arguments)]}
            for r in discovery if r.condition=='discovery' and r.quality['overall']]
    deterministic = copy.deepcopy(registry)
    from guarded_agentic_compaction.schema.artifacts import Gate
    for artifact in deterministic.artifacts:
        artifact.gate = Gate(threshold=1., alpha=1., retire=False,
            notes='UNCERTIFIED deterministic guards; statistical admission removed')
    deterministic._reindex()
    return dict(name=name, model=model, store=store, tools=tools, catalog=catalog,
        manifest=manifest, continuation=continuation, registry=registry,
        support_only=shared.support_registry(registry), deterministic=deterministic,
        compilation=compilation, examples=examples,
        reconstruction_ms=(time.perf_counter()-started)*1000)


def runtime_record(rt):
    return {'artifact': rt['registry'].artifacts[0].to_dict(),
        'compilation': rt['compilation'], 'manifest': rt['manifest'].compatibility_key(),
        'continuation': rt['continuation'].compatibility_key(),
        'discovery_sha256': shared.digest(source_paths()[rt['name']]),
        'eligible_discovery_traces': len(rt['examples']),
        'induction_request': prior.awm.induction_request(rt['examples'], rt['model'],
            [{'name':t.name,'description':t.description,'parameters':t.params_json_schema} for t in rt['tools']])}


def exclusions():
    excluded, hashes = shared.exclusion_audit(ROOT/'paper/results')
    for path in sorted((ROOT/'experiments').rglob('*.json')):
        if path.is_relative_to(OUT) or 'vendor' in path.parts:
            continue
        ids = shared.used_ids(json.loads(path.read_text()))
        if ids:
            excluded.update(ids)
            hashes[str(path.relative_to(ROOT))] = shared.digest(path)
    return excluded, hashes


def select(stores, excluded):
    cohorts = {}
    used = set(excluded)
    for name, n in COUNTS.items():
        store = stores[name=='issue_type']
        def eligible(row):
            if name != 'issue_type':
                return family.FAMILIES[name].eligible(row) and len(family.normalize_text(row.get('title'))) <= 500
            texts = [row.get('title',''),row.get('body',''),*row.get('comments',[])[:3]]
            return (not row.get('pull_request') and 0 < len(str(row.get('title',''))) <= 500
                    and any(len(str(t).strip())>=20 for t in texts))
        numbers = [k for k,v in store.items() if k not in used and eligible(v)]
        numbers.sort(key=lambda k: shared.object_digest(['generalization-gate',SEED,name,k]))
        if len(numbers) < n+6:
            raise ValueError(f'{name}: only {len(numbers)} fresh valid records, need {n+6}')
        cohorts[name] = {'pilot':numbers[:6], 'primary':numbers[6:n+6], 'available':len(numbers)}
        used.update(numbers[:n+6])
    return cohorts


def schedule(cohorts):
    jobs=[]
    orders=list(permutations(ARMS))
    for group in ('pilot','primary'):
        for name, cohort in cohorts.items():
            for pos, number in enumerate(cohort[group]):
                for model in MODELS[::1 if pos%2==0 else -1]:
                    for arm in orders[pos%6]:
                        jobs.append(dict(index=len(jobs),group=group,family=name,model=model,
                                         issue_number=number,arm=arm))
    return jobs


def premodel(rt, number, registry, calls):
    from guarded_agentic_compaction.runtime.dispatch import Dispatcher
    from guarded_agentic_compaction.runtime.runner import CompactingRunner
    def execute(tool,args):
        value=family.execute_snapshot(family.FAMILIES[rt['name']],rt['store'],tool,args)
        calls.append({'tool':tool,'arguments':args,'status':'ok','output_digest':shared.object_digest(value)})
        return value
    return CompactingRunner(Dispatcher(registry,rt['catalog'],mode='live'),rt['catalog'],rt['manifest']).execute_pre_model(
        {'record_number':number},executor=execute,day=str(rt['store'][number].get('created_at'))[:10],
        continuation_compatibility_key=rt['continuation'].compatibility_key())


def probe(rt, numbers):
    from guarded_agentic_compaction.runtime.dispatch import Dispatcher
    records=[]
    for number in numbers:
        arms={}
        for arm,key in [('gac','registry'),('support_only','support_only'),('deterministic','deterministic')]:
            started=time.perf_counter()
            calls=[]
            if rt['name']=='issue_type':
                m=rt['manifest']
                decision=Dispatcher(rt[key],rt['catalog'],mode='live').decide(
                    compatibility_key=m.compatibility_key(),partition={},entry_state={'issue_number':number},
                    context={**{k:getattr(m,k) for k in ('model','prompt_hash','tools_hash','policy_hash','guardrail_hash','entry_contract_version')},
                             'effect_catalog_version':rt['catalog'].catalog_version,'day':''},
                    executor=lambda tool,args:issue.execute_issue_snapshot(rt['store'],tool,args))
                signature={'compacted':decision.compacted,'calls':decision.calls,'outputs':decision.results}
                record=decision.record
            else:
                decision=premodel(rt,number,rt[key],calls)
                signature={'compacted':decision.compacted,'calls':calls,
                           'observations':[asdict(o) for o in decision.observations]}
                record=decision.record
            reasons=record.get('reasons',[])
            if any(str(r).startswith(('no_artifact','manifest_missing','manifest_mismatch')) for r in reasons):
                raise ValueError(f'configuration failure {rt["name"]}: {reasons}')
            arms[arm]={'signature':shared.object_digest(signature),'compacted':decision.compacted,
                       'record':record,'wall_ms':(time.perf_counter()-started)*1000}
        records.append({'issue_number':number,'arms':arms,
                        'equal':len({a['signature'] for a in arms.values()})==1})
    return {'all_equivalent':all(r['equal'] for r in records),'records':records,
            'compacted':sum(r['arms']['gac']['compacted'] for r in records)}


def code_hashes():
    paths=list((ROOT/'src').rglob('*.py'))+list((ROOT/'paper/scripts').glob('*.py'))
    paths += [OUT/'README.md',ROOT/'demos/live_runtime.py']
    paths += list(prior.awm.VENDOR.rglob('*'))
    return {str(p.relative_to(ROOT)):shared.digest(p) for p in sorted(paths) if p.is_file()}


def budget_source():
    path=prior.OUT/'analysis.json'
    data=json.loads(path.read_text())
    checkpoint=json.loads((prior.OUT/'checkpoint.json').read_text())
    if checkpoint['pending'] or data['checkpoint_sha256']!=shared.digest(prior.OUT/'checkpoint.json'):
        raise ValueError('prior checkpoint unresolved or changed')
    amount=data['aggregate_estimate_and_reserve_usd']
    if not math.isclose(amount,8.57705193,abs_tol=1e-8):
        raise ValueError('unexpected carried budget')
    return {'prior_estimate_and_reserve_usd':amount,'source_hashes':{
        str(p.relative_to(ROOT)):shared.digest(p) for p in (path,prior.OUT/'checkpoint.json')}}


def load_runtimes():
    stores=(family.load_store()[0],issue.load_store()[0])
    return stores,{name+'|'+model:build_runtime(name,model,stores) for name in COUNTS for model in MODELS}


def ni_bound(losses,n):
    from scipy.stats import beta
    if not 0 <= losses <= n or n<=0: raise ValueError('invalid binomial counts')
    return 1. if losses==n else float(beta.ppf(1-.05/6,losses+1,n-losses))


def power(n,p):
    from scipy.stats import binom
    passing=[k for k in range(n) if ni_bound(k,n)<.05]
    return float(binom.cdf(max(passing),n,p)) if passing else 0.


def prepare():
    if (OUT/'seal.json').exists(): raise ValueError('already sealed')
    stores,runtimes=load_runtimes()
    excluded,hashes=exclusions()
    cohorts=select(stores,excluded)
    cells={}
    for key,rt in runtimes.items():
        c=cohorts[rt['name']]
        cells[key]=runtime_record(rt)
        cells[key]['probe']=probe(rt,c['pilot']+c['primary'])
        if not cells[key]['probe']['all_equivalent']:
            raise ValueError(f'{key}: gate differences require prospective live ablation design')
        cells[key]['reconstruction_ms']=rt['reconstruction_ms']
    from demos.live_runtime import MODEL_PRICES
    frozen=dict(schema='generalization-gate/v1',seed=SEED,cohorts=cohorts,cells=cells,
        schedule=schedule(cohorts),excluded_ids=sorted(excluded),exclusion_hashes=hashes,
        code_hashes=code_hashes(),environment={p:version(p) for p in prior.DEPS},
        source_sha256=shared.digest(prior.fixed.DATA_PATH),vendor=prior.awm.verify_vendor(),
        prices={m:asdict(MODEL_PRICES[m]) for m in MODELS},settings=prior.settings().to_json_dict(),
        budget=budget_source(),cap=CAP,concurrency=CONCURRENCY,
        power={name:{'n':n,'loss_01':power(n,.01),'loss_02':power(n,.02),'loss_03':power(n,.03)} for name,n in COUNTS.items()})
    shared.write_json(OUT/'seal.json',frozen)
    return {'scheduled':len(frozen['schedule']),'power':frozen['power'],
            'gate_equivalence':{k:v['probe']['all_equivalent'] for k,v in cells.items()}}


def verify():
    frozen=json.loads((OUT/'seal.json').read_text())
    if frozen['code_hashes']!=code_hashes() or frozen['environment']!={p:version(p) for p in prior.DEPS}:
        raise ValueError('code/environment drift')
    if (frozen['cap']!=CAP or frozen['concurrency']!=CONCURRENCY or frozen['settings']!=prior.settings().to_json_dict()
            or frozen['source_sha256']!=shared.digest(prior.fixed.DATA_PATH) or frozen['budget']!=budget_source()):
        raise ValueError('source/budget drift')
    for p,h in frozen['exclusion_hashes'].items():
        if shared.digest(ROOT/p)!=h: raise ValueError('exclusion drift')
    stores,runtimes=load_runtimes()
    if select(stores,set(frozen['excluded_ids']))!=frozen['cohorts'] or schedule(frozen['cohorts'])!=frozen['schedule']:
        raise ValueError('selection drift')
    for key,rt in runtimes.items():
        record=runtime_record(rt)
        if any(frozen['cells'][key][k]!=v for k,v in record.items()): raise ValueError('candidate drift')
    return frozen,runtimes


def grade(rt,number,answer,calls):
    if rt['name']=='issue_type':
        q=prior.quality(number,answer,calls,rt['store'])
        return q,all(q[k] for k in prior.FIELDS)
    q=family.grade(family.FAMILIES[rt['name']],rt['store'][number],answer,[c['tool'] for c in calls])
    # Tool usage is reported separately, not included in factual task accuracy.
    keys=('record_number_correct','title_correct','comment_grounded')+(
        ('outcome_correct',) if rt['name']=='pr_outcome' else ('route_correct','owner_correct'))
    return q,all(q[k] for k in keys)


async def execute(job,rt,memory,prices,provider):
    from agents import Runner,RunConfig
    from guarded_agentic_compaction.runtime.model_provider import CompactingModel
    row={**prior.record(),**job}; started=time.perf_counter(); compacting=None
    try:
        model=ObservedModel(provider,row)
        tools=rt['tools']; user=task(rt['name'],job['issue_number'])
        if job['arm']=='gac':
            if rt['name']=='issue_type':
                compacting=CompactingModel(model,registry=rt['registry'],catalog=rt['catalog'],manifest=rt['manifest'],
                    mode='live',entry_state_fn=lambda _:{'issue_number':job['issue_number']},partition_fn=lambda _i,_e:{})
                model=compacting
            else:
                d=premodel(rt,job['issue_number'],rt['registry'],row['continuation_calls'])
                row['dispatch']=d.record;row['compacted']=d.compacted
                if d.compacted:
                    if len(d.observations)!=1: raise ValueError('invalid composite observation')
                    tools=()
                    user+='\nThe runtime already executed an approved guarded evidence plan. Do not call tools. Use only this source-grounded JSON evidence:\n'+json.dumps(d.observations[0].result,sort_keys=True,separators=(',',':'))
        inp=(prior.awm.memory_messages(memory) if job['arm']=='awm_offline_adapted' else [])+[{'role':'user','content':user}]
        row['model_input_digest']=shared.object_digest(inp)
        observed=prior.observed_tools(tools,row)
        agent=(prior.fixed.make_agent(model,observed,shared.TASK) if rt['name']=='issue_type'
               else family.make_agent(family.FAMILIES[rt['name']],model,observed))
        agent.model_settings=prior.settings()
        result=await asyncio.wait_for(Runner.run(agent,inp,max_turns=8,run_config=RunConfig(tracing_disabled=True)),timeout=120)
        row['stage']='answer_validation'
        schema=prior.fixed.ExtractiveIssueTriageAnswer if rt['name']=='issue_type' else family.FAMILIES[rt['name']].answer_model
        row['answer']=schema.model_validate(result.final_output).model_dump()
        row['quality'],row['correct']=grade(rt,job['issue_number'],row['answer'],row['continuation_calls'])
        if not row['usage_observations'] or len(row['usage_observations'])!=row['requests_started']: raise ValueError('missing usage')
        for raw in row['usage_observations']: price_usage(raw,prices)
        row['status']='completed'
    except Exception as exc:
        row.update(status='failed',error=safe_error(exc,row['stage']))
    if compacting:
        row['dispatch']=compacting.dispatcher.telemetry.as_dict()
        row['compacted']=bool(row['dispatch'].get('compacted'))
    return prior.finish(row,prices,started)


async def induce(cell,model,prices,client):
    row=prior.record();started=time.perf_counter()
    try:
        row['requests_started']=1
        response=await asyncio.wait_for(client.responses.create(model=model,input=cell['induction_request']['messages'],
            max_output_tokens=1024,reasoning={'effort':'low'},text={'verbosity':'low'},store=False),timeout=120)
        row['usage_observations'].append(safe_usage(response))
        row['text']=response.output_text;row['response_status']=response.status
        if response.status!='completed': raise ValueError('truncated induction')
        row['memory']=prior.awm.filter_memory(row['text'])
        for raw in row['usage_observations']: price_usage(raw,prices)
        row['status']='completed'
    except Exception as exc:
        row.update(status='failed',error=safe_error(exc,row['stage']))
    return prior.finish(row,prices,started)


def total(frozen,state):
    rows=state['rows']+list(state['inductions'].values())
    return frozen['budget']['prior_estimate_and_reserve_usd']+len(state['pending'])+sum(
        r['metrics']['estimated_cost_usd']+r['unknown_cost_reserve_usd'] for r in rows)


def reserve(frozen,state,key,job):
    if key in state['pending']: raise ValueError('duplicate pending')
    if not math.isfinite(frozen['cap']) or not 0<frozen['cap']<=CAP: raise ValueError('invalid cap')
    if total(frozen,state)+1>frozen['cap']:
        state['halt_reason']='estimated_spend_guard';return False
    state['pending'][key]=job;return True


def audit(frozen,runtimes,state):
    if state['seal_sha256']!=shared.object_digest(frozen) or state['pending']: raise ValueError('identity/pending')
    for key,row in state['inductions'].items():
        if key not in runtimes: raise ValueError('unknown induction')
        prior.audit_usage(row,frozen['prices'][runtimes[key]['model']])
        if row['status']=='completed' and row['memory']!=prior.awm.filter_memory(row['text']): raise ValueError('memory drift')
    if state['rows']:
        memory_seal={k:shared.object_digest(r) for k,r in state['inductions'].items()}
        if json.loads((OUT/'memory_seal.json').read_text())!=memory_seal: raise ValueError('frozen memory drift')
    seen=set()
    for row in state['rows']:
        idx=row['index']
        if idx in seen or not 0<=idx<len(frozen['schedule']): raise ValueError('duplicate/invalid job')
        seen.add(idx)
        if any(row[k]!=v for k,v in frozen['schedule'][idx].items()): raise ValueError('schedule drift')
        key=row['family']+'|'+row['model'];rt=runtimes[key]
        if state['inductions'][key]['status']!='completed': raise ValueError('evaluation before induction')
        prior.audit_usage(row,frozen['prices'][row['model']])
        user=task(rt['name'],row['issue_number'])
        if row['arm']=='gac' and rt['name']!='issue_type':
            calls=[];d=premodel(rt,row['issue_number'],rt['registry'],calls)
            if row.get('compacted')!=d.compacted: raise ValueError('dispatch drift')
            if row['continuation_calls'][:len(calls)]!=calls: raise ValueError('prefetch drift')
            if d.compacted:
                user+='\nThe runtime already executed an approved guarded evidence plan. Do not call tools. Use only this source-grounded JSON evidence:\n'+json.dumps(d.observations[0].result,sort_keys=True,separators=(',',':'))
        inp=(prior.awm.memory_messages(state['inductions'][key]['memory']) if row['arm']=='awm_offline_adapted' else [])+[{'role':'user','content':user}]
        if row.get('model_input_digest') and row['model_input_digest']!=shared.object_digest(inp): raise ValueError('input drift')
        if row['status']=='completed' and not row.get('model_input_digest'): raise ValueError('missing input digest')
        if 'answer' in row:
            schema=prior.fixed.ExtractiveIssueTriageAnswer if rt['name']=='issue_type' else family.FAMILIES[rt['name']].answer_model
            schema.model_validate(row['answer'])
            q,correct=grade(rt,row['issue_number'],row['answer'],row['continuation_calls'])
            if q!=row['quality'] or correct!=row['correct']: raise ValueError('grade drift')
        elif row['status']=='completed': raise ValueError('missing answer')
        for c in row['continuation_calls']:
            if c['status']=='ok':
                value=(issue.execute_issue_snapshot(rt['store'],c['tool'],c['arguments']) if rt['name']=='issue_type'
                       else family.execute_snapshot(family.FAMILIES[rt['name']],rt['store'],c['tool'],c['arguments']))
                if shared.object_digest(value)!=c['output_digest']: raise ValueError('tool replay drift')


def pilot_valid(state):
    for name in COUNTS:
        for model in MODELS:
            rows=[r for r in state['rows'] if r['group']=='pilot' and r['family']==name and r['model']==model]
            if len(rows)!=18 or any(r['status']!='completed' for r in rows) or not any(r.get('compacted') for r in rows): return False
    return True


async def run(env_file):
    lock=OUT/'run.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
    try:
        frozen,runtimes=verify();path=OUT/'checkpoint.json'
        state=json.loads(path.read_text()) if path.exists() else dict(seal_sha256=shared.object_digest(frozen),
            inductions={},rows=[],pending={},halt_reason=None)
        audit(frozen,runtimes,state)
        if state['halt_reason']: raise ValueError('halted; no automatic resume')
        from dotenv import load_dotenv
        from openai import AsyncOpenAI
        from agents.models.openai_provider import OpenAIProvider
        load_dotenv(env_file)
        if not os.getenv('OPENAI_API_KEY'): raise ValueError('missing credential')
        async with AsyncOpenAI(max_retries=0) as client:
            for key,cell in frozen['cells'].items():
                if key in state['inductions']: continue
                if not reserve(frozen,state,key,{'induction':key}): break
                shared.write_json(path,state)
                model=runtimes[key]['model']
                row=await induce(cell,model,frozen['prices'][model],client)
                state['inductions'][key]=row;state['pending'].pop(key)
                if row['status']!='completed': state['halt_reason']='induction_failed'
                shared.write_json(path,state)
                if state['halt_reason']: break
            if state['halt_reason']: return {'halt_reason':state['halt_reason']}
            memory_seal={k:shared.object_digest(r) for k,r in state['inductions'].items()}
            mp=OUT/'memory_seal.json'
            if mp.exists() and json.loads(mp.read_text())!=memory_seal: raise ValueError('memory seal changed')
            shared.write_json(mp,memory_seal)
            failures=0;done={r['index'] for r in state['rows']}
            for group in ('pilot','primary'):
                if group=='primary' and not pilot_valid(state): state['halt_reason']='pilot_execution_gate';break
                groups={}
                for j in frozen['schedule']:
                    if j['group']==group and j['index'] not in done: groups.setdefault((j['family'],j['issue_number']),[]).append(j)
                queue=asyncio.Queue()
                for jobs in groups.values(): queue.put_nowait(jobs)
                async def worker():
                    nonlocal failures
                    while not queue.empty() and not state['halt_reason']:
                        jobs=queue.get_nowait()
                        for j in jobs:
                            if state['halt_reason'] or not reserve(frozen,state,str(j['index']),j): break
                            shared.write_json(path,state)
                            key=j['family']+'|'+j['model']
                            row=await execute(j,runtimes[key],state['inductions'][key]['memory'],frozen['prices'][j['model']],
                                OpenAIProvider(openai_client=client).get_model(j['model']))
                            state['rows'].append(row);state['pending'].pop(str(j['index']))
                            failures=failures+1 if row['status']=='failed' else 0
                            if failures>=5: state['halt_reason']='five_consecutive_failures'
                            shared.write_json(path,state)
                            if len(state['rows'])%24==0: print(json.dumps({'attempted':len(state['rows']),'scheduled':len(frozen['schedule']),
                                'failed':sum(r['status']=='failed' for r in state['rows']),'aggregate_usd':total(frozen,state)}),flush=True)
                        queue.task_done()
                await asyncio.gather(*(worker() for _ in range(CONCURRENCY)))
                if state['halt_reason']: break
        shared.write_json(path,state);audit(frozen,runtimes,state)
        return {'attempted':len(state['rows']),'halt_reason':state['halt_reason'],'aggregate_usd':total(frozen,state)}
    finally: lock.unlink()


def analyze():
    frozen,runtimes=verify();state=json.loads((OUT/'checkpoint.json').read_text());audit(frozen,runtimes,state)
    result={'checkpoint_sha256':shared.digest(OUT/'checkpoint.json'),'attempted':len(state['rows']),
            'scheduled':len(frozen['schedule']),'halt_reason':state['halt_reason'],
            'aggregate_estimate_and_reserve_usd':total(frozen,state),'cells':{}}
    for key,rt in runtimes.items():
        numbers=frozen['cohorts'][rt['name']]['primary']
        rows=[r for r in state['rows'] if r['group']=='primary' and r['family']==rt['name'] and r['model']==rt['model']]
        indexed={(r['issue_number'],r['arm']):r for r in rows}
        summaries={}
        for arm in ARMS:
            a=[r for r in rows if r['arm']==arm]
            summaries[arm]={'scheduled':len(numbers),'attempted':len(a),'completed':sum(r['status']=='completed' for r in a),
                'correct':sum(r['status']=='completed' and r.get('correct',False) for r in a),
                'metrics_total':{m:sum(r['metrics'][m] for r in a) for m in prior.METRICS},
                'accounting_complete':all(len(r['usage_observations'])==r['requests_started'] and not r['invalid_usage_indices'] for r in a)}
        def correct(n,arm):
            r=indexed.get((n,arm),{})
            return r.get('status')=='completed' and r.get('correct',False)
        losses=sum(correct(n,'awm_offline_adapted') and not correct(n,'gac') for n in numbers)
        gains=sum(correct(n,'gac') and not correct(n,'awm_offline_adapted') for n in numbers)
        upper=ni_bound(losses,len(numbers));complete=len(rows)==len(numbers)*3
        pairs=[(indexed[(n,'gac')],indexed[(n,'awm_offline_adapted')]) for n in numbers
               if all(indexed.get((n,a),{}).get('status')=='completed' for a in ('gac','awm_offline_adapted'))]
        contrasts={m:prior.interval([a['metrics'][m]-b['metrics'][m] for a,b in pairs]) for m in prior.METRICS} if pairs else {}
        from scipy.stats import binomtest
        result['cells'][key]={'arms':summaries,'gac_only_correct':gains,'awm_only_correct':losses,
            'loss_upper_bound':upper,'noninferior_5pp':complete and upper<.05,
            'noninferior_2pp_sensitivity':complete and upper<.02,'noninferior_1pp_sensitivity':complete and upper<.01,
            'mcnemar_p_descriptive':float(binomtest(min(losses,gains),losses+gains,.5).pvalue) if losses+gains else 1.,
            'complete_pairs':len(pairs),'resource_differences':contrasts,
            'induction_cost':state['inductions'].get(key,{}).get('metrics',{}).get('estimated_cost_usd'),
            'gate_equivalent':frozen['cells'][key]['probe']['all_equivalent']}
    result['pilot']={'attempted':sum(r['group']=='pilot' for r in state['rows']),
        'completed':sum(r['group']=='pilot' and r['status']=='completed' for r in state['rows']),
        'correct':sum(r['group']=='pilot' and r['status']=='completed' and r.get('correct',False) for r in state['rows'])}
    result['errors']=[{k:r.get(k) for k in ('index','family','model','issue_number','arm','status','quality','error')}
        for r in state['rows'] if r['status']!='completed' or not r.get('correct',False)]
    shared.write_json(OUT/'analysis.json',result)
    render_report(result,frozen)
    return result


def render_report(result,frozen):
    lines=['# Fresh generalization and gate attribution: retained results','',
        f"Attempted {result['attempted']}/{result['scheduled']}; halt reason: {result['halt_reason']}. "
        'Source regrading, tool replay, frozen-memory and usage audits passed.','',
        '| Family / model | GAC correct | AWM correct | Baseline correct | GAC-only / AWM-only correct | Loss upper bound | NI at 5pp |',
        '| --- | ---: | ---: | ---: | ---: | ---: | --- |']
    for key,c in result['cells'].items():
        a=c['arms'];n=a['gac']['scheduled']
        lines.append(f"| {key.replace('|',' / ')} | {a['gac']['correct']}/{n} | {a['awm_offline_adapted']['correct']}/{n} | {a['baseline']['correct']}/{n} | {c['gac_only_correct']} / {c['awm_only_correct']} | {100*c['loss_upper_bound']:.2f}% | {c['noninferior_5pp']} |")
    lines += ['', 'The one-sided loss bounds use 0.05/6 error probability. They conservatively bound accuracy loss by ignoring GAC-only successes. NI requires complete attempted pairs and an upper bound below 5 percentage points. Backlog has low prospective power. These are task-accuracy results, not runtime safety certificates.', '',
        '| Family / model | Arm | Attempted / completed | Requests / attempted | Tools / attempted | Estimated USD / 1000 attempted | Usage complete |',
        '| --- | --- | ---: | ---: | ---: | ---: | --- |']
    for key,c in result['cells'].items():
        for arm,a in c['arms'].items():
            n=a['attempted'];m=a['metrics_total']
            vals=[f"{m[k]/n:.3f}" if n else 'NA' for k in ('requests','total_tool_calls')]
            cost=f"{1000*m['estimated_cost_usd']/n:.3f}" if n else 'NA'
            lines.append(f"| {key.replace('|',' / ')} | {arm} | {n} / {a['completed']} | {vals[0]} | {vals[1]} | {cost} | {a['accounting_complete']} |")
    lines += ['', '## Gate attribution', '',
        'All full, support-only and deterministic-guard dispatch signatures matched across all 2,724 selected record/model cases (including pilot). This is exact provider-free routing/evidence agreement on already admitted candidates, not three independently sampled live arms or a new learned-gate benefit. Six issue records fell back identically on each model. The historical learned end-to-end gate retirement is unchanged.', '',
        '## Accounting and limits', '',
        f"Pilot: {result['pilot']}. Errors and failures are retained in analysis.json. Aggregate estimated spend plus retained reserves: ${result['aggregate_estimate_and_reserve_usd']:.8f} / $400. The cap is not a provider billing limit.", '',
        'Per-cell induction costs, paired resource intervals, tighter margin sensitivity and descriptive McNemar tests are in analysis.json. Resource means include all attempted episodes; paired intervals exclude incomplete pairs and disclose their denominators. Missing usage is not zero cost.', '',
        'One repository/snapshot, three workflows, two related models, shared historical discovery and one induced memory per cell. This is adapted AWM, not its native benchmark. Compiled evidence placement differs between workflow adapters. Independence across tasks/authors/time is not established. No broad cross-domain, independent human audit, gate safety or acceptance claim follows.']
    (OUT/'RESULTS.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=('prepare','verify','run','analyze'));p.add_argument('--env-file')
    args=p.parse_args()
    value=prepare() if args.command=='prepare' else ({'verified':True} if args.command=='verify' and verify() else
        asyncio.run(run(args.env_file)) if args.command=='run' else analyze())
    print(json.dumps(value,indent=2))
