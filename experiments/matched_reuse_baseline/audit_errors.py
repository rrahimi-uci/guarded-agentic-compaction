"""Post-run source audit; preserves sealed endpoints, cohorts and provider data."""
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'paper/scripts'))
import recurrence_only_ablation as snapshot


def main():
    checkpoint=json.loads((OUT/'checkpoint.json').read_text())
    analysis=json.loads((OUT/'analysis.json').read_text())
    seal=json.loads((OUT/'seal.json').read_text())
    if hashlib.sha256((OUT/'checkpoint.json').read_bytes()).hexdigest()!=analysis['checkpoint_sha256']:
        raise ValueError('checkpoint drift')
    store,source=snapshot.load_store()
    feasibility=[]
    for group in ('pilot','primary'):
        for n in seal[group+'_numbers']:
            row=store[n]
            evidence=[row['title'],row['body'][:2400],*(c[:800] for c in row['comments'][:3])]
            lengths=[len(t.strip()) for t in evidence]
            feasibility.append({'group':group,'issue_number':n,'available_excerpt_lengths':lengths,
                                'minimum_20_character_excerpt_possible':max(lengths)>=20})
    impossible={r['issue_number'] for r in feasibility if not r['minimum_20_character_excerpt_possible']}
    if impossible != {377}:
        raise ValueError('unexpected feasibility audit; update interpretation from evidence')
    errors=[]
    for row in checkpoint['rows']:
        if row['status']=='completed' and row['correct']:
            continue
        n=row['issue_number']
        errors.append({'group':row['group'],'issue_number':n,'arm':row['arm'],'status':row['status'],
            'wrong_fields':[k for k in ('category_correct','issue_number_correct','evidence_label_correct',
                         'title_exact','state_exact','comment_count_exact','evidence_excerpt_exact')
                            if row.get('quality',{}).get(k) is False],
            'source_labels':list(store[n]['labels']),
            'answer_category':row.get('answer',{}).get('category'),
            'answer_evidence_label':row.get('answer',{}).get('evidence_label'),
            'excerpt_possible':n not in impossible,
            'failure_type':row.get('error',{}).get('error_type')})
    result={'schema':'matched-reuse-posthoc-source-audit/v1','provider_calls_executed':0,
        'primary_denominator_unchanged':120,'checkpoint_sha256':analysis['checkpoint_sha256'],
        'source':source,'excerpt_feasibility':feasibility,'error_episodes':errors,
        'impossible_excerpt_issue_numbers':sorted(impossible),
        'interpretation':'Post-hoc author source audit, not independent human adjudication or a new primary endpoint.'}
    (OUT/'error_audit.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    lines=['# Post-run source and error audit','',
        'This provider-free author audit preserves every original outcome and denominator. '
        'It is not independent human adjudication and does not revise the sealed study.', '',
        'The 20-character minimum excerpt is impossible for issue 377: its title has six characters, '
        'its body is empty, and it has no comments. It was selected by the frozen hash ranking, which '
        'did not screen excerpt feasibility. All three arms fail it: GAC at output-schema validation, '
        'baseline and adapted AWM at the source-excerpt check. The failed GAC output was not retained, '
        'so its exact invalid field cannot be reconstructed. Its observed usage and $1 reserve remain.', '',
        'This was the only issue failing this excerpt-length screen among all 126 pilot/primary issues. '
        'Passing this narrow screen does not prove every other aspect of task validity. No issue is replaced '
        'or removed from the primary analysis. Future studies should freeze a feasibility screen before selection.', '',
        'Each primary arm has three category/evidence-label failures involving the label `dataset bug`: '
        'the fixed task uses exact category labels and the grader expects `other`/`none`, whereas these '
        'answers use `bug`/`dataset bug`. The particular records differ by arm. These are strict contract '
        'errors, not demonstrated false real-world claims. Excerpt and title mismatches likewise retain '
        'the exact endpoint; this audit does not equate every mismatch with semantic hallucination.', '',
        '| Issue | Arm | Status | Incorrect fields |', '| --- | --- | --- | --- |']
    for e in errors:
        lines.append(f"| {e['issue_number']} | {e['arm']} | {e['status']} | {', '.join(e['wrong_fields']) or e['failure_type']} |")
    (OUT/'ERROR_AUDIT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'error_episodes':len(errors),'impossible_excerpt_issue_numbers':sorted(impossible),'provider_calls_executed':0}))


if __name__=='__main__':
    main()
