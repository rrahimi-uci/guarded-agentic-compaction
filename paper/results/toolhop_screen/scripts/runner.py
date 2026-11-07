"""Sandboxed (sandbox-exec: no network, no writes) reconstruction of ToolHop gold calls.

Reads the dataset JSON, AST-screens each tool function (import allowlist, forbidden
names), executes screened functions with candidate kwargs, and prints one JSON line
per query to stdout. Candidate pools are built from schema enums, string literals in
the function source, and the sub-task answers; success = tool output contains the
sub-task answer and is not an error object.
"""
import ast, contextlib, io, itertools, json, re, signal, sys, time

ALLOWED_IMPORTS = {"datetime", "re", "math", "json", "string", "collections", "typing",
                   "itertools", "statistics", "calendar", "functools", "decimal",
                   "fractions", "unicodedata", "pytz", "dateutil", "time", "random",
                   "operator", "copy", "textwrap", "enum", "dataclasses", "zoneinfo",
                   "difflib", "numbers", "bisect", "heapq", "hashlib", "base64",
                   "binascii", "urllib.parse", "html", "locale"}
FORBIDDEN_NAMES = {"open", "exec", "eval", "compile", "__import__", "os", "sys",
                   "subprocess", "socket", "shutil", "breakpoint", "importlib",
                   "requests", "urllib", "pathlib", "ctypes", "pickle"}


class TO(BaseException):
    pass


def _alarm(sig, frm):
    raise TO()


signal.signal(signal.SIGALRM, _alarm)


def screen(code):
    try:
        tree = ast.parse(code)
    except Exception as e:
        return False, "syntax", [], tree if False else None
    lits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] not in {m.split(".")[0] for m in ALLOWED_IMPORTS}:
                    return False, "import:" + a.name, [], tree
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] not in {m.split(".")[0] for m in ALLOWED_IMPORTS}:
                return False, "import:" + str(node.module), [], tree
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            return False, "name:" + node.id, [], tree
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            return False, "dunder:" + node.attr, [], tree
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            lits.append(node.value)
    return True, "", lits, tree


def doc_strings(tree):
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.Module, ast.AsyncFunctionDef)):
            d = ast.get_docstring(node, clean=False)
            if d:
                out.add(d)
    return out


def norm(s):
    return str(s).strip().lower().removesuffix(".0").replace(",", "")


def to_str(o):
    if isinstance(o, str):
        return o
    try:
        return json.dumps(o, ensure_ascii=False, default=str)
    except Exception:
        return str(o)


def is_error(o):
    if isinstance(o, dict) and any(k in o for k in ("error", "Error")):
        return True
    if isinstance(o, str) and re.match(r"\s*(error|an error|invalid|unknown)", o, re.I):
        return True
    return False


def contains(out, ans):
    a = norm(ans)
    t = norm(to_str(out))
    if not a:
        return False
    if re.fullmatch(r"[\w.\-: ]{1,6}", a):
        return re.search(r"(?<![\w.])" + re.escape(a) + r"(?![\w])", t) is not None
    return a in t


def jsonable(o, depth=0):
    if depth > 6:
        return str(o)[:200]
    if isinstance(o, (str, int, float, bool)) or o is None:
        return o if not isinstance(o, str) else o[:2000]
    if isinstance(o, dict):
        return {str(k): jsonable(v, depth + 1) for k, v in list(o.items())[:60]}
    if isinstance(o, (list, tuple, set)):
        return [jsonable(v, depth + 1) for v in list(o)[:60]]
    return str(o)[:500]


def call(fn, kwargs, secs=0.3):
    buf = io.StringIO()
    signal.setitimer(signal.ITIMER_REAL, secs, 0.05)
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            return True, fn(**kwargs)
    except TO:
        return False, "timeout"
    except BaseException as e:
        return False, "exc:" + type(e).__name__
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def build_fn(code, name):
    ns = {"__name__": "toolmod"}
    buf = io.StringIO()
    signal.setitimer(signal.ITIMER_REAL, 2.0, 0.05)
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            exec(compile(code, "<tool>", "exec"), ns)
    except TO:
        return None, "build_timeout"
    except BaseException as e:
        # module-level example usage may fail; function may still be defined
        if name not in ns:
            return None, "build_exc:" + type(e).__name__
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    fn = ns.get(name)
    if not callable(fn):
        return None, "no_def"
    return fn, ""


def ptype(p):
    t = p.get("type", "string") if isinstance(p, dict) else "string"
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), "string")
    return t


def enum_of(p):
    if not isinstance(p, dict):
        return None
    if "enum" in p:
        return list(p["enum"])
    it = p.get("items")
    if isinstance(it, dict) and "enum" in it:
        return list(it["enum"])
    return None


def pools(code_lits, answers_before, ans_prev, subq):
    seen, strs = set(), []

    def add(s):
        if isinstance(s, str) and 1 <= len(s) <= 80 and s not in seen:
            seen.add(s)
            strs.append(s)
    # priority: previous answer, then literals that occur in the sub-question
    if ans_prev is not None:
        add(ans_prev)
    sq = subq.lower()
    for s in sorted(set(code_lits), key=lambda x: -len(x)):
        if len(s) >= 2 and s.lower() in sq:
            add(s)
    for a in answers_before[::-1]:
        add(a)
    for s in code_lits:
        add(s)
    return strs[:70]


