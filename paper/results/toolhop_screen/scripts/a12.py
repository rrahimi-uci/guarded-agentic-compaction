"""Cross-trace binder test for DEPENDENT arguments: family = previous tool NAME (any next tool),
env = {'z0': previous tool output}, target = dependent argument value. >=5 independent groups."""
import json, sys, re, collections
sys.path.insert(0, '/Users/rezarahimi/Documents/GitHub/personal/guarded-agentic-compaction/.claude/worktrees/agent-ab3faaa3a57b1a4c8/src')
from guarded_agentic_compaction.grc.dsl import SynthContext
from guarded_agentic_compaction.grc.synthesize import synthesize_binding
C = collections.Counter
data = json.load(open(sys.argv[1]))
rows = json.load(open(sys.argv[2]))['rows']
n = len(data); par = list(range(n))
def find(x):
    while par[x] != x:
        par[x] = par[par[x]]; x = par[x]
    return x
norm = lambda s: re.sub(r'\W+', ' ', s.lower()).strip()
first = {}
for i, q in enumerate(data):
    for key in (('q', list(q['sub_task'])[0]), ('a', norm(list(q['sub_task'].values())[0]))):
        if key in first: par[find(i)] = find(first[key])
        else: first[key] = i
grp = {q['id']: find(i) for i, q in enumerate(data)}
fam = collections.defaultdict(dict)
for r in rows:
    if not r['prev_ok'] or r['prev_output'] is None: continue
    fam[r['tool_prev']].setdefault((r['id'], r['i']), r)   # one leaf per step
res = []
for name, steps in fam.items():
    # one observation per independent group
    byg = {}
    for (qid, i), r in steps.items():
        byg.setdefault(grp[qid], r)
    obs = list(byg.values())
    if len(obs) < 5: continue
    envs = [{'z0': r['prev_output']} for r in obs]
    targets = [r['value'] for r in obs]
    groups = [str(grp[r['id']]) for r in obs]
    ctx = SynthContext.from_observations([*envs, *targets], max_depth=2)
    out = synthesize_binding('arg', envs, targets, groups, ctx=ctx, max_sources=40)
    res.append({'prev_tool': name, 'groups': len(obs), 'binding_found': out.ok, 'reason': out.reason,
                'binding': out.binding.to_dict() if out.binding else None})
res.sort(key=lambda r: -r['groups'])
print('previous-tool families with >=5 independent groups:', len(res), 'bindings found:', sum(r['binding_found'] for r in res))
print('groups covered by those families', sum(r['groups'] for r in res), 'found', sum(r['groups'] for r in res if r['binding_found']))
for r in res: print(r['prev_tool'], r['groups'], r['binding_found'], r['reason'], r['binding'] if r['binding_found'] else '')
json.dump(res, open(sys.argv[3], 'w'), indent=1)
