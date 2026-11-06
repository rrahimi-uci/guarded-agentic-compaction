"""Publish structural common-entry evidence; encrypt all protected reference data."""
from collections import Counter
import json
import hashlib
import subprocess
from pathlib import Path

from adaptive_pilot import ROOT, LOCAL as CAMPAIGN, digest, write
from appworld_entry_preflight import BASE, CACHE, OUT, IMAGE
from appworld_entry_controls import CONTROL, PREFIXES
from export_appworld_viability import PACK


def summarize_references(seal, rows):
    ids = [r['task_id'] for r in rows]
    if len(ids) != len(set(ids)) or set(ids) != set(seal['tasks']):
        raise ValueError('exact fixed reference cohort required')
    if any(r.get('status') != 'completed' for r in rows):
        raise ValueError('unfinished reference inventory')
    family_tasks = {name: [] for name in PREFIXES}
    details = []
    for row in rows:
        calls = row['calls']
        core = [c for c in calls if not c['tool'].endswith('.login') and c['tool'] not in {'supervisor.show_profile', 'supervisor.show_account_passwords'}]
        for family, api in PREFIXES.items():
            first = core[:2]
            if len(first) == 2 and all(c['tool'] == api and set(c['arguments']) == {'access_token', 'page_index'} and c['arguments']['page_index'] == i for i, c in enumerate(first)):
                family_tasks[family].append(row['task_id'])
        details.append({'task_id': row['task_id'], 'reference_success': row['reference_success'],
            'api_calls': len(calls), 'after_removing_common_entry_calls': len(core), 'tests': row['tests'], 'passed_tests': row['passed_tests']})
    counts = [r['api_calls'] for r in details]
    return {'tasks': details, 'reference_successes': sum(r['reference_success'] for r in rows),
        'total_reference_api_calls': sum(counts), 'min_reference_api_calls': min(counts), 'max_reference_api_calls': max(counts),
        'references_above_old_24_request_limit': sum(n > 24 for n in counts),
        'references_above_old_48_api_limit': sum(n > 48 for n in counts),
        'posthoc_reference_prefix_hypotheses': family_tasks,
        'interpretation': 'Reference API counts are not a lower bound on task difficulty or model requests. Prefix hypotheses were identified from exposed reference solutions, not mined from model traces; no automatic compiler success is asserted.'}


