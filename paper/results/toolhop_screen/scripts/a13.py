import json, sys, collections
C = collections.Counter
rows = json.load(open(sys.argv[1]))['rows']
def shape(o):
    if isinstance(o, str): return 'str'
    if isinstance(o, dict): return 'dict:' + ','.join(sorted(o))[:60]
    if isinstance(o, list): return 'list'
    return 'scalar'
for name in ('extract_first_name', 'extract_last_name', 'genealogy_lookup', 'family_relationship_finder'):
    seen = {}
    for r in rows:
        if r['tool_prev'] == name and r['prev_ok'] and r['prev_output'] is not None:
            seen[(r['id'], r['i'])] = shape(r['prev_output'])
    c = C(seen.values())
    print(name, 'steps', len(seen), 'distinct output shapes', len(c), c.most_common(5))
