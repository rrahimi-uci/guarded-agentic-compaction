import json, re, collections, sys
sys.path.insert(0, ".")
import hermes_census as H

out = {}
for f in ["func-calling-singleturn.json", "func-calling.json", "glaive-function-calling-5k.json"]:
    d = json.load(open(H.ROOT + f))
    first = []
    calls_in_first_turn = collections.Counter()
    for ex in d:
        conv = ex["conversations"]
        names = []
        for c in conv:
            if c["from"] in ("gpt", "assistant"):
                for m in H.TC.finditer(c["value"]):
                    try:
                        names.append(json.loads(m.group(1)).get("name"))
                    except Exception:
                        names.append("<unparsed>")
                break
        first.append(tuple(names))
        calls_in_first_turn[len(names)] += 1
    r = {"n": len(d), "calls_in_first_assistant_turn": dict(sorted(calls_in_first_turn.items()))}
    for k in (1, 2):
        c = collections.Counter(o[:k] for o in first if len(o) >= k)
        n = sum(c.values())
        r[f"entry_open{k}"] = dict(n=n, distinct=len(c), ge5=sum(v >= 5 for v in c.values()),
                                   ge30=sum(v >= 30 for v in c.values()), ge92=sum(v >= 92 for v in c.values()),
                                   top=[(list(o), v) for o, v in c.most_common(4)],
                                   read_share=round(sum(v for o, v in c.items() if all(H.is_read(t) for t in o)) / n, 3) if n else None)
    out[f] = r
    print(f, json.dumps(r)[:1500])
json.dump(out, open(sys.argv[1], "w"), indent=1)
a = json.load(open(H.ROOT + "func-calling.json"))
b = json.load(open(H.ROOT + "func-calling-singleturn.json"))
print("ids equal", [x["id"] for x in a] == [x["id"] for x in b])
ex = [e for e in a if any(c["from"] == "tool" for c in e["conversations"])][0]
print([(c["from"], c["value"][:150]) for c in ex["conversations"]])
