"""Provider-free regression checks for prospective inference and live adapters."""
import asyncio
import copy
import json
from collections import Counter
from dataclasses import asdict
from types import SimpleNamespace
import pytest
import generalization_gate_study as s
import test_matched_reuse_baseline as old


def test_exact_loss_bound_and_prespecified_power():
    assert s.ni_bound(17,600)<.05<s.ni_bound(18,600)
    assert s.ni_bound(1,144)<.05<s.ni_bound(2,144)
    assert .93<s.power(600,.02)<.95
    assert s.ni_bound(600,600)==1
    with pytest.raises(ValueError):s.ni_bound(-1,10)


def test_schedule_balances_orders_and_models_without_independent_repeats():
    c={'issue_type':{'pilot':list(range(6)),'primary':list(range(6,18))}}
    jobs=s.schedule(c)
    assert len(jobs)==108
    assert len({(j['group'],j['issue_number'],j['model'],j['arm']) for j in jobs})==108
    for model in s.MODELS:
        selected=[j for j in jobs if j['group']=='primary' and j['model']==model]
        counts=Counter(tuple(j['arm'] for j in selected[i:i+3]) for i in range(0,len(selected),3))
        assert len(counts)==6 and set(counts.values())=={2}


def test_failed_pending_costs_and_invalid_budget():
    f={'budget':{'prior_estimate_and_reserve_usd':8.5},'cap':11.}
    r={'metrics':{'estimated_cost_usd':.1},'unknown_cost_reserve_usd':1.}
    state={'rows':[r],'inductions':{},'pending':{},'halt_reason':None}
    assert s.reserve(f,state,'a',{})
    assert s.total(f,state)==pytest.approx(10.6)
    assert not s.reserve(f,state,'b',{})
    with pytest.raises(ValueError):s.reserve(f,state,'a',{})
    f['cap']=float('nan')
    with pytest.raises(ValueError):s.reserve(f,state,'c',{})


@pytest.fixture(scope='module')
def runtimes():
    if not s.prior.fixed.DATA_PATH.exists():pytest.skip('optional local snapshot')
    return s.load_runtimes()[1]


def fake_family(rt,n,fail=False):
    from agents.models.interface import Model
    from agents.items import ModelResponse
    from openai.types.responses import ResponseFunctionToolCall,ResponseOutputMessage,ResponseOutputText
    class Local(Model):
        calls=0
        async def get_response(self,*args,**kwargs):
            kwargs={**dict(zip(('system_instructions','input','model_settings','tools','output_schema','handoffs','tracing'),args)),**kwargs}
            self.calls+=1
            assert kwargs['tracing'].is_disabled()
            assert kwargs['model_settings'].retry.max_retries==0
            if fail and self.calls==2:raise TimeoutError('secret must never be serialized')
            observed={v.get('name') for v in kwargs['input'] if v.get('type')=='function_call'}
            remaining=[t.name for t in kwargs['tools'] if t.name not in observed]
            if remaining:
                name=remaining[0];a={'record_number':n}
                if name==s.family.FAMILIES[rt['name']].tools[2]:a['limit']=3
                output=[ResponseFunctionToolCall(type='function_call',name=name,arguments=json.dumps(a),call_id=f'c{self.calls}',id=f'f{self.calls}')]
            else:
                row=rt['store'][n];comments=s.family._comments(row)
                answer={'record_number':n,'title':s.family.normalize_text(row['title']),
                        'comment_evidence':comments[0][:50] if comments else 'none'}
                if rt['name']=='pr_outcome':answer['outcome']=s.family.pr_outcome(row)
                else:
                    answer['route']=s.family.backlog_route(row)
                    answer['owner']=s.family.normalize_text((row.get('assignees') or [{}])[0].get('login')) if answer['route']=='owned' else 'none'
                output=[ResponseOutputMessage(id='final',type='message',role='assistant',status='completed',
                    content=[ResponseOutputText(type='output_text',annotations=[],text=json.dumps(answer))])]
            return ModelResponse(output=output,usage=old.response().usage,response_id=f'local{self.calls}')
        async def stream_response(self,*a,**kw):
            raise NotImplementedError
            yield
    return Local()


@pytest.mark.parametrize('name',s.COUNTS)
@pytest.mark.parametrize('model',s.MODELS)
@pytest.mark.parametrize('arm',s.ARMS)
def test_all_six_cells_real_sdk_with_offline_provider(runtimes,name,model,arm):
    rt=runtimes[name+'|'+model]
    discovery=json.loads(s.source_paths()[name].read_text())['results']
    n=next(r['issue_number'] for r in discovery if name!='issue_type' or len(rt['store'][r['issue_number']]['body'])>100)
    provider=old.fake_model(n,rt['store']) if name=='issue_type' else fake_family(rt,n)
    row=asyncio.run(s.execute(dict(index=0,group='pilot',family=name,model=model,issue_number=n,arm=arm),rt,'Read workflow.',old.prices(),provider))
    assert row['status']=='completed',row.get('error')
    assert row['correct']
    assert row['metrics']['total_tool_calls']==3
    expected=(2 if name=='issue_type' else 1) if arm=='gac' else 4
    assert row['metrics']['requests']==expected
    if arm=='gac':assert row['compacted']
    s.prior.audit_usage(row,old.prices())


def test_partial_failure_preserves_usage_and_safe_error(runtimes):
    rt=runtimes['pr_outcome|gpt-6-luna']
    n=json.loads(s.source_paths()['pr_outcome'].read_text())['results'][0]['issue_number']
    row=asyncio.run(s.execute(dict(index=0,group='pilot',family='pr_outcome',model='gpt-6-luna',issue_number=n,arm='baseline'),rt,'memory',old.prices(),fake_family(rt,n,True)))
    assert row['status']=='failed' and row['requests_started']==2
    assert len(row['usage'])==1 and row['unknown_cost_reserve_usd']==1
    assert 'secret must never' not in json.dumps(row)


def test_gate_ablation_preserves_candidate_and_continuation(runtimes):
    for key,rt in runtimes.items():
        original=rt['registry'].artifacts[0].to_dict()
        for arm in ('support_only','deterministic'):
            ablated=rt[arm].artifacts[0].to_dict()
            assert {k:v for k,v in original.items() if k!='gate'}=={k:v for k,v in ablated.items() if k!='gate'}
        n=json.loads(s.source_paths()[rt['name']].read_text())['results'][0]['issue_number']
        assert s.probe(rt,[n])['all_equivalent']
