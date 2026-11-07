"""Provider-free derivability analysis of reconstructed ToolHop gold chains.

Inputs: dataset JSON, directory of runner chunk*.jsonl (sandbox outputs), output json.
Uses the repo's closed transform library (T-v1) and binder, read-only.
"""
import glob, json, sys, re, collections, random
sys.path.insert(0, '/Users/rezarahimi/Documents/GitHub/personal/guarded-agentic-compaction/.claude/worktrees/agent-ab3faaa3a57b1a4c8/src')
from guarded_agentic_compaction.grc.dsl import SynthContext, search_chains
from guarded_agentic_compaction.grc.synthesize import synthesize_binding

C = collections.Counter
data = {q['id']: q for q in json.load(open(sys.argv[1]))}
runs = {}
for f in sorted(glob.glob(sys.argv[2] + '/all.jsonl')):
    for line in open(f):
        r = json.loads(line)
        runs[r['id']] = r
print('queries processed', len(runs))

def norm(s):
    return re.sub(r'\s+', ' ', str(s)).strip().lower()

def leaves(v, out=None, path=''):
    if out is None: out = []
    if isinstance(v, dict):
        for k, x in v.items(): leaves(x, out, f'{path}.{k}' if path else k)
    elif isinstance(v, list):
        for i, x in enumerate(v): leaves(x, out, f'{path}[{i}]')
    elif isinstance(v, bool) or v is None:
        pass
    else:
        out.append((path, v))
    return out

def sval(x):
    if isinstance(x, float) and x.is_integer(): return str(int(x))
    return str(x)

# ---------- 1. coverage ----------
status = C(); by_hop = collections.defaultdict(C)
for r in runs.values():
    for s in r['steps']:
        st = s['status'].split(':')[0] + (':' + s['status'].split(':')[1] if s['status'].startswith('unsafe') else '')
        status[s['status'] if not s['status'].startswith('unsafe') else 'unsafe'] += 1
        by_hop['hop0' if s['i'] == 0 else 'hop>=1'][s['status'] if not s['status'].startswith('unsafe') else 'unsafe'] += 1
unsafe_reasons = C(s['status'] for r in runs.values() for s in r['steps'] if s['status'].startswith('unsafe'))
print('step status', dict(status)); print('by hop', {k: dict(v) for k, v in by_hop.items()})
print('unsafe reasons', unsafe_reasons.most_common(12))
nsteps = sum(len(r['steps']) for r in runs.values())
q_full = sum(all(s['status'] == 'ok' for s in r['steps']) for r in runs.values())
print('steps', nsteps, 'queries with every step reconstructed', q_full)
amb = C(min(s.get('n_success', 0), 5) for r in runs.values() for s in r['steps'] if s['status'] == 'ok')
print('n_success (capped 5) among ok', dict(amb))

