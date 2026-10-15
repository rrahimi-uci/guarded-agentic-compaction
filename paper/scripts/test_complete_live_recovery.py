"""Provider-free regression tests for completion accounting and execution."""
import asyncio
import copy
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import complete_live_recovery as study
from test_live_safeguard_recovery import source, artifact


def raw(**changes):
    return dict(input_tokens=1043,output_tokens=79,cached_input_tokens=0,
                cache_write_tokens=1040,total_tokens=1122,**changes) if not changes else {**raw(),**changes}


def test_observed_cache_write_failure_is_priced_once():
    prices=study.old.price_table()
    r=study.price_usage(raw(),prices)
    assert r['estimated_cost_usd']==pytest.approx((3*prices['input']+1040*prices['cache_write']+79*prices['output'])/1e6)
    r=study.price_usage(raw(cached_input_tokens=100,cache_write_tokens=900),prices)
    assert r['estimated_cost_usd']==pytest.approx((43*prices['input']+100*prices['cached_input']+900*prices['cache_write']+79*prices['output'])/1e6)


@pytest.mark.parametrize('changes',[{'cache_write_tokens':-1},{'cached_input_tokens':4},
    {'total_tokens':0},{'cache_write_tokens':True},{'cache_write_tokens':1044},{'input_tokens':0}])
def test_invalid_token_partition_is_not_zero_cost(changes):
    with pytest.raises(ValueError): study.price_usage(raw(**changes),study.old.price_table())


