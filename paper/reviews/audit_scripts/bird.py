import os as _os
ROOT=_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", ".."))
import json,collections
from scipy.stats import binomtest
B=ROOT+'/paper/results/bird/'
dbs=['card_games','codebase_community','formula_1','student_club','thrombosis_prediction']
by=collections.defaultdict(dict); fails=0
for db in dbs:
    e=json.load(open(B+f'schema_first/{db}/evaluation.json')); fails+=len(e['failures'])
    for r in e['results']: by[(db,r['issue_number'])][r['condition']]=r
print('questions',len(by),'failures',fails)
ok=lambda r: bool(r and r['quality'].get('execution_correct'))
corr={c:sum(ok(v.get(c)) for v in by.values()) for c in ('baseline','baseline_repeat','compiled','manual_schema_prefetch')}
print('correct',corr)
disp=sum(1 for v in by.values() if v['compiled'].get('dispatch',{}).get('outcome')=='COMPACTED'); print('compiled dispatched',disp, collections.Counter(v['compiled'].get('dispatch',{}).get('outcome') for v in by.values()))
b=sum(ok(v['baseline']) and not ok(v['compiled']) for v in by.values()); c=sum(ok(v['compiled']) and not ok(v['baseline']) for v in by.values())
print('disc b-only',b,'c-only',c,'mcnemar',binomtest(min(b,c),b+c,0.5).pvalue)
for m in ('requests','wall_latency_ms','estimated_cost_usd'):
    s={k:sum(v[k]['metrics'][m] for v in by.values()) for k in ('baseline','baseline_repeat','compiled')}
    print(m,'vs warm repeat %.2f%%'%(100*(1-s['compiled']/s['baseline_repeat'])),'vs first baseline %.2f%%'%(100*(1-s['compiled']/s['baseline'])))
# question counts per db (dev)
P=json.load(open(B+'preflight.json'))
print(list(P.keys()))
cnt=collections.Counter()
for v in by.values():
    d=v['compiled'].get('dispatch',{}); cnt['compacted>=1']+= d.get('compacted',0)>=1; cnt['gate_rej']+=d.get('gate_rejections',0)
print(cnt)
