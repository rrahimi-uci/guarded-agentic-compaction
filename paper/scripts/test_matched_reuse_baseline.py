"""Offline tests of external-source fidelity, real SDK execution and accounting."""
import asyncio
import copy
import json
import shutil
import socket
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import matched_reuse_baseline as study
from test_live_safeguard_recovery import response


def prices():
    return dict(input=1., output=2., cached_input=.1, cache_write=1.25)


def test_exact_upstream_functions_work_without_network(monkeypatch):
    monkeypatch.setattr(socket, 'create_connection', lambda *a,**k: pytest.fail('network forbidden'))
    result = study.awm.induction_request([{'confirmed_task': 'read issue', 'action_reprs': ['read(1)']}],
                                        'fixture', [{'name':'read'}])
    assert result['max_tokens']==1024 and result['temperature']==0 and result['model']=='fixture'
    text = result['messages'][0]['content']
    assert 'read-only API tasks' in text and 'read(1)' in text and '# Summary Workflows' in text
    assert (study.awm.VENDOR/'mind2web/prompt/one_shot_action.txt').read_text() in text
    memory = study.awm.filter_memory('# github\n\nWorkflow: read issue\n\n# delta\n\nother')
    assert memory=='Workflow: read issue'
    assert study.awm.memory_messages(memory)==[{'role':'user','content':memory}]


def test_vendor_tamper_fails_before_execution(monkeypatch,tmp_path):
    shutil.copytree(study.awm.VENDOR,tmp_path/'vendor')
    monkeypatch.setattr(study.awm,'VENDOR',tmp_path/'vendor')
    (study.awm.VENDOR/'mind2web/memory.py').write_text('def get_exemplars(args): return []')
    with pytest.raises(ValueError,match='upstream source changed'):
        study.awm.memory_messages('workflow')


def test_discovery_serialization_uses_only_eligible_actions():
    path=study.ROOT/'paper/results/github_natural_replication/discovery_checkpoint.json'
    rows=json.loads(path.read_text())
    examples=study.discovery_examples(rows)
    assert len(examples)==130
    assert all(set(e)=={'confirmed_task','action_reprs'} for e in examples)
    altered=copy.deepcopy(rows)
    for row in altered['results']:
        row['answer']={'secret':'held-out-oracle-must-not-leak'}
    assert study.discovery_examples(altered)==examples
    with pytest.raises(ValueError): study.discovery_examples({'results':[]})


def test_selection_exclusion_and_balanced_issue_orders():
    store={n:{'pull_request': n==200} for n in range(220)}
    pilot,primary,_=study.select(store,set(range(50)))
    assert len(set(pilot+primary))==126 and not set(pilot+primary)&(set(range(50))|{200})
    jobs=study.schedule(pilot,primary)
    assert len(jobs)==len({(j['issue_number'],j['arm']) for j in jobs})==378
    for group,count in [('pilot',1),('primary',20)]:
        selected=[j for j in jobs if j['group']==group]
        orders=Counter(tuple(j['arm'] for j in selected[i:i+3]) for i in range(0,len(selected),3))
        assert len(orders)==6 and set(orders.values())=={count}
    with pytest.raises(ValueError): study.select({},set())


def test_budget_carries_prior_partial_costs_failure_and_pending_reserves():
    frozen={'budget':{'prior_estimate_and_reserve_usd':7.27},'approved_aggregate_cap_usd':10.}
    state={'rows':[{'metrics':{'estimated_cost_usd':.2},'unknown_cost_reserve_usd':1}],
           'induction':{'metrics':{'estimated_cost_usd':.1},'unknown_cost_reserve_usd':0},'pending':{},'halt_reason':None}
    assert study.reserve(frozen,state,'one',{})
    assert study.budget_total(frozen,state)==pytest.approx(9.57)
    assert not study.reserve(frozen,state,'two',{})
    assert state['halt_reason']=='estimated_spend_guard'
    with pytest.raises(ValueError,match='duplicate'): study.reserve(frozen,state,'one',{})
    frozen['approved_aggregate_cap_usd']=float('nan')
    with pytest.raises(ValueError,match='invalid cap'): study.reserve(frozen,state,'two',{})


