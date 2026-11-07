"""Where do T1's first-turn tool-call arguments come from? Parse only (ast.parse), never execute."""
import ast, collections, json, sys
sys.path.insert(0, ".")
import t1_load as L

CACHE = L.CACHE_OPS | L.NON_TOOL


def kwcalls(plan):
    try:
        tree = ast.parse(plan)
    except Exception:
        return None
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id not in CACHE:
            kws = {}
            for kw in node.keywords:
                try:
                    kws[kw.arg] = ast.literal_eval(kw.value)
                except Exception:
                    kws[kw.arg] = "<expr:%s>" % ast.unparse(kw.value)
            out.append((node.func.id, kws))
    return sorted(out, key=lambda t: 0)


def flat(v):
    if isinstance(v, (list, tuple)):
        for x in v:
            yield from flat(x)
    else:
        yield v


d = L.load()
stats = collections.Counter()
per_tool = collections.defaultdict(collections.Counter)
parse_fail = 0
n_dialogs_with_entry_call = 0
slot_stats = collections.Counter()
for key, rows in d.items():
    ut = 0
    for r in rows:
        role = r["Template"].split(":", 1)[0].strip()
        if role != "user":
            continue
        ut += 1
        if ut > 1:
            break
        plan = r["Filled_Plan"]
        if not isinstance(plan, str) or plan == "nan":
            continue
        cs = kwcalls(plan)
        if cs is None:
            parse_fail += 1
            continue
        if not cs:
            continue
        n_dialogs_with_entry_call += 1
        utt = r["Filled_Template"].split(":", 1)[1].strip().lower()
        for name, kws in cs:
            for a, v in kws.items():
                for x in flat(v):
                    sx = str(x).lower()
                    if isinstance(x, str) and x.startswith("<expr:"):
                        cat = "expr_or_cache"
                    elif sx in utt:
                        cat = "verbatim_in_first_user_utterance"
                    elif isinstance(x, bool):
                        cat = "boolean_flag_semantic"
                    else:
                        cat = "not_verbatim"
                    stats[cat] += 1
                    per_tool[name][cat] += 1
                    slot_stats[(name, a, cat)] += 1
print("entry-call dialogues", n_dialogs_with_entry_call, "parse_fail", parse_fail)
print(dict(stats))
for t, c in per_tool.items():
    print(t, dict(c))
nv = [(k, v) for k, v in slot_stats.items() if k[2] != "verbatim_in_first_user_utterance"]
print(sorted(nv, key=lambda kv: -kv[1])[:15])
json.dump({"entry_call_dialogues": n_dialogs_with_entry_call, "arg_value_provenance": dict(stats),
           "by_tool": {t: dict(c) for t, c in per_tool.items()}, "parse_fail": parse_fail},
          open(sys.argv[1], "w"), indent=1)