def test_all_permutations_balanced_and_cohorts_disjoint():
    confirmation=list(range(72)); replication=list(range(72,96))
    rows=study.schedule(confirmation,replication)
    assert len(rows)==len({(r['case_id'],r['arm']) for r in rows})==2304
    from collections import Counter
    for group,numbers in [('confirmation',confirmation),('replication',replication)]:
        for suite in study.old.offline.SUITES:
            for limit in (1,3,5):
                orders=Counter(tuple(r['arm'] for r in rows if r['case_id']==f'{n}:{suite}:{limit}') for n in numbers)
                assert len(orders)==24 and set(orders.values())=={len(numbers)//24}
    assert all(r['group']=='confirmation' for r in rows[:1728])


def fixture(monkeypatch,out,prior=0):
    import openai
    frozen={'confirmation':[1,2], 'replication':[], 'cases':study.old.offline.cases([1,2]),
        'schedule':study.schedule([1,2],[]),'configuration':{'price_table':study.old.price_table()},
        'prior_estimate_and_reserve_usd':prior}
    monkeypatch.setattr(study,'verify',lambda _: (frozen,source(),artifact()))
    monkeypatch.setenv('OPENAI_API_KEY','offline-fixture')
    class Client:
        def __init__(self,**kwargs): assert kwargs=={'max_retries':0}
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
    monkeypatch.setattr(openai,'AsyncOpenAI',Client)
    called=[]
    async def execute(case,arm,art,store,client,prices):
        state=json.loads((out/'checkpoint.json').read_text())
        assert any(r['case_id']==case['case_id'] and r['arm']==arm for r in state['pending'].values())
        assert study.budget_total(frozen,state)<=study.CAP
        called.append((case['case_id'],arm))
        await asyncio.sleep(0)
        context,_=study.old.initial_context(case,arm,art,store)
        row={'case_id':case['case_id'],'arm':arm,'status':'completed',**context['metadata'],
            'model_input_digest':study.old.object_digest(context['model_input']),
            'answer':study.old.offline.source_answer(case,store),'correct':True,'requests_started':1,
            'usage_observations':[raw()], 'continuation_calls':[], 'unknown_cost_reserve_usd':0}
        usage,invalid,totals=study.usage_account(row,prices)
        row.update(usage=usage,invalid_usage_indices=invalid,metrics={**totals,'wall_latency_ms':1})
        return row
    monkeypatch.setattr(study,'execute',execute)
    return frozen,called,execute


def test_concurrent_checkpoint_resume_idempotence_and_analysis(monkeypatch,tmp_path):
    frozen,called,_=fixture(monkeypatch,tmp_path)
    result=asyncio.run(study.run(tmp_path))
    assert result['attempted']==48 and result['completed']==48 and len(called)==48
    state=json.loads((tmp_path/'checkpoint.json').read_text())
    assert not state['pending']
    assert study.audit(frozen,source(),artifact(),state)
    asyncio.run(study.run(tmp_path))
    assert len(called)==48
    report=study.analyze(tmp_path)
    assert report['audit_passed'] and report['all_scheduled_attempted']
    pair=report['groups']['confirmation']['ordinary']['paired_vs_full']['baseline']
    assert pair['paired_intervals']['accuracy_full_minus_other']['ci95']==[0,0]


def test_failed_attempt_retained_but_other_cases_continue(monkeypatch,tmp_path):
    _,called,base=fixture(monkeypatch,tmp_path)
    async def fail_one(*args):
        r=await base(*args)
        if r['case_id']=='1:ordinary:1' and r['arm']=='baseline':
            r.update(status='failed',unknown_cost_reserve_usd=1,error={'stage':'runner_processing','error_type':'TimeoutError'})
        return r
    monkeypatch.setattr(study,'execute',fail_one)
    result=asyncio.run(study.run(tmp_path))
    assert result['attempted']==48 and result['completed']==47 and len(called)==48
    report=study.analyze(tmp_path)
    pair=report['groups']['confirmation']['ordinary']['paired_vs_full']['baseline']
    assert pair['full_only_correct']==1
    assert 'requests_full_minus_other' not in pair['paired_intervals']


def test_pending_reserves_stop_new_work_before_budget_exhaustion(monkeypatch,tmp_path):
    _,called,_=fixture(monkeypatch,tmp_path,prior=198.999999)
    result=asyncio.run(study.run(tmp_path))
    assert len(called)==1 and result['halt_reason']=='budget_guard'
    assert result['aggregate_estimate_and_reserve_usd']<=200
    with pytest.raises(ValueError,match='halted'): asyncio.run(study.run(tmp_path))


def test_repeated_failures_open_circuit_without_retry(monkeypatch,tmp_path):
    _,called,base=fixture(monkeypatch,tmp_path)
    async def fail(*args):
        r=await base(*args)
        r.update(status='failed',unknown_cost_reserve_usd=1,error={'stage':'runner_processing','error_type':'TimeoutError'})
        return r
    monkeypatch.setattr(study,'execute',fail)
    result=asyncio.run(study.run(tmp_path))
    assert result['halt_reason']=='five_consecutive_execution_failures'
    assert 5<=len(called)<=8 and len(called)==len(set(called))
    with pytest.raises(ValueError,match='halted'): asyncio.run(study.run(tmp_path))


def test_pending_and_lock_refuse_automatic_replay(monkeypatch,tmp_path):
    frozen,called,_=fixture(monkeypatch,tmp_path)
    state={'seal_sha256':study.old.object_digest(frozen),'approved_aggregate_cap_usd':200,
           'rows':[],'pending':{'0':frozen['schedule'][0]},'halt_reason':None}
    study.old.write_json(tmp_path/'checkpoint.json',state)
    with pytest.raises(ValueError,match='interrupted'): asyncio.run(study.run(tmp_path))
    assert not called
    (tmp_path/'run.lock').write_text('existing')
    with pytest.raises(FileExistsError): asyncio.run(study.run(tmp_path))
    assert (tmp_path/'run.lock').exists()


def test_cache_write_cost_tampering_rejected(monkeypatch,tmp_path):
    frozen,_,_=fixture(monkeypatch,tmp_path)
    asyncio.run(study.run(tmp_path))
    state=json.loads((tmp_path/'checkpoint.json').read_text())
    state['rows'][0]['usage'][0]['estimated_cost_usd']=0
    with pytest.raises(ValueError,match='usage/cost'): study.audit(frozen,source(),artifact(),state)


def test_safe_exception_has_no_message_or_source_text():
    from recovery_observation import safe_error
    try:
        raise ValueError('credential-or-provider-content-must-not-appear')
    except ValueError as exc:
        r=safe_error(exc,'usage_validation')
    assert r['error_type']=='ValueError' and r['frames']
    assert 'credential' not in json.dumps(r)


def test_bootstrap_groups_variants_before_resampling():
    result=study.cluster_interval([1,-1,0])
    assert result['mean']==0 and result['issue_groups']==3
    assert result==study.cluster_interval([1,-1,0])


def test_real_sdk_loop_retains_and_prices_cache_write_usage(monkeypatch):
    from agents.models.interface import Model
    from agents.models.openai_provider import OpenAIProvider
    from agents.items import ModelResponse
    from openai.types.responses import ResponseOutputMessage, ResponseOutputText, ResponseFunctionToolCall
    from test_live_safeguard_recovery import response, case
    class RepairModel(Model):
        count=0
        async def get_response(self,**kwargs):
            self.count+=1
            assert kwargs['tracing'].is_disabled()
            assert kwargs['model_settings'].retry.max_retries==0
            if self.count==1:
                output=[ResponseFunctionToolCall(type='function_call',name='read_comment_page',
                    arguments=json.dumps({'issue_number':10,'offset':3,'limit':2}),call_id='repair',id='fc_repair')]
            else:
                assert any(x.get('type')=='function_call_output' and 'error four' in x.get('output','') for x in kwargs['input'])
                output=[ResponseOutputMessage(id='final',type='message',role='assistant',status='completed',
                    content=[ResponseOutputText(type='output_text',annotations=[],text=json.dumps(
                        {'issue_number':10,'comment_count':5,'matching_positions':[2,4]}))])]
            usage=response().usage
            usage.input_tokens_details.cache_write_tokens=70
            return ModelResponse(output=output,usage=usage,response_id=f'offline_{self.count}')
        async def stream_response(self,*args,**kwargs):
            raise NotImplementedError
            yield
    model=RepairModel()
    monkeypatch.setattr(OpenAIProvider,'get_model',lambda *args:model)
    r=asyncio.run(study.execute(case(5),'no_entry_hull',artifact(),source(),None,study.old.price_table()))
    assert r['status']=='completed' and r['correct']
    assert r['metrics']['cache_write_tokens']==140 and r['metrics']['requests']==2
    assert r['metrics']['total_tool_calls']==3
    assert len(r['usage_observations'])==2 and 'raw_responses' not in r


def test_runner_failure_retains_prior_response_usage(monkeypatch):
    from agents.models.interface import Model
    from agents.models.openai_provider import OpenAIProvider
    from agents.items import ModelResponse
    from openai.types.responses import ResponseFunctionToolCall
    from test_live_safeguard_recovery import response, case
    class FailingModel(Model):
        count=0
        async def get_response(self,**kwargs):
            self.count+=1
            if self.count==2: raise TimeoutError('secret must not appear')
            return ModelResponse(output=[ResponseFunctionToolCall(type='function_call',name='read_comment_page',
                arguments=json.dumps({'issue_number':10,'offset':0,'limit':3}),call_id='read',id='fc_read')],
                usage=response().usage,response_id='offline_partial')
        async def stream_response(self,*args,**kwargs):
            raise NotImplementedError
            yield
    monkeypatch.setattr(OpenAIProvider,'get_model',lambda *args:FailingModel())
    r=asyncio.run(study.execute(case(),'baseline',artifact(),source(),None,study.old.price_table()))
    assert r['status']=='failed' and r['error']['stage']=='model_request'
    assert r['requests_started']==2 and len(r['usage'])==1
    assert r['metrics']['estimated_cost_usd']>0 and r['unknown_cost_reserve_usd']==1
    assert 'secret' not in json.dumps(r)
