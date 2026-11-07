"""Static (AST only, no execution) audit of the 3,912 tool functions: imports, side-effect
constructs, and whether the functions embed the query's sub-task answers (hard-coded lookup)."""
import ast, json, sys, re, collections
C = collections.Counter
d = json.load(open(sys.argv[1]))
imports = C(); bad = C(); n = 0; parse_fail = 0
glob = 0; hard = 0; hard_retr = 0; retr = 0; comp_hard = 0; comp = 0
net = 0; fs = 0; mutate = 0
RETR = re.compile(r'(lookup|finder|retriev|info|search|query|identif|locator|fetch|get_|biograph|genealog|relationship|director|author|publication|histor)', re.I)
per_tool_flags = []
for q in d:
    answers = [a for a in q['sub_task'].values()]
    names = [t['name'] for t in q['tools'].values()]
    for i, name in enumerate(names):
        code = next((f for f in q['functions'] if re.search(r'def\s+' + re.escape(name) + r'\s*\(', f)), None)
        if code is None:
            continue
        n += 1
        try:
            tree = ast.parse(code)
        except Exception:
            parse_fail += 1
            continue
        lits = set(); flag = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names: imports[a.name.split('.')[0]] += 1
            elif isinstance(node, ast.ImportFrom):
                imports[(node.module or '').split('.')[0]] += 1
            elif isinstance(node, ast.Global):
                flag.add('global_stmt')
            elif isinstance(node, ast.Name) and node.id in ('open', 'exec', 'eval', 'compile', '__import__', 'input'):
                flag.add('builtin_' + node.id)
            elif isinstance(node, ast.Name) and node.id in ('os', 'sys', 'subprocess', 'socket', 'requests', 'urllib', 'shutil', 'pathlib', 'http'):
                flag.add('mod_' + node.id)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                lits.add(node.value)
        for f in flag: bad[f] += 1
        # hard-coded answer: sub-task answer for this step appears as a string literal inside the code
        ans = answers[i] if i < len(answers) else ''
        a_n = ans.strip().lower()
        has_ans = any(a_n and a_n in s.lower() for s in lits) if a_n else False
        is_r = bool(RETR.search(name))
        if is_r:
            retr += 1; hard_retr += has_ans
        else:
            comp += 1; comp_hard += has_ans
        per_tool_flags.append((q['id'], i, name, is_r, has_ans, sorted(flag)))
print('functions parsed', n, 'parse_fail', parse_fail)
print('imports', imports.most_common(25))
print('flags', dict(bad))
print('retrieval-named tools', retr, 'of which embed gold answer literal', hard_retr, round(hard_retr / max(retr, 1), 3))
print('compute-named tools', comp, 'embed gold answer literal', comp_hard, round(comp_hard / max(comp, 1), 3))
json.dump({'n': n, 'parse_fail': parse_fail, 'imports': dict(imports), 'flags': dict(bad), 'retr': retr, 'retr_hardcoded': hard_retr,
           'comp': comp, 'comp_hardcoded': comp_hard}, open(sys.argv[2], 'w'), indent=1)
