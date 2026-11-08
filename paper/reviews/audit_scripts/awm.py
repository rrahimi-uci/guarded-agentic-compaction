import os as _os
ROOT=_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", ".."))
import json,collections
from scipy.stats import beta
E=ROOT+'/experiments/generalization_gate/'
s=json.load(open(E+'checkpoint.json'));rows=s['rows']
print('rows',len(rows),collections.Counter(r['group'] for r in rows),collections.Counter(r['status'] for r in rows))
recs=collections.defaultdict(set)
for r in rows: recs[r['group']].add((r['family'],r['issue_number']))
print('distinct records by group',{g:len(v) for g,v in recs.items()},'all distinct',len({(r['family'],r['issue_number']) for r in rows}))
cells=collections.defaultdict(list)
for r in rows:
    if r['group']=='primary': cells[(r['family'],r['model'])].append(r)
for k,rs in sorted(cells.items()):
    by=collections.defaultdict(dict)
    for r in rs: by[r['issue_number']][r['arm']]=r
    n=len(by)
    ok=lambda r: r is not None and r['status']=='completed' and r.get('correct',False)
    corr={a:sum(ok(v.get(a)) for v in by.values()) for a in ('gac','awm_offline_adapted','baseline')}
    loss=sum(ok(v.get('awm_offline_adapted')) and not ok(v.get('gac')) for v in by.values())
    U=1.0 if loss==n else beta.ppf(1-0.05/6,loss+1,n-loss)
    tot={a:{m:sum(r['metrics'][m] for r in rs if r['arm']==a) for m in ('requests','estimated_cost_usd')} for a in ('gac','awm_offline_adapted')}
    att={a:sum(1 for r in rs if r['arm']==a) for a in ('gac','awm_offline_adapted')}
    req={a:tot[a]['requests']/att[a] for a in tot}
    usd={a:1000*tot[a]['estimated_cost_usd']/att[a] for a in tot}
    print(k,n,corr,'loss',loss,'100U=%.2f'%(100*U),'req/ep %.3f/%.3f'%(req['gac'],req['awm_offline_adapted']),'usd/1k %.3f/%.3f'%(usd['gac'],usd['awm_offline_adapted']),'saving %.1f%%'%(100*(1-usd['gac']/usd['awm_offline_adapted'])),'reqred %.1f%%'%(100*(1-req['gac']/req['awm_offline_adapted'])),'5pp',U<0.05,'2pp',U<0.02,'1pp',U<0.01)
