import os as _os
ROOT=_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", ".."))
import json,collections
R=ROOT+'/paper/results/'
for study in ['github_multirepo_pr_outcome_core','github_multirepo_pr_outcome_balanced']:
    d=json.load(open(R+study+'/results.json'))
    reps=d['repositories']; reps=reps if isinstance(reps,list) else list(reps.values())
    tot=collections.Counter(); B=collections.Counter(); C=collections.Counter(); Cd=collections.Counter(); Bd=collections.Counter()
    for r in reps:
        name=r.get('source',{}).get('repository') if isinstance(r.get('source'),dict) else None
        if 'results' not in r:
            print(study,'NO RUN',r.get('error','')[:400].replace('\n',' | ')); 
            sel=r.get('selection') or {}
            print('  sel',{k:v for k,v in sel.items() if 'count' in k} if isinstance(sel,dict) else '')
            continue
        g=r['compiler'].get('artifact',{}).get('gate',{}) if isinstance(r['compiler'].get('artifact'),dict) else {}
        res=[x for x in r['results'] if int(x.get('repeat',0))==0]
        cnt=collections.Counter(x['condition'] for x in res)
        ex={c:sum(1 for x in res if x['condition']==c and x['quality'].get('overall')) for c in cnt}
        base={x['issue_number']:x for x in res if x['condition']=='baseline'}
        comp={x['issue_number']:x for x in res if x['condition']=='compiled'}
        disp=[i for i,x in comp.items() if x.get('dispatch',{}).get('outcome')=='COMPACTED']
        for i in comp:
            B['req']+=base[i]['metrics']['requests']; C['req']+=comp[i]['metrics']['requests']
        for i in disp:
            Bd['req']+=base[i]['metrics']['requests']; Cd['req']+=comp[i]['metrics']['requests']
        print(study, r['source'].get('repository') if isinstance(r.get('source'),dict) else '', dict(cnt), ex, 'gate n/k/U',g.get('n_calibration_groups'),g.get('observed_violations'),g.get('risk_upper_bound'), 'dispatched',len(disp),'/',len(comp), 'tools',collections.Counter(tuple(x['tool_sequence']) for x in res if x['condition']=='baseline').most_common(1))
        for c in cnt: tot[c,'n']+=cnt[c]; tot[c,'ex']+=ex[c]
    print(study,dict(tot),'req reduction all',1-C['req']/B['req'],'dispatched only',1-Cd['req']/Bd['req'] if Bd['req'] else None)
