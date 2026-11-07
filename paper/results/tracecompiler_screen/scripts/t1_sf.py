"""Template support and argument provenance for T1's only recurrent same-turn read-only pair:
search_flights, search_flights at the first tool-issuing turn. Parse only."""
import sys, collections, json, ast, hashlib
sys.path.insert(0, ".")
import t1_load as L
import t1_census as C

CACHE = L.CACHE_OPS | L.NON_TOOL


def kw(plan):
    out = []
    for node in ast.walk(ast.parse(plan)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id not in CACHE:
            k = {}
            for a in node.keywords:
                try:
                    k[a.arg] = ast.literal_eval(a.value)
                except Exception:
                    k[a.arg] = "<expr>"
            out.append((node.func.id, k))
    return out


def flat(v):
    if isinstance(v, (list, tuple)):
        for x in v:
            yield from flat(x)
    else:
        yield v


d = L.load()
tmpl = set()
n = 0
cats = collections.Counter()
turn_idx = collections.Counter()
for key, rows in d.items():
    utts = []
    done = False
    tparts = []
    for r in rows:
        tparts.append(r["Plan"] if isinstance(r["Plan"], str) else "")
    th = (key[0], hashlib.sha1("\n".join(tparts).encode()).hexdigest()[:12])
    for r in rows:
        role = r["Template"].split(":", 1)[0].strip()
        if role != "user":
            continue
        utts.append(r["Filled_Template"].split(":", 1)[1].strip().lower())
        plan = r["Filled_Plan"]
        if not isinstance(plan, str) or plan == "nan":
            continue
        cs = kw(plan)
        if not cs:
            continue
        if done:
            break
        done = True
        if len(cs) >= 2 and cs[0][0] == "search_flights" and cs[1][0] == "search_flights":
            n += 1
            tmpl.add(th)
            turn_idx[len(utts)] += 1
            cur = utts[-1]
            allu = " ".join(utts)
            for name, k in cs[:2]:
                for a, v in k.items():
                    for x in flat(v):
                        sx = str(x).lower()
                        if x == "<expr>":
                            cat = "expr"
                        elif sx in cur:
                            cat = "verbatim_current_turn"
                        elif sx in allu:
                            cat = "verbatim_earlier_turn"
                        else:
                            cat = "not_verbatim"
                        cats[cat] += 1
        break
print("dialogues", n, "templates", len(tmpl), "turn index", dict(turn_idx))
print(dict(cats))
json.dump({"dialogues": n, "templates": len(tmpl), "user_turn_index": dict(turn_idx), "arg_provenance": dict(cats)}, open(sys.argv[1], "w"), indent=1)