def build():
    if (OUT / 'operational_evidence.bundle').exists():
        raise ValueError('retain published evidence; version any amendment')
    reference_seal = json.loads((CACHE / 'seal.json').read_text())
    control_seal = json.loads((CONTROL / 'seal.json').read_text())
    for base, seal in ((BASE, json.loads((BASE / 'seal.json').read_text())), (CACHE, reference_seal), (CONTROL, control_seal)):
        for rel, sha in seal['source_hashes'].items():
            if digest(base / 'sealed_sources' / rel) != sha:
                raise ValueError('historical sealed source drift')
            if base != BASE and digest(ROOT / rel) != sha:
                raise ValueError('current preflight source drift')
    rows = [json.loads((CACHE / 'references' / (t+'.json')).read_text()) for t in reference_seal['tasks']]
    summary = summarize_references(reference_seal, rows)
    controls = []
    for task in control_seal['tasks']:
        for mode in control_seal['modes']:
            raw = json.loads((CONTROL / 'results' / task / (mode+'.json')).read_text())
            if raw['status'] not in {'completed', 'failed'}:
                raise ValueError('unfinished common-entry control')
            controls.append({'task_id': task, 'mode': mode, 'status': raw['status'], 'passed': raw['passed'],
                'setup_calls': len(raw.get('setup', [])), 'setup_apps': raw.get('setup_apps', []),
                'control_calls': len(raw.get('calls', [])), 'official_success': raw.get('success'),
                'tests': raw.get('tests'), 'passed_tests': raw.get('passed_tests'),
                'saved_state_unchanged': raw.get('saved_state_unchanged'),
                'entry_setup_sha256': hashlib.sha256(json.dumps(raw.get('setup'), sort_keys=True).encode()).hexdigest(),
                'entry_saved_state_sha256': hashlib.sha256(json.dumps(raw.get('saved_state_before'), sort_keys=True).encode()).hexdigest()})
    old = [json.loads((BASE / 'references' / (t+'.json')).read_text()) for t in reference_seal['tasks']]
    ledger = json.loads((CAMPAIGN / 'ledger.json').read_text())
    new_requests = [r for r in ledger['requests'] if r['started_unix'] >= json.loads((BASE/'seal.json').read_text())['created_unix']]
    if new_requests:
        raise ValueError('unexpected campaign calls during provider-free preflight; reconcile before publication')
    parity = [{'task_id': task, 'identical_setup': len({r['entry_setup_sha256'] for r in controls if r['task_id'] == task}) == 1,
        'identical_saved_entry': len({r['entry_saved_state_sha256'] for r in controls if r['task_id'] == task}) == 1} for task in control_seal['tasks']]
    passed = all(r['passed'] for r in controls) and summary['reference_successes'] == len(rows) and all(r['identical_setup'] and r['identical_saved_entry'] for r in parity)
    report = {'schema': 'appworld-entry-preflight-report-v1',
        'decision': 'COMMON_ENTRY_VALIDATED_NO_CONFIRMATORY_GO' if passed else 'NO_GO_CONTROL_FAILURE',
        'reference_summary': summary, 'controls': controls, 'common_entry_parity': parity,
        'control_totals': {mode: {'scheduled': sum(r['mode'] == mode for r in controls),
            'passed': sum(r['mode'] == mode and r['passed'] for r in controls)} for mode in control_seal['modes']},
        'initial_instrumentation_attempt': {'scheduled': len(old), 'reference_successes': sum(r.get('reference_success') is True for r in old),
            'reason': 'Source-file hashing inside AppWorld.execute violated its sandbox. Hashing moved after execution; original failures retained. These are instrumentation failures, not benchmark outcomes.'},
        'effect_boundary': {'authentication': 'write barrier; identical explicit setup, never speculated',
            'library_probes': 'Only two pages, default query/filter/sort. Endpoint and retrieval/helper sources inspected; sampled saved DB files unchanged. Not a universal effect proof or authorization for all parameter combinations.',
            'catalog_changed': False, 'artifacts_emitted': 0, 'calibration_groups': 0, 'test_groups': 0},
        'budget': {'new_model_requests': len(new_requests), 'new_model_cost_usd': 0,
            'campaign_accounted_upper_usd': ledger['accounted_upper_usd'], 'remaining_cap_usd': ledger['cap_usd'] - ledger['accounted_upper_usd'],
            'ledger_sha256': digest(CAMPAIGN / 'ledger.json'), 'scope': 'Local compute and engineering are unpriced.'},
        'limitations': ['All tasks and references are previously exposed development material.',
            'A common authenticated entry changes the task contract and adds 11 setup API calls per control.',
            'Known-correct sequences validate execution/grading, not baseline competence or compilation.',
            'Reference prefix hypotheses are posthoc development observations, not model-discovered families.',
            'The comparator, actual automatic candidate, fresh calibration population and learned-gate experiment remain unexecuted.'],
        'export_source_sha256': digest(__file__)}
    OUT.mkdir(parents=True, exist_ok=True)
    for name, seal in [('reference_seal', reference_seal), ('entry_control_seal', control_seal)]:
        write(OUT / (name+'.json'), seal)
    subprocess.run(['docker', 'run', '--rm', '--network', 'none', '--read-only', '--cap-drop', 'ALL',
        '--security-opt', 'no-new-privileges', '--memory', '4g', '--tmpfs', '/work:rw,nosuid,size=2g,mode=1777',
        '-v', str(BASE)+':/input:ro', '-v', str(OUT)+':/output:rw', IMAGE, '-I', '-c', PACK], check=True, timeout=120)
    report['encrypted_evidence_sha256'] = digest(OUT / 'operational_evidence.bundle')
    report['bundle_verification'] = json.loads((OUT/'bundle_verification.json').read_text())
    report['protected_raw_files'] = [{'path': str(p.relative_to(BASE)), 'sha256': digest(p), 'bytes': p.stat().st_size}
        for p in sorted(BASE.rglob('*')) if p.is_file() and p.suffix not in {'.lock', '.tmp'}]
    write(OUT/'report.json', report)
    print(json.dumps({k: report[k] for k in ('decision', 'control_totals', 'budget')}))


if __name__ == '__main__':
    build()
