import json, sys, re, collections
C = collections.Counter
d = json.load(open(sys.argv[1]))
mean_n = sum(len(q['sub_task']) for q in d) / len(d)
print('mean tools/hops', mean_n, 'mean baseline requests (1 call per turn + final answer)', mean_n + 1, 'prefix-1 ceiling fraction', 1 / (mean_n + 1))
fr = [1 / (len(q['sub_task']) + 1) for q in d]
print('mean per-query ceiling', sum(fr) / len(fr))

def norm(s):
    return re.sub(r'\W+', ' ', s.lower()).strip()

def entities(q):
    out = set()
    items = list(q['sub_task'].items())
    for i, (sq, a) in enumerate(items[:-1]):
        a = norm(a)
        if len(a) >= 4 and not re.fullmatch(r'[\d\s]+', a):
            out.add(a)
    return out
parent = list(range(len(d)))
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]; x = parent[x]
    return x
ent2q = collections.defaultdict(list)
for i, q in enumerate(d):
    for e in entities(q):
        ent2q[e].append(i)
shared = {e: v for e, v in ent2q.items() if len(v) > 1}
for e, v in shared.items():
    for j in v[1:]:
        parent[find(j)] = find(v[0])
comp = C(find(i) for i in range(len(d)))
print('entities appearing in >1 query', len(shared), 'queries touched', len({i for v in shared.values() for i in v}))
print('components (entity-sharing) ', len(comp), 'largest', comp.most_common(3))
# question-level dup of first-hop sub-question
fq = C(list(q['sub_task'])[0] for q in d)
print('dup first sub-questions', sum(1 for v in fq.values() if v > 1))
fa = C(norm(list(q['sub_task'].values())[0]) for q in d)
print('queries sharing first-hop answer with another query', sum(v for v in fa.values() if v > 1), 'distinct', len(fa))
fe = C(norm(q['answer']) for q in d)
print('final-answer top', fe.most_common(8))
dom = C(q['domain'].strip().lower() for q in d)
print('domains (case-normalised)', len(dom), dom.most_common(10))
