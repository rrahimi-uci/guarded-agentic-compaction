import os, json, sys
B = "/Users/rezarahimi/Documents/GitHub/personal/guarded-agentic-compaction/benchmarks/.cache/tracecompiler_screen/appworld_out/x/"
rows = []
for r in sorted(os.listdir(B)):
    d = B + r + "/evaluations/"
    for f in os.listdir(d) if os.path.isdir(d) else []:
        if f.endswith(".json"):
            j = json.load(open(d + f))
            ind = j["individual"]
            s = sum(1 for v in ind.values() if v["success"])
            rows.append((r, len(ind), s, round(100 * s / len(ind), 1), j["aggregate"]))
for x in rows:
    print(x)
nrm = [x for x in rows if x[0].endswith("test_normal")]
print("test_normal runs", len(nrm), "min/median/max TGC", min(x[3] for x in nrm), sorted(x[3] for x in nrm)[len(nrm)//2], max(x[3] for x in nrm))
json.dump(rows, open(sys.argv[1], "w"))
