"""Recurrence census over Hermes-Function-Calling-v1 configs. Parses JSON only."""
import collections, json, re, sys

ROOT = "/Users/rezarahimi/Documents/GitHub/personal/guarded-agentic-compaction/benchmarks/.cache/tracecompiler_screen/hermes/"
TC = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)
READ_PREFIX = ("get_", "list_", "search_", "find_", "fetch_", "check_", "retrieve_", "lookup_", "query_", "read_", "view_", "show_", "calculate_", "analyze_", "compare_", "validate_", "verify_", "track_", "estimate_", "detect_", "extract_")


def is_read(name):
    return name.startswith(READ_PREFIX)


def run(fname):
    d = json.load(open(ROOT + fname))
    res = dict(file=fname, n=len(d))
    seqs = []
    has_resp = 0
    multi_turn = 0
    schema_sigs = collections.Counter()
    tools_per_ex = []
    for ex in d:
        conv = ex["conversations"]
        roles = [c["from"] for c in conv]
        calls = []
        for c in conv:
            if c["from"] in ("gpt", "assistant"):
                for m in TC.finditer(c["value"]):
                    try:
                        calls.append(json.loads(m.group(1)))
                    except Exception:
                        try:
                            calls.append(json.loads(m.group(1).replace("'", '"')))
                        except Exception:
                            calls.append({"name": "<unparsed>", "arguments": {}})
        names = [str(c.get("name")) for c in calls]
        seqs.append(names)
        if "tool" in roles:
            has_resp += 1
        if roles.count("human") > 1:
            multi_turn += 1
        # tool vocabulary
        sysmsg = conv[0]["value"] if conv and conv[0]["from"] == "system" else ""
        tool_names = tuple(sorted(re.findall(r'"name": "([^"]+)"', sysmsg)))
        schema_sigs[tool_names] += 1
        tools_per_ex.append(len(tool_names))
    res["with_tool_response_turn"] = has_resp
    res["multi_human_turn"] = multi_turn
    res["with_>=1_call"] = sum(1 for s in seqs if s)
    res["with_>=2_calls"] = sum(1 for s in seqs if len(s) >= 2)
    res["calls_per_example"] = dict(mean=round(sum(map(len, seqs)) / len(seqs), 2), max=max(map(len, seqs)))
    res["distinct_tool_vocabularies"] = len(schema_sigs)
    res["distinct_tool_names"] = len({n for s in seqs for n in s})
    for k in (1, 2, 3):
        c = collections.Counter(tuple(s[:k]) for s in seqs if len(s) >= k)
        n = sum(c.values())
        sup = lambda m: sum(1 for v in c.values() if v >= m)
        res[f"open{k}"] = dict(n=n, distinct=len(c), ge5=sup(5), ge30=sup(30), ge92=sup(92),
                               top=[(list(o), v) for o, v in c.most_common(5)],
                               read_share=round(sum(v for o, v in c.items() if all(is_read(t) for t in o)) / n, 4) if n else None,
                               top1_share=round(c.most_common(1)[0][1] / n, 4) if n else None)
    return res


if __name__ == "__main__":
    out = {}
    for f in ["func-calling-singleturn.json", "func-calling.json", "glaive-function-calling-5k.json"]:
        out[f] = run(f)
        print(json.dumps(out[f], default=str)[:2500])
    json.dump(out, open(sys.argv[1], "w"), indent=1)
