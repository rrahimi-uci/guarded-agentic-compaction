import json, sys, collections, re
C = collections.Counter
d = json.load(open(sys.argv[1]))
fq = C(list(q['sub_task'])[0] for q in d)
print('distinct first sub-questions', len(fq), 'max multiplicity', max(fq.values()), 'queries in groups of size>1', sum(v for v in fq.values() if v > 1))
sq = C(sq for q in d for sq in q['sub_task'])
print('distinct sub-questions overall', len(sq), 'of', sum(sq.values()))
# union-find on shared first sub-question OR shared first-hop answer (norm)
n = len(d); par = list(range(n))
def find(x):
    while par[x] != x:
        par[x] = par[par[x]]; x = par[x]
    return x
def union(a, b): par[find(a)] = find(b)
norm = lambda s: re.sub(r'\W+', ' ', s.lower()).strip()
first = {}
for i, q in enumerate(d):
    for key in (('q', list(q['sub_task'])[0]), ('a', norm(list(q['sub_task'].values())[0]))):
        if key in first: union(i, first[key])
        else: first[key] = i
comp = C(find(i) for i in range(n))
print('components by shared first sub-question or first-hop answer', len(comp), 'largest', comp.most_common(3), 'singletons', sum(1 for v in comp.values() if v == 1))
sizes = sorted(comp.values(), reverse=True)
print('size distribution top10', sizes[:10])