# ---------- 2. dependent arguments ----------
random.seed(0)
rows = []
for r in runs.values():
    steps = r['steps']
    for i, s in enumerate(steps):
        if i == 0 or s['status'] != 'ok': continue
        prev = steps[i - 1]
        prev_ans = prev['answer']
        pa = norm(prev_ans)
        # candidate dependent leaves: arg leaves related to previous answer
        dep = []
        for path, v in leaves(s['args']):
            sv = norm(sval(v))
            if not sv: continue
            if sv == pa or (len(sv) >= 2 and sv in pa) or (len(pa) >= 2 and pa in sv):
                dep.append((path, v))
            else:
                # token overlap (>=1 token len>=3) e.g. 'Stanley Park' vs 'Stanley Park, Blackpool'
                tv = set(re.findall(r'\w{3,}', sv)); tp = set(re.findall(r'\w{3,}', pa))
                if tv and tp and (tv & tp) and len(tv & tp) >= max(1, min(len(tv), len(tp)) // 2) and not sv.isdigit():
                    dep.append((path, v))
        for path, v in dep:
            rows.append({'id': r['id'], 'i': i, 'arg_path': path, 'value': sval(v), 'prev_answer': prev_ans,
                         'prev_ok': prev['status'] == 'ok', 'prev_output': prev.get('output'), 'tool': s['name'],
                         'tool_prev': prev['name'], 'n_args_total': len(leaves(s['args']))})
steps_ok_dep = {(r['id'], r['i']) for r in rows}
n_dep_steps_candidates = sum(1 for r in runs.values() for i, s in enumerate(r['steps']) if i > 0 and s['status'] == 'ok')
print('dependent steps (i>=1, reconstructed)', n_dep_steps_candidates, 'with >=1 dependent arg leaf', len(steps_ok_dep), 'dependent arg leaves', len(rows))

ctx_cache = {}
def baked(chain):
    # a chain whose fmt template embeds alphabetic constants copied from the target is
    # constant-baking (overfits one instance), not a derivation; reject it
    for o in chain:
        t = str(o)
        if t.startswith('fmt('):
            tmpl = t[4:-1].strip("'\"")
            if re.search(r'[A-Za-z]', tmpl.replace('{}', '')):
                return True
    return False
def classify(row):
    v = row['value']; pa = row['prev_answer']
    cat = {}
    cat['answer_relation'] = 'copy_of_prev_answer' if v == str(pa) else ('case_or_ws_variant' if norm(v) == norm(pa) else 'reformulation_of_prev_answer')
    if not row['prev_ok']:
        cat['output_relation'] = 'prev_output_unavailable'
        return cat
    out = row['prev_output']
    ls = leaves(out) if not isinstance(out, (str, int, float)) else [('', out)]
    # (a) identity / structured field access: a leaf equal to v
    exact = [(p, x) for p, x in ls if sval(x) == v]
    if exact:
        whole = isinstance(out, (str, int, float))
        cat['output_relation'] = 'identity_of_whole_output' if whole else 'field_access_copy'
        cat['chain'] = []
        return cat
    # (b) T-v1 chain depth<=2 from any string leaf (or serialised output)
    best = None
    cands = [(p, x) for p, x in ls if isinstance(x, str) and v in x]
    if not cands:
        cands = [(p, x) for p, x in ls if isinstance(x, str) and norm(v) in norm(x)]
    for p, x in cands[:4]:
        try:
            ctx = SynthContext.from_observations([x, v], max_depth=2)
            res = [c for c in search_chains(x, v, ctx, max_results=8) if not baked(c)]
        except Exception as e:
            res = []
        if res:
            ch = res[0]
            if best is None or len(ch) < len(best[1]):
                best = (p, ch)
    if best:
        cat['output_relation'] = 'string_op_chain_in_T-v1(depth<=2)'
        cat['chain'] = [str(o) for o in best[1]]
        cat['chain_depth'] = len(best[1])
        return cat
    if cands:
        cat['output_relation'] = 'substring_of_output_but_no_T-v1_chain'
        return cat
    # (c) absent from output
    if norm(v) and any(norm(v) in norm(sval(x)) or norm(sval(x)) in norm(v) for p, x in ls if len(norm(sval(x))) >= 2):
        cat['output_relation'] = 'overlaps_output_not_substring'
    else:
        cat['output_relation'] = 'absent_from_prev_output'
    return cat

for row in rows:
    row.update(classify(row))
tab = C(r['output_relation'] for r in rows)
print('output_relation', tab)
print('answer_relation', C(r['answer_relation'] for r in rows))
print('cross', C((r['answer_relation'], r['output_relation']) for r in rows).most_common(20))
print('chain ops (depth1+)', C(tuple(r.get('chain', [])) for r in rows if r.get('chain')).most_common(15))

# Per-dependent-step view (a step is "derivable by T-v1 from prior result" if ALL its dependent leaves are copy/field/string-chain)
def derivable(row):
    return row['output_relation'] in ('identity_of_whole_output', 'field_access_copy', 'string_op_chain_in_T-v1(depth<=2)')
step_rows = collections.defaultdict(list)
for r in rows: step_rows[(r['id'], r['i'])].append(r)
ds = sum(all(derivable(x) for x in v) for v in step_rows.values())
print('dependent steps with all dependent leaves instance-expressible in T-v1 (single trace):', ds, 'of', len(step_rows))
ds_strict = sum(all(x['output_relation'] in ('identity_of_whole_output', 'field_access_copy') for x in v) for v in step_rows.values())
print('... of which pure identity/field copy only:', ds_strict)

# sample for manual audit
random.shuffle(rows)
sample = rows[:120]
json.dump({'rows': rows}, open(sys.argv[3] + '/dep_rows.json', 'w'), ensure_ascii=False, default=str)
json.dump({'sample': sample[:120]}, open(sys.argv[3] + '/dep_sample.json', 'w'), ensure_ascii=False, default=str, indent=1)

# ---------- 3. hop-0 arguments: derivable from the entry question? ----------
h0 = []
for r in runs.values():
    s = r['steps'][0]
    if s['status'] != 'ok': continue
    q = data[r['id']]['question']
    for path, v in leaves(s['args']):
        if isinstance(v, str) and (v.lower() in q.lower() or norm(v) in norm(q)):
            h0.append({'id': r['id'], 'tool': s['name'], 'param': path, 'value': v, 'question': q, 'sq0': s['subq']})
print('hop0 ok', sum(1 for r in runs.values() if r['steps'][0]['status'] == 'ok'), 'hop0 string args that are substrings of the entry question', len(h0))
# instance-level T-v1 expressibility from question
inst = 0; inst_chain = C()
for x in h0:
    ctx = SynthContext.from_observations([x['question'], x['value']], max_depth=2)
    res = [c for c in search_chains(x['question'], x['value'], ctx, max_results=8) if not baked(c)]
    if res:
        inst += 1; inst_chain[tuple(str(o) for o in res[0])] += 1
print('hop0 substring args with an instance-level T-v1 chain (question->value):', inst, 'of', len(h0))
print('top chains', inst_chain.most_common(5))
# cross-instance binding by family (tool name, param) with support >= 5 distinct first sub-questions
fam = collections.defaultdict(list)
for x in h0: fam[(x['tool'], x['param'])].append(x)
fam_res = []
for k, xs in fam.items():
    # one observation per distinct first-sub-question group
    seen = {};
    for x in xs: seen.setdefault(x['sq0'], x)
    xs = list(seen.values())
    if len(xs) < 5: continue
    envs = [{'entry': {'question': x['question']}} for x in xs]
    targets = [x['value'] for x in xs]
    groups = [x['sq0'] for x in xs]
    ctx = SynthContext.from_observations([*envs, *targets], max_depth=2)
    res = synthesize_binding('arg', envs, targets, groups, ctx=ctx, max_sources=40)
    fam_res.append({'family': list(k), 'support_groups': len(xs), 'binding_found': res.ok, 'reason': res.reason,
                    'binding': res.binding.to_dict() if res.binding else None})
fam_res.sort(key=lambda r: -r['support_groups'])
print('families (tool,param) with support>=5 groups tested:', len(fam_res), 'bindings found:', sum(r['binding_found'] for r in fam_res))
for r in fam_res[:12]: print('   ', r['family'], r['support_groups'], r['binding_found'], r['reason'])
json.dump({'tab': dict(tab), 'answer_relation': dict(C(r['answer_relation'] for r in rows)), 'fam_res': fam_res,
           'hop0_args': len(h0), 'hop0_instance_chain': inst}, open(sys.argv[3] + '/derivability.json', 'w'), indent=1, default=str)

# ---------- 4. other (non-dependent, non-entity) arguments and chain-level ceilings ----------
dep_keys = {(r['id'], r['i'], r['arg_path']) for r in rows}
h0_keys = {(x['id'], 0, x['param']) for x in h0}
def other_args(r, s):
    return [p for p, v in leaves(s['args']) if (r['id'], s['i'], p) not in dep_keys and (r['id'], s['i'], p) not in h0_keys]
other_steps = 0; ok_steps = 0; other_leaf_n = 0
for r in runs.values():
    for s in r['steps']:
        if s['status'] != 'ok': continue
        ok_steps += 1
        oth = other_args(r, s)
        if oth: other_steps += 1; other_leaf_n += len(oth)
print('reconstructed steps', ok_steps, 'with >=1 arg that is neither a copy of prior answer nor a question entity (semantic/literal slot):', other_steps, 'leaves', other_leaf_n)
derivable_step = {k for k, v in step_rows.items() if all(derivable(x) for x in v)}
h0_ids = {x['id'] for x in h0}
qsum = C(); chain_complete = []
for r in runs.values():
    st = r['steps']
    if not st or any(s['status'] != 'ok' for s in st): qsum['not_fully_reconstructed'] += 1; continue
    h = r['id'] in h0_ids
    deps = all(((r['id'], i) in derivable_step) for i in range(1, len(st)))
    no_other = all(not other_args(r, s) for s in st)
    qsum['full'] += 1
    qsum['hop0_entity_in_question'] += h
    qsum['dependents_T-v1_derivable'] += deps
    qsum['both'] += (h and deps)
    qsum['both_and_no_semantic_literals'] += (h and deps and no_other)
    if h and deps and no_other: chain_complete.append(len(st))
print('chain-level (fully reconstructed queries):', dict(qsum))
print('chain-complete query hop counts:', dict(C(chain_complete)))
json.dump({'qsum': dict(qsum), 'chain_complete_n': dict(C(chain_complete)), 'other_steps': other_steps, 'ok_steps': ok_steps,
           'dependent_steps': len(step_rows), 'derivable_steps': len(derivable_step)}, open(sys.argv[3] + '/chain_level.json', 'w'), indent=1)