def reconstruct(fn, tool, code_lits, answers_before, ans_prev, ans, subq, budget=1200):
    params = tool.get("parameters", {}).get("properties", {}) or {}
    req = [r for r in tool.get("parameters", {}).get("required", []) if r in params]
    opt = [k for k in params if k not in req]
    P = pools(code_lits, answers_before, ans_prev, subq)
    nums = []
    for a in answers_before + ([ans_prev] if ans_prev else []):
        try:
            nums.append(int(float(a)))
        except Exception:
            pass
    for s in code_lits:
        if re.fullmatch(r"\d{1,4}", s):
            nums.append(int(s))
    nums = list(dict.fromkeys(nums + [1, 2, 3, 5, 10]))[:12]

    def cands(k, wide=True):
        p = params[k]
        t = ptype(p)
        en = enum_of(p)
        if t == "string":
            return (list(en) if en and "items" not in p else P[:(40 if wide else 12)]) or [""]
        if t in ("integer", "number"):
            return nums
        if t == "boolean":
            return [True, False]
        if t == "array":
            if en:
                return [[e] for e in en[:8]] + [en[:2]]
            return [[s] for s in P[:(15 if wide else 8)]] + [[]]
        if t == "object":
            return [{}]
        return P[:10]

    tries = 0
    successes = []
    first = None

    t0 = time.time()

    def attempt(kw):
        nonlocal tries, first
        tries += 1
        if time.time() - t0 > 12:
            tries = 10**9
            return False
        okc, out = call(fn, kw)
        if okc and not is_error(out) and contains(out, ans):
            successes.append(kw)
            if first is None:
                first = (kw, out)
            return True
        return False
    # phase 1: required only
    lists = [cands(k) for k in req]
    for combo in itertools.product(*lists):
        if tries >= budget // 2 or len(successes) >= 30:
            break
        attempt(dict(zip(req, combo)))
    # phase 2: add one/two optional params to the best required combos
    if first is None and opt and tries < budget:
        base_lists = [cands(k, wide=False) for k in req]
        base_combos = list(itertools.islice(itertools.product(*base_lists), 12))
        optlists = {k: cands(k, wide=False) for k in opt if ptype(params[k]) in ("string", "array", "boolean", "integer", "number", "object")}
        for bc in base_combos:
            for k1 in optlists:
                for v1 in optlists[k1]:
                    if tries >= budget or len(successes) >= 30:
                        break
                    attempt({**dict(zip(req, bc)), k1: v1})
        if first is None:
            ks = list(optlists)
            for bc in base_combos[:4]:
                for k1, k2 in itertools.combinations(ks, 2):
                    for v1 in optlists[k1][:6]:
                        for v2 in optlists[k2][:6]:
                            if tries >= budget:
                                break
                            attempt({**dict(zip(req, bc)), k1: v1, k2: v2})
    return first, len(successes), tries


def main():
    data = json.load(open(sys.argv[1]))
    lo, hi = int(sys.argv[2]), int(sys.argv[3])
    skip = {int(x) for x in sys.argv[4].split(",") if x} if len(sys.argv) > 4 else set()
    for q in data[lo:hi]:
        subs = list(q["sub_task"].items())
        tools = list(q["tools"].values())
        funcs = q["functions"]
        answers = [a for _, a in subs]
        print(json.dumps({"id": q["id"], "n": len(subs)}), flush=True)
        for i, ((sq, ans), tool) in enumerate(zip(subs, tools)):
            name = tool["name"]
            st = {"i": i, "name": name, "subq": sq, "answer": ans}
            if i in skip:
                st["status"] = "hang"
                print(json.dumps({"id": q["id"], "step": st}, ensure_ascii=False), flush=True)
                continue
            print(json.dumps({"id": q["id"], "start": i}), flush=True)
            code = next((f for f in funcs if re.search(r"def\s+" + re.escape(name) + r"\s*\(", f)), None)
            if code is None:
                st["status"] = "no_code"
            else:
                ok, why, lits, tree = screen(code)
                if not ok:
                    st["status"] = "unsafe:" + why
                else:
                    docs = doc_strings(tree)
                    lits = [s for s in lits if s not in docs]
                    fn, why = build_fn(code, name)
                    if fn is None:
                        st["status"] = why
                    else:
                        first, nsucc, tries = reconstruct(fn, tool, lits, answers[:i], answers[i - 1] if i else None, ans, sq)
                        st["tries"] = tries
                        st["n_success"] = nsucc
                        if first is None:
                            st["status"] = "unreconstructed"
                        else:
                            st["status"] = "ok"
                            st["args"] = jsonable(first[0])
                            st["output"] = jsonable(first[1])
                            st["required"] = tool.get("parameters", {}).get("required", [])
                            st["n_literals"] = len(lits)
            print(json.dumps({"id": q["id"], "step": st}, ensure_ascii=False), flush=True)


main()