@pytest.fixture(scope='module')
def runtime():
    if not study.fixed.DATA_PATH.exists():
        pytest.skip('optional pinned snapshot unavailable; no download in tests')
    return study.shared.runtime()


def fake_model(number, store, fail=False):
    from agents.models.interface import Model
    from agents.items import ModelResponse
    from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage, ResponseOutputText
    class LocalModel(Model):
        calls=0
        async def get_response(self, *args, **kwargs):
            kwargs = {**dict(zip(('system_instructions','input','model_settings','tools','output_schema','handoffs','tracing'), args)), **kwargs}
            self.calls+=1
            assert kwargs['tracing'].is_disabled()
            assert kwargs['model_settings'].retry.max_retries==0
            assert kwargs['model_settings'].max_tokens==2048
            assert kwargs['system_instructions']==study.fixed.prompt_for(study.shared.TASK)
            if fail and self.calls==2:
                raise TimeoutError('do not retain this provider secret')
            observed={x.get('name') for x in kwargs['input'] if x.get('type')=='function_call'}
            remaining=[t.name for t in kwargs['tools'] if t.name not in observed]
            if remaining:
                name=remaining[0]
                args={'issue_number':number}
                if name=='issue_get_comments': args['limit']=3
                output=[ResponseFunctionToolCall(type='function_call',name=name,arguments=json.dumps(args),
                                                call_id=f'c{self.calls}',id=f'f{self.calls}')]
            else:
                source=store[number]
                category=study.fixed.category_for(source['labels'])
                answer={'issue_number':number,'category':category,'evidence_label':category if category!='other' else 'none',
                        'title':source['title'],'state':source['state'],'comment_count':len(source['comments']),
                        'evidence_excerpt':source['body'][:80]}
                output=[ResponseOutputMessage(id='final',type='message',role='assistant',status='completed',
                        content=[ResponseOutputText(type='output_text',annotations=[],text=json.dumps(answer))])]
            usage=response().usage
            usage.input_tokens_details.cache_write_tokens=70
            return ModelResponse(output=output,usage=usage,response_id=f'offline_{self.calls}')
        async def stream_response(self,*args,**kwargs):
            raise NotImplementedError
            yield
    return LocalModel()


def number_for(runtime):
    # Stable, in-range issue from historical discovery. No test selection changes.
    return next(r['issue_number'] for r in json.loads((study.ROOT/'paper/results/github_natural_replication/discovery_checkpoint.json').read_text())['results']
                if len(runtime[0][r['issue_number']]['body'])>100)


@pytest.mark.parametrize('arm',study.ARMS)
def test_real_sdk_all_arms_preserve_tools_usage_and_answers(runtime,arm):
    number=number_for(runtime)
    job={'index':0,'group':'pilot','issue_number':number,'arm':arm}
    model=fake_model(number,runtime[0])
    row=asyncio.run(study.execute(job,runtime,'Workflow: read issue tools.',prices(),model))
    assert row['status']=='completed',row.get('error')
    assert row['correct'] and row['quality']['factuality_exact']
    assert row['metrics']['total_tool_calls']==3
    assert row['metrics']['requests']==model.calls==(2 if arm=='gac' else 4)
    assert row['metrics']['cache_write_tokens']==70*model.calls
    assert row['model_input_digest']==study.shared.object_digest(study.model_input(number,arm,'Workflow: read issue tools.'))
    if arm=='gac': assert row['dispatch']['compacted']==1
    study.audit_usage(row,prices())


