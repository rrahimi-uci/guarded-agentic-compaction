import os as _os
ROOT=_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", ".."))
import json,collections,glob,os
B=ROOT+'/paper/results/bird/'
def cohort(paths,label,sched=None):
    by=collections.defaultdict(dict)
    for p in paths:
        db=p.split('/')[-2]
        for r in json.load(open(p))['results']: by[(db,r['issue_number'])][r['condition']]=r
    ok=lambda r: bool(r and r['quality'].get('execution_correct'))
    corr={c:sum(ok(v.get(c)) for v in by.values()) for c in ('baseline','baseline_repeat','compiled','manual_schema_prefetch')}
    pairs=[v for v in by.values() if 'baseline' in v and 'compiled' in v]
    red={m:round(100*(1-sum(v['compiled']['metrics'][m] for v in pairs)/sum(v['baseline']['metrics'][m] for v in pairs)),2) for m in ('requests','estimated_cost_usd')}
    wpairs=[v for v in by.values() if 'baseline_repeat' in v and 'compiled' in v]
    redw={m:round(100*(1-sum(v['compiled']['metrics'][m] for v in wpairs)/sum(v['baseline_repeat']['metrics'][m] for v in wpairs)),2) for m in ('requests',)}
    print(label,'questions',len(by),'dbs',len({k[0] for k in by}),corr,'pairs',len(pairs),'red vs base',red,'red vs warm',redw)
print(glob.glob(B+'replications/gpt-6-luna/*')[:5])
cohort(sorted(glob.glob(B+'replications/gpt-6-luna/schema_first/*/evaluation.json')),'second model gpt-6-luna')
cohort(sorted(glob.glob(B+'train/schema_first/*/evaluation.json')),'train')
