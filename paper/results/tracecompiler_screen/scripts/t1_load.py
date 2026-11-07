"""Load T1 (capitalone/T1) into per-dialogue ordered tool-call lists. Read-only parse; no execution of plan code."""
import csv, glob, json, os, re, sys, collections

ROOT = "/Users/rezarahimi/Documents/GitHub/personal/guarded-agentic-compaction/benchmarks/.cache/tracecompiler_screen/t1/"
CALL_RE = re.compile(r"(?:(\w+)\s*=\s*)?\b([A-Za-z_]\w*)\s*\(")
CACHE_OPS = {"save_to_cache", "get_results_from_cache"}
NON_TOOL = {"seek_information"}
KEYWORDS = {"if", "for", "while", "print", "len", "str", "int", "float", "sorted", "min", "max", "sum", "range", "list", "dict", "set", "isinstance"}


def calls_in(plan: str):
    out = []
    if not plan or plan == "nan":
        return out
    for line in plan.splitlines():
        for m in CALL_RE.finditer(line):
            name = m.group(2)
            if name in KEYWORDS:
                continue
            out.append(name)
    return out


def load():
    dialogs = {}
    for path in sorted(glob.glob(ROOT + "*/*/*.csv")):
        rel = os.path.relpath(path, ROOT).split(os.sep)
        if rel[0] == "ontology":
            continue
        domain, split = rel[0], rel[1]
        csv.field_size_limit(10**9)
        with open(path, newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            rows = list(r)
        by_id = collections.OrderedDict()
        for row in rows:
            by_id.setdefault(row["ID"], []).append(row)
        for did, rs in by_id.items():
            key = (domain, split, os.path.basename(path), did)
            dialogs[key] = rs
    return dialogs


if __name__ == "__main__":
    d = load()
    print(len(d))