def test_partial_provider_failure_retains_usage_and_reserve(runtime):
    number=number_for(runtime)
    row=asyncio.run(study.execute({'index':0,'group':'primary','issue_number':number,'arm':'baseline'},
                                 runtime,'memory',prices(),fake_model(number,runtime[0],fail=True)))
    assert row['status']=='failed' and row['requests_started']==2 and len(row['usage'])==1
    assert row['metrics']['estimated_cost_usd']>0 and row['unknown_cost_reserve_usd']==1
    assert 'provider secret' not in json.dumps(row)
    study.audit_usage(row,prices())
    row['metrics']['estimated_cost_usd']=0
    with pytest.raises(ValueError,match='cost/metric'): study.audit_usage(row,prices())


@pytest.mark.parametrize('status',['completed','incomplete'])
def test_induction_no_retry_and_truncation_stop(status):
    called=[]
    async def create(**kwargs):
        called.append(kwargs)
        assert kwargs['max_output_tokens']==1024
        return SimpleNamespace(status=status,output_text='Workflow: use the issue tools',
            usage=SimpleNamespace(input_tokens=100,output_tokens=10,total_tokens=110,
                                  input_tokens_details=SimpleNamespace(cached_tokens=20,cache_write_tokens=70)))
    frozen={'induction_request':{'messages':[{'role':'user','content':'fixture'}]},'price_table':prices()}
    row=asyncio.run(study.induce(frozen,SimpleNamespace(responses=SimpleNamespace(create=create))))
    assert len(called)==1 and row['metrics']['cache_write_tokens']==70
    assert row['status']==('completed' if status=='completed' else 'failed')
    assert row['unknown_cost_reserve_usd']==(0 if status=='completed' else 1)


def test_pilot_gate_is_execution_based_not_accuracy():
    rows=[{'group':'pilot','status':'completed','correct':False,'dispatch':{'compacted':1}} for _ in range(18)]
    assert study.pilot_valid({'rows':rows})
    rows[0]['status']='failed'
    assert not study.pilot_valid({'rows':rows})


def test_boundary_bootstrap_does_not_change_marginal_uncertainty():
    from scipy.stats import binomtest
    assert study.interval([0]*120)['ci95']==[0,0]
    assert binomtest(120,120).proportion_ci().low<.97


def runner_fixture(monkeypatch,out,prior=0):
    import openai
    from agents.models.openai_provider import OpenAIProvider
    frozen={'pilot_numbers':list(range(1,7)),'primary_numbers':list(range(7,13)),
            'schedule':study.schedule(list(range(1,7)),list(range(7,13))),
            'price_table':prices(),'budget':{'prior_estimate_and_reserve_usd':prior},
            'approved_aggregate_cap_usd':400.,'induction_request':{'messages':[]},'reconstruction_wall_latency_ms':1}
    store={n:{'number':n,'labels':['bug'],'title':'A sufficiently long fixture title',
              'body':'A sufficiently long fixture body with evidence','comments':[],
              'state':'open','html_url':'https://example.invalid','day':'2026-01-01'} for n in range(1,13)}
    rt=(store,None,None,None,None,None,None)
    monkeypatch.setattr(study,'verify',lambda _: (frozen,rt))
    monkeypatch.setenv('OPENAI_API_KEY','offline-fixture')
    class Client:
        def __init__(self,**kwargs): assert kwargs=={'max_retries':0}
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
    monkeypatch.setattr(openai,'AsyncOpenAI',Client)
    monkeypatch.setattr(OpenAIProvider,'get_model',lambda *a: None)
    calls=[]
    async def induce(frozen,client):
        state=json.loads((out/'checkpoint.json').read_text())
        assert 'induction' in state['pending']
        row=study.record()
        row.update(status='completed',requests_started=1,text='Workflow: read issue',memory='Workflow: read issue',
            usage_observations=[{'input_tokens':100,'output_tokens':10,'total_tokens':110,'cached_input_tokens':20,'cache_write_tokens':70}])
        return study.finish(row,prices(),0)
    async def execute(job,runtime,memory,rate,model):
        state=json.loads((out/'checkpoint.json').read_text())
        assert str(job['index']) in state['pending'] and study.budget_total(frozen,state)<=400
        calls.append(job['index'])
        await asyncio.sleep(0)
        row={**study.record(),**job,'requests_started':1,'usage_observations':[
            {'input_tokens':100,'output_tokens':10,'total_tokens':110,'cached_input_tokens':20,'cache_write_tokens':70}]}
        number=job['issue_number']; source=store[number]
        row.update(status='completed',model_input_digest=study.shared.object_digest(study.model_input(number,job['arm'],memory)),
            answer={'issue_number':number,'category':'bug','evidence_label':'bug','title':source['title'],
                    'state':'open','comment_count':0,'evidence_excerpt':source['body']},dispatch={'compacted':int(job['arm']=='gac')})
        row['quality']=study.quality(number,row['answer'],[],store)
        row['correct']=all(row['quality'][f] for f in study.FIELDS)
        return study.finish(row,rate,0)
    monkeypatch.setattr(study,'induce',induce)
    monkeypatch.setattr(study,'execute',execute)
    return frozen,rt,calls,execute


