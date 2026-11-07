import json, sys, collections, re
C = collections.Counter
d = json.load(open(sys.argv[1]))
n = len(d); par = list(range(n))
def find(x):
    while par[x] != x:
        par[x] = par[par[x]]; x = par[x]
    return x
norm = lambda s: re.sub(r'\W+', ' ', s.lower()).strip()
first = {}
for i, q in enumerate(d):
    for key in (('q', list(q['sub_task'])[0]), ('a', norm(list(q['sub_task'].values())[0]))):
        if key in first: par[find(i)] = find(first[key])
        else: first[key] = i
grp = [find(i) for i in range(n)]
def sig(t):
    p = t['parameters']; props = p.get('properties', {})
    return tuple(sorted((k, str(props[k].get('type', '?')) if isinstance(props[k], dict) else '?') for k in p.get('required', []) if k in props))
out = {}
for label, key in (('name', lambda t: t['name']), ('name+reqsig', lambda t: (t['name'], sig(t))), ('reqsig', sig)):
    for k in (1, 2, 3):
        g = collections.defaultdict(set)
        for i, q in enumerate(d):
            ch = list(q['tools'].values())
            if len(ch) < k: continue
            g[tuple(key(t) for t in ch[:k])].add(grp[i])
        sup = sorted((len(v) for v in g.values()), reverse=True)
        r = {'distinct': len(sup), 'ge5': sum(s >= 5 for s in sup), 'ge30': sum(s >= 30 for s in sup), 'ge92': sum(s >= 92 for s in sup), 'max_group_support': sup[0]}
        out[f'{label}_k{k}'] = r
        print(label, k, r)
json.dump(out, open(sys.argv[2], 'w'), indent=1)
