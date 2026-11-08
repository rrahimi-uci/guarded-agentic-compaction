import os as _os
ROOT=_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", ".."))
import json,glob
from pathlib import Path
from scipy.stats import beta
P=Path(ROOT+'/paper')
def load(p): return json.load(open(p))
def ex(r):
    q=r.get('quality',{}); return bool(q.get('factuality_exact',q.get('overall',False)))
groups={}
def add(name,path,cond,repo=None):
    rows=[r for r in load(path).get('results',[]) if int(r.get('repeat',0))==0]
    key=lambda r: r.get('record_number',r.get('issue_number'))
    base={key(r):ex(r) for r in rows if r['condition']=='baseline'}
    comp={key(r):ex(r) for r in rows if r['condition']==cond}
    co=[k for k,v in comp.items() if base.get(k,False) and not v]
    qkeys=set()
    for r in rows:
        if r['condition']==cond: qkeys|=set(r.get('quality',{}).keys())
    groups.setdefault(name,[]).append((path.parent.name if repo is None else repo,len(comp),co,sorted(qkeys),[(repo or str(path), k) for k in comp]))
add('issue',P/'results/github_natural_replication/results.json','compiled','hf')
add('pr',P/'results/github_workflow_families/pr_outcome/final/results.json','compiled','hf')
add('backlog',P/'results/github_workflow_families/backlog_attention/final/results.json','compiled','hf')
for p in sorted((P/'results/github_multirepo_pr_outcome_core/repos').glob('*/results.json')): add('core',p,'compiled',p.parent.name)
for p in sorted((P/'results/github_multirepo_pr_outcome_balanced/repos').glob('*/results.json')): add('balanced',p,'compiled',p.parent.name)
for p in sorted((P/'results/github_multirepo_gate_frontier/repos').glob('*/results.json')): add('gf',p,'learned_gate',p.parent.name)
add('ext',P/'results/issue_type_extended_heldout/results.json','compiled','hf')
add('tf',P/'results/time_forward/pr_outcome/evaluation_checkpoint.json','compiled','hf-tf')
tot=0
outcome=set(); n_out=0
for g,lst in groups.items():
    n=sum(x[1] for x in lst); tot+=n
    print(g,n,[ (x[0],x[1],x[2]) for x in lst], lst[0][3])
    if g in ('core','balanced','gf'):
        n_out+=n
        for x in lst: outcome|=set((x[0],k) for _,k in x[4])
print('total',tot,'outcome eps',n_out,'distinct',len(outcome))
print('U(1,270,.95)',beta.ppf(.95,2,269),'U(1,270,.9)',beta.ppf(.9,2,269))
