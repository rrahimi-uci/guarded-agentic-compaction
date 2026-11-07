import os, json, collections, sys
B = "/Users/rezarahimi/Documents/GitHub/personal/guarded-agentic-compaction/benchmarks/.cache/tracecompiler_screen/appworld_out/x/"


def load_calls(p):
    out = []
    for line in open(p):
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        out.append((o.get("method", "").lower(), o.get("url", "")))
    return out


def opening(calls, drop_docs, k):
    seq = [(m, u) for m, u in calls if not (drop_docs and u.startswith("/api_docs"))]
    return tuple(f"{m} {u}" for m, u in seq[:k]), seq


def ro_prefix_len(seq):
    n = 0
    for m, u in seq:
        if m == "get":
            n += 1
        else:
            break
    return n


def summarize(items, label, drop_docs):
    res = {"label": label, "trajectories": len(items), "drop_api_docs": drop_docs}
    for k in (1, 2, 3):
        c = collections.Counter()
        scen = collections.defaultdict(set)
        ro = 0
        n = 0
        for task, calls in items:
            o, seq = opening(calls, drop_docs, k)
            if len(o) < k:
                continue
            n += 1
            c[o] += 1
            scen[o].add(task.split("_")[0])
            if ro_prefix_len(seq) >= k:
                ro += 1
        sup = lambda m: sum(1 for v in c.values() if v >= m)
        res[f"open{k}"] = dict(n_with_k=n, distinct=len(c), ge5=sup(5), ge30=sup(30), ge92=sup(92),
                               read_only_share=round(ro / n, 4) if n else None,
                               top=[(list(o), v, len(scen[o])) for o, v in c.most_common(5)],
                               scen_ge5=sum(1 for o in c if len(scen[o]) >= 5), scen_ge30=sum(1 for o in c if len(scen[o]) >= 30),
                               scen_ge92=sum(1 for o in c if len(scen[o]) >= 92))
    return res


def main(outp):
    runs = sorted(os.listdir(B))
    per_run = {}
    for r in runs:
        d = B + r + "/tasks/"
        its = []
        for t in sorted(os.listdir(d)):
            p = d + t + "/logs/api_calls.jsonl"
            if os.path.exists(p):
                its.append((t, load_calls(p)))
        per_run[r] = its
    out = {"runs": len(runs), "trajectories": sum(len(v) for v in per_run.values())}
    pooled = [it for v in per_run.values() for it in v]
    for drop in (False, True):
        out[f"pooled_drop{drop}"] = summarize(pooled, "pooled 28 runs", drop)
        for fam in ("react", "full_code_refl", "ipfuncall", "plan_exec"):
            its = [it for r, v in per_run.items() if r.startswith(fam + "_") for it in v]
            out[f"{fam}_drop{drop}"] = summarize(its, fam, drop)
        # test_normal ReAct gpt4o: the TraceCompiler-like 168 trajectories
        out[f"react_gpt4o_normal_drop{drop}"] = summarize(per_run["react_gpt4o_test_normal"], "react_gpt4o_test_normal (168)", drop)
    json.dump(out, open(outp, "w"), indent=1)
    for k, v in out.items():
        if isinstance(v, dict):
            print(k, json.dumps({kk: vv for kk, vv in v.items() if kk != "open3"})[:1500])


main(sys.argv[1])
