import os as _os
ROOT=_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", ".."))
import json,collections,glob
R=ROOT+'/paper/results/'
def ex(r):
    q=r['quality']; return bool(q.get('factuality_exact',q.get('overall')))
def study(p):
    d=json.load(open(R+p))
    rs=[r for r in d['results'] if int(r.get('repeat',0))==0]
    cnt=collections.Counter(r['condition'] for r in rs)
    by=collections.defaultdict(dict)
    for r in rs: by[r['issue_number']][r['condition']]=r
    exs={c:sum(ex(r) for r in rs if r['condition']==c) for c in cnt}
    co=[(i,{k:v for k,v in v['compiled']['quality'].items() if v is False}) for i,v in by.items() if 'compiled' in v and 'baseline' in v and not ex(v['compiled']) and ex(v['baseline'])]
    bo=[i for i,v in by.items() if 'compiled' in v and 'baseline' in v and ex(v['compiled']) and not ex(v['baseline'])]
    print(p,dict(cnt),exs,'compiled-only misses',co,'baseline-only',bo)
for p in ['second_model_replication/issue_type/results.json','github_workflow_families/pr_outcome/gpt6_luna/results.json','github_workflow_families/backlog_attention/gpt6_luna/results.json',
          'second_model_replication/issue_type_rediscovery/results.json','github_workflow_families/pr_outcome/gpt6_luna_rediscovery/results.json',
          'second_provider_replication/issue_type/results.json','github_workflow_families/pr_outcome/anthropic_sonnet5_rediscovery/results.json']:
    try: study(p)
    except Exception as e: print(p,'ERR',e)
