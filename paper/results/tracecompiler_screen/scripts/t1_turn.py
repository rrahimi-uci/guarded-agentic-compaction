import sys, collections, json
sys.path.insert(0, ".")
import t1_load as L
import t1_census as C

d = L.load()
first_turn_calls = []
allturn = []  # per dialogue: list of per-turn call tuples
for key, rows in d.items():
    turns = []
    for r in rows:
        role = r["Template"].split(":", 1)[0].strip()
        if role == "user":
            cs = tuple(C.tool_calls(r["Filled_Plan"]))
            turns.append(cs)
    nz = [t for t in turns if t]
    first_turn_calls.append((key, nz[0] if nz else ()))
    allturn.append((key, turns))
c = collections.Counter(len(t) for _, t in first_turn_calls)
print("calls in first tool-issuing turn:", dict(sorted(c.items())))
ge2 = [(k, t) for k, t in first_turn_calls if len(t) >= 2]
print("dialogues whose first tool-issuing turn has >=2 calls:", len(ge2), "of", len(first_turn_calls))
oc = collections.Counter(t[:2] for _, t in ge2)
print("distinct 2-call same-turn openings", len(oc), "support>=5", sum(v >= 5 for v in oc.values()), ">=30", sum(v >= 30 for v in oc.values()), ">=92", sum(v >= 92 for v in oc.values()))
print(oc.most_common(8))
# fraction of ALL tool calls issued in a turn that contains >=2 calls (compactable block) and distinct same-turn blocks
blocks = collections.Counter()
tot_calls = 0
multi = 0
for key, turns in allturn:
    for t in turns:
        tot_calls += len(t)
        if len(t) >= 2:
            multi += len(t)
print("share of all tool calls in same-turn blocks of >=2:", round(multi / tot_calls, 3), tot_calls)
# how many turns have a dependent arg ("prior_results" or cache-derived)
res = {"first_tool_turn_calls_hist": dict(sorted(c.items())), "ge2_dialogues": len(ge2),
       "same_turn_open2": dict(distinct=len(oc), ge5=sum(v >= 5 for v in oc.values()), ge30=sum(v >= 30 for v in oc.values()), ge92=sum(v >= 92 for v in oc.values()), top=[(list(o), v) for o, v in oc.most_common(6)]),
       "share_calls_in_multicall_turns": round(multi / tot_calls, 3)}
json.dump(res, open(sys.argv[1], "w"), indent=1)
