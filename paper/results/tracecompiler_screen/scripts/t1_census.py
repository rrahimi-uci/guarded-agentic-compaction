"""Recurrence census over T1 (provider-free; parses plan text only)."""
import collections, hashlib, json, sys, statistics
sys.path.insert(0, ".")
import t1_load as L

CACHE = L.CACHE_OPS | L.NON_TOOL
READ_TOOLS = {"search_hotels", "search_flights", "search_attractions", "search_restaurants", "search_nearest",
              "filter_hotels", "filter_flights", "filter_attractions", "filter_restaurants", "sort_results", "adjust_date"}


def tool_calls(plan):
    return [n for n in L.calls_in(plan) if n not in CACHE]


def census(keys_filter=None):
    d = L.load()
    recs = []
    for key, rows in d.items():
        domain, split, fname, did = key
        if keys_filter and not keys_filter(key):
            continue
        seq = []  # (user_turn_index, tool)
        ut = 0
        first_user_calls = None
        tmpl_parts = []
        for r in rows:
            role = r["Template"].split(":", 1)[0].strip()
            plan = r["Filled_Plan"]
            if role == "user":
                ut += 1
                cs = tool_calls(plan)
                if ut == 1:
                    first_user_calls = cs
                for c in cs:
                    seq.append((ut, c))
            tmpl_parts.append(r["Plan"] if isinstance(r["Plan"], str) else "")
        tmpl = hashlib.sha1("\n".join(tmpl_parts).encode()).hexdigest()[:12]
        recs.append(dict(key=key, domain=domain, split=split, seq=[c for _, c in seq],
                         first_call_user_turn=(seq[0][0] if seq else None),
                         first_user_calls=first_user_calls or [], template=(domain, tmpl), n_user=ut))
    return recs


def openings(recs, k):
    c = collections.Counter(tuple(r["seq"][:k]) for r in recs if len(r["seq"]) >= k)
    return c


def summarize(recs, label):
    out = {"label": label, "dialogues": len(recs),
           "templates": len({r["template"] for r in recs})}
    out["with_no_tool_call"] = sum(1 for r in recs if not r["seq"])
    out["first_call_at_first_user_turn"] = sum(1 for r in recs if r["first_call_user_turn"] == 1)
    out["first_call_user_turn_dist"] = dict(sorted(collections.Counter(r["first_call_user_turn"] for r in recs).items(), key=lambda kv: (kv[0] is None, kv[0])))
    out["calls_per_dialogue"] = dict(median=statistics.median(len(r["seq"]) for r in recs),
                                      mean=round(statistics.mean(len(r["seq"]) for r in recs), 2),
                                      max=max(len(r["seq"]) for r in recs))
    out["read_only_tool_share"] = None
    tools = collections.Counter(c for r in recs for c in r["seq"])
    out["tool_counts"] = dict(tools.most_common())
    out["all_tools_read_only"] = all(t in READ_TOOLS for t in tools)
    for k in (1, 2, 3):
        c = openings(recs, k)
        n = sum(c.values())
        # support in dialogues and in distinct templates
        tmpl_support = collections.defaultdict(set)
        for r in recs:
            if len(r["seq"]) >= k:
                tmpl_support[tuple(r["seq"][:k])].add(r["template"])
        sup = lambda m: sum(1 for v in c.values() if v >= m)
        tsup = lambda m: sum(1 for v in tmpl_support.values() if len(v) >= m)
        out[f"open{k}"] = dict(
            n_with_k_calls=n, distinct=len(c),
            support_dialogues_ge5=sup(5), ge30=sup(30), ge92=sup(92),
            support_templates_ge5=tsup(5), tge30=tsup(30), tge92=tsup(92),
            top=[(list(o), v, len(tmpl_support[o])) for o, v in c.most_common(8)],
            top1_share=round(c.most_common(1)[0][1] / n, 4) if n else None,
            read_only_share=round(sum(v for o, v in c.items() if all(t in READ_TOOLS for t in o)) / n, 4) if n else None)
    return out


if __name__ == "__main__":
    recs = census()
    res = {"all": summarize(recs, "all 13500"),
           "train": summarize([r for r in recs if r["split"] == "train"], "train 3375"),
           "test": summarize([r for r in recs if r["split"] == "test"], "test 9000")}
    json.dump(res, open(sys.argv[1], "w"), indent=1, default=str)
    for k, v in res.items():
        print(k, json.dumps(v, default=str)[:3500])
