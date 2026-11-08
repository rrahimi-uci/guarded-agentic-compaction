import os as _os
ROOT=_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", ".."))
import json
R=ROOT+'/paper/results/'
fams=[('issue','github_natural_replication/results.json','macro'),
      ('pr','github_workflow_families/pr_outcome/final/results.json','manual_pre_model'),
      ('backlog','github_workflow_families/backlog_attention/final/results.json','manual_pre_model')]
M=['requests','tool_calls','total_tokens','wall_latency_ms','estimated_cost_usd']
pool={c:{m:0.0 for m in M} for c in ['baseline','compiled','manual']}
pe={c:[0,0,0] for c in pool}
for name,p,man in fams:
    d=json.load(open(R+p))
    rows={}
    for c,cn in [('baseline','baseline'),('compiled','compiled'),('manual',man)]:
        rs=[r for r in d['results'] if r['condition']==cn and int(r.get('repeat',0))==0]
        rows[c]=rs
        s={m:sum(float(r['metrics'].get(m) or 0) for r in rs) for m in M}
        fe=sum(bool(r['quality'].get('factuality_exact',r['quality'].get('overall'))) for r in rs)
        ov=sum(bool(r['quality'].get('overall')) for r in rs)
        tc=sum(bool(r['quality'].get('tool_contract')) for r in rs)
        print(name,c,len(rs),'exact(fact/overall/toolcontract)',fe,ov,tc,{m:round(v,6) for m,v in s.items()})
        for m in M: pool[c][m]+=s[m]
        pe[c][0]+=len(rs);pe[c][1]+=fe;pe[c][2]+=ov
        if c=='baseline':
            miss=[r['issue_number'] for r in rs if not r['quality'].get('factuality_exact',r['quality'].get('overall'))]
            print(' baseline misses',miss,[ {k:v for k,v in r['quality'].items() if v is False} for r in rs if r['issue_number'] in miss])
    ids=[sorted(int(r['issue_number']) for r in rows[c]) for c in rows]
    assert ids[0]==ids[1]==ids[2]
    b={m:sum(float(r['metrics'].get(m) or 0) for r in rows['baseline']) for m in M}
    cc={m:sum(float(r['metrics'].get(m) or 0) for r in rows['compiled']) for m in M}
    print(name,'reductions %',{m:round(100*(1-cc[m]/b[m]),2) for m in M})
print('pooled exact',pe)
print('pooled reductions %',{m:round(100*(1-pool['compiled'][m]/pool['baseline'][m]),3) for m in M})
print('manual pooled reductions %',{m:round(100*(1-pool['manual'][m]/pool['baseline'][m]),3) for m in M})
print('manual vs compiled', {m:(pool['manual'][m],pool['compiled'][m]) for m in M})