def test_full_runner_pending_memory_seal_audit_and_idempotent_resume(monkeypatch,tmp_path):
    frozen,rt,calls,_=runner_fixture(monkeypatch,tmp_path)
    result=asyncio.run(study.run(tmp_path))
    assert result['completed']==result['attempted']==36 and not result['pending']
    state=json.loads((tmp_path/'checkpoint.json').read_text())
    assert study.audit(frozen,rt,state,tmp_path)=='Workflow: read issue'
    asyncio.run(study.run(tmp_path))
    assert len(calls)==len(set(calls))==36
    study.analyze(tmp_path)
    analysis=json.loads((tmp_path/'analysis.json').read_text())
    assert analysis['groups']['primary']['arms']['gac']['correct']==6
    pair=analysis['groups']['primary']['contrasts']['gac-minus-awm_offline_adapted']
    assert pair['mcnemar_holm_p']==1 and pair['completed_pairs']==6
    state['rows'].append(state['rows'][0])
    with pytest.raises(ValueError,match='duplicate'): study.audit(frozen,rt,state,tmp_path)


def test_pilot_failure_stops_primary_without_replacing_records(monkeypatch,tmp_path):
    frozen,rt,calls,base=runner_fixture(monkeypatch,tmp_path)
    async def fail_one(*args):
        row=await base(*args)
        if row['index']==0:
            row.update(status='failed',unknown_cost_reserve_usd=1)
        return row
    monkeypatch.setattr(study,'execute',fail_one)
    result=asyncio.run(study.run(tmp_path))
    assert result['halt_reason']=='pilot_execution_gate' and len(calls)==18
    with pytest.raises(ValueError,match='halted'): asyncio.run(study.run(tmp_path))


def test_pending_unknown_attempt_and_existing_lock_refuse_replay(monkeypatch,tmp_path):
    frozen,rt,calls,_=runner_fixture(monkeypatch,tmp_path)
    state={'seal_sha256':study.shared.object_digest(frozen),'induction':None,'rows':[],
           'pending':{'induction':{}},'halt_reason':None}
    study.shared.write_json(tmp_path/'checkpoint.json',state)
    with pytest.raises(ValueError,match='pending'): asyncio.run(study.run(tmp_path))
    assert not calls
    (tmp_path/'run.lock').write_text('existing')
    with pytest.raises(FileExistsError): asyncio.run(study.run(tmp_path))
    assert (tmp_path/'run.lock').exists()


def test_budget_guard_runs_before_induction(monkeypatch,tmp_path):
    frozen,rt,calls,_=runner_fixture(monkeypatch,tmp_path,prior=399.5)
    result=asyncio.run(study.run(tmp_path))
    assert result['halt_reason']=='estimated_spend_guard' and not calls
    assert json.loads((tmp_path/'checkpoint.json').read_text())['induction'] is None
