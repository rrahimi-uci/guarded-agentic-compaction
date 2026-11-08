import os as _os
ROOT=_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", ".."))
import json,glob,os
from scipy.stats import beta
R=ROOT+'/paper/results/multirepo_end_to_end/'
def U(k,n,c): return 1-(1-c)**(1/n) if k==0 else beta.ppf(c,k+1,n-k)
tot={'n':0,'c':0,'b':0,'m':0,'k':0}
reg={'n':0,'k':0}
for p in sorted(glob.glob(R+'*/calibration_groups.json')):
    if 'fixture' in p: continue
    g=json.load(open(p)); n=len(g)
    c=sum(x['arms']['compiled']['contract_met'] for x in g)
    b=sum(x['arms']['baseline']['contract_met'] for x in g)
    m=sum(x['arms']['manual']['contract_met'] for x in g)
    # violation: compiled arm contract miss
    k=n-c
    cost=lambda a: sum(x['arms'][a]['cost_usd'] for x in g)
    print(os.path.basename(os.path.dirname(p)),n,c,b,m,'k',k,'U',round(U(k,n,1-0.1/11),4), 'costred',round(100*(1-cost('compiled')/cost('baseline')),2))
    for kk,v in zip('ncbmk',(n,c,b,m,k)): tot[kk]+=v
    if n<=200: reg['n']+=n; reg['k']+=k
print(tot, 'U',U(tot['k'],tot['n'],1-0.1/11)); print(reg, U(reg['k'],reg['n'],1-0.1/11))
