"""Post-selection source-validity audit; does not alter cohorts or paid execution.

This author audit is not independent human adjudication. Run after sealing; it
inspects public source only and preserves every selected record.
"""
import json
import sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'paper/scripts')]
import generalization_gate_study as study


def main():
    seal=json.loads((study.OUT/'seal.json').read_text())
    family_store=study.family.load_store()[0]
    issue_store=study.issue.load_store()[0]
    findings=[]
    rows=[]
    for name,cohort in seal['cohorts'].items():
        for group in ('pilot','primary'):
            for number in cohort[group]:
                source=(issue_store if name=='issue_type' else family_store)[number]
                defects=[]
                if name=='issue_type':
                    title=source['title'];texts=[title,source['body'],*source['comments'][:3]]
                    if not 0<len(title)<=500: defects.append('unrepresentable_title')
                    if not any(len(str(v).strip())>=20 for v in texts):defects.append('no_minimum_length_excerpt')
                    label_aliases=[v for v in source['labels'] if 'bug' in v.lower() and v.lower()!='bug']
                    if label_aliases:findings.append({'family':name,'group':group,'number':number,
                        'strict_category_aliases':label_aliases,
                        'note':'Exact category contract may differ from semantic label interpretation; not removed.'})
                else:
                    title=study.family.normalize_text(source.get('title'))
                    if not 0<len(title)<=500:defects.append('unrepresentable_title')
                    if name=='backlog_attention' and study.family.backlog_route(source)=='owned':
                        owner=study.family.normalize_text((source.get('assignees') or [{}])[0].get('login'))
                        if not 0<len(owner)<=120:defects.append('unrepresentable_owner')
                    comments=[study.family.normalize_text(v) for v in source.get('comments',[])[:3]]
                    if any(comments) and not any(study.family.normalize_text(v[:800]) for v in source.get('comments',[])[:3]):
                        defects.append('all_nonempty_comments_outside_tool_window')
                expected=(study.prior.fixed.category_for(source['labels']) if name=='issue_type' else study.family.FAMILIES[name].class_for(source))
                rows.append({'family':name,'group':group,'number':number,'expected_class':expected,'structural_defects':defects})
    result={'scope':'author source-only audit; not independent human review; no selection changes',
        'seal_sha256':study.shared.digest(study.OUT/'seal.json'),'selected_source_records':len(rows),
        'structural_defect_records':[r for r in rows if r['structural_defects']],
        'class_mix':dict(Counter(r['family']+'|'+r['group']+'|'+r['expected_class'] for r in rows)),
        'strict_label_findings':findings,'records':rows}
    study.shared.write_json(study.OUT/'source_audit.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('records','strict_label_findings')},indent=2))
    print('strict label findings:',len(findings))

if __name__=='__main__':main()
