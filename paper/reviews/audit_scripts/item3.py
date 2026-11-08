import os as _os
ROOT=_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", ".."))
import json,glob,os
from scipy.stats import beta
R=ROOT+'/paper/results/multirepo_end_to_end/'
def U(k,n,conf):
    if n==0 or k>=n: return 1.0
    if k==0: return 1-(1-conf)**(1/n)
    return float(beta.ppf(conf,k+1,n-k))
G=1-0.1/11
S=json.load(open(R+'summary.json'))
stage={r['repo']:r.get('stage') for r in S['repositories']}
rows=[];allg=[]
for d in sorted(glob.glob(R+'*/calibration_groups.json')):
    if '/fixture/' in d: continue
    g=json.load(open(d)); repo=g[0]['repo']
    c=lambda x:x['arms']['compiled']
    inn=[x for x in g if c(x)['eligible'] and (c(x)['dispatched'] or c(x)['verifier_abstained'])]
    k=sum(1 for x in inn if c(x)['dispatched'] and not c(x)['contract_met'])
    n=len(inn)
    met={a:sum(1 for x in g if x['arms'][a]['contract_met']) for a in ('compiled','baseline','manual')}
    authors=len({x['author'] for x in g})
    rows.append((repo,stage.get(repo),len(g),n,k,round(U(k,n,G),4),round(U(k,n,0.9),4),'admit' if U(k,n,G)<=0.05 else 'retire',met,authors))
    allg+=g
for r in rows: print(r)
def pool(gs):
    c=lambda x:x['arms']['compiled']
    inn=[x for x in gs if c(x)['eligible'] and (c(x)['dispatched'] or c(x)['verifier_abstained'])]
    k=sum(1 for x in inn if c(x)['dispatched'] and not c(x)['contract_met']); n=len(inn)
    met={a:sum(1 for x in gs if x['arms'][a]['contract_met']) for a in ('compiled','baseline','manual')}
    res={}
    for a in ('compiled','manual'):
        res[a]={m:round(100*(1-sum(x['arms'][a][m] for x in gs)/sum(x['arms']['baseline'][m] for x in gs)),2) for m in ('cost_usd','requests','tokens','latency_ms')}
    return len(gs),n,k,round(U(k,n,G),4),round(U(k,n,0.9),4),met,res
reg=[x for x in allg if stage.get(x['repo'])=='registered']
a3=[x for x in allg if stage.get(x['repo'])=='amendment_3']
print('registered repos',sorted({x['repo'] for x in reg}),pool(reg))
print('amendment3 repos',sorted({x['repo'] for x in a3}),pool(a3))
print('all',pool(allg))
