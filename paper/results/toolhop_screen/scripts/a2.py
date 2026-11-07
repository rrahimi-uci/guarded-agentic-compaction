import json,sys,collections,re,hashlib
d=json.load(open(sys.argv[1]))
C=collections.Counter
RETR=re.compile(r'(lookup|finder|retriev|info|search|query|identif|locator|fetch|get_|database|biograph|genealog|relationship|director|author|publication|history|historical)',re.I)
def chain(x):
    """ordered tool list: follow sub_task order; fall back to tools order"""
    ts=list(x['tools'].values())
    return ts
def sig(t):
    p=t['parameters']
    props=p.get('properties',{})
    req=p.get('required',[])
    return tuple(sorted((k,str(props[k].get('type','?')) if isinstance(props[k],dict) else '?') for k in req))
def fam(t):
    return 'R' if RETR.search(t['name']) else 'C'
def report(label,key,k):
    ops=C(); groups=collections.defaultdict(set)
    for x in d:
        ch=chain(x)
        if len(ch)<k: continue
        o=tuple(key(t) for t in ch[:k])
        groups[o].add(x['id'])
    sup=sorted(((len(v),o) for o,v in groups.items()),reverse=True)
    n=len(sup)
    print(f'{label} k={k}: distinct openings={n}; support>=2:{sum(s>=2 for s,_ in sup)} >=5:{sum(s>=5 for s,_ in sup)} >=30:{sum(s>=30 for s,_ in sup)} >=92:{sum(s>=92 for s,_ in sup)}; queries covered by openings with support>=5: {sum(s for s,_ in sup if s>=5)}, >=30: {sum(s for s,_ in sup if s>=30)}, >=92: {sum(s for s,_ in sup if s>=92)}')
    for s,o in sup[:5]: print('    ',s,o)
    return {'distinct':n,'ge2':sum(s>=2 for s,_ in sup),'ge5':sum(s>=5 for s,_ in sup),'ge30':sum(s>=30 for s,_ in sup),'ge92':sum(s>=92 for s,_ in sup),'cov5':sum(s for s,_ in sup if s>=5),'cov30':sum(s for s,_ in sup if s>=30),'cov92':sum(s for s,_ in sup if s>=92),'top':[(s,o) for s,o in sup[:5]]}
out={}
for k in (1,2,3):
    out[f'name_k{k}']=report('NAME',lambda t:t['name'],k)
for k in (1,2,3):
    out[f'namesig_k{k}']=report('NAME+REQSIG',lambda t:(t['name'],sig(t)),k)
for k in (1,2,3):
    out[f'sig_k{k}']=report('REQSIG only',lambda t:sig(t),k)
for k in (1,2,3):
    out[f'fam_k{k}']=report('RETR/COMPUTE+sig',lambda t:(fam(t),sig(t)),k)
for k in (1,2,3):
    out[f'famonly_k{k}']=report('RETR/COMPUTE',lambda t:fam(t),k)
# full-schema identity (name + full parameter schema json)
for k in (1,2):
    out[f'fullschema_k{k}']=report('FULL PARAM SCHEMA',lambda t:(t['name'],hashlib.sha1(json.dumps(t['parameters'],sort_keys=True).encode()).hexdigest()[:8]),k)
# is the first-hop tool a retrieval type?
print('first hop fam',C(fam(chain(x)[0]) for x in d))
json.dump(out,open(sys.argv[2],'w'),default=str,indent=1)
