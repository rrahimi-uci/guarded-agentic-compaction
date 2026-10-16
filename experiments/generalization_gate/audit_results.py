"""Post-registration descriptive audit; never changes the primary analysis.

Adds source error taxonomy and author/day cluster sensitivity. Not an independent
human review, new gate certificate, or a replacement noninferiority test.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'paper/scripts')]
import generalization_gate_study as study


def cluster_sensitivity(numbers,differences,labels):
    groups=defaultdict(list)
    for n,d in zip(numbers,differences):groups[labels[n]].append(d)
    sums=np.array([sum(v) for v in groups.values()],dtype=float)
    sizes=np.array([len(v) for v in groups.values()],dtype=float)
    rng=np.random.default_rng(20261021)
    draws=rng.integers(0,len(groups),size=(10000,len(groups)))
    estimates=sums[draws].sum(axis=1)/sizes[draws].sum(axis=1)
    return {'groups':len(groups),'largest_group':int(sizes.max()),
        'accuracy_difference':float(sum(differences)/len(numbers)),
        'descriptive_cluster_bootstrap_ci95':[float(x) for x in np.quantile(estimates,[.025,.975])],
        'warning':'Post-registration descriptive sensitivity. Groups are not proven independent; degenerate intervals do not establish equality.'}


def main():
    sealed,runtimes=study.verify()
    checkpoint=json.loads((study.OUT/'checkpoint.json').read_text())
    analysis=json.loads((study.OUT/'analysis.json').read_text())
    if analysis['checkpoint_sha256']!=study.shared.digest(study.OUT/'checkpoint.json'):raise ValueError('analysis stale')
    study.audit(sealed,runtimes,checkpoint)
    raw=study.family.load_store()[0]
    rows=checkpoint['rows'];details=[]
    dispatch_expected={key:{r['issue_number']:r['arms']['gac']['compacted'] for r in cell['probe']['records']} for key,cell in sealed['cells'].items()}
    dispatch_mismatches=[]
    checked_dispatches=0
    for row in rows:
        if row['arm']=='gac' and row['status']=='completed':
            checked_dispatches+=1
            key=row['family']+'|'+row['model']
            if bool(row.get('compacted'))!=dispatch_expected[key][row['issue_number']]:
                dispatch_mismatches.append({k:row.get(k) for k in ('index','family','model','issue_number','compacted','dispatch')})
    for row in rows:
        if row['status']=='completed' and row.get('correct'):continue
        errors=[k for k,v in row.get('quality',{}).items() if v is False and k not in ('overall','tool_contract','trace_valid','factuality_exact')]
        n=row['issue_number'];rt=runtimes[row['family']+'|'+row['model']]
        item={k:row[k] for k in ('index','group','family','model','issue_number','arm','status')}
        item.update(failed_checks=errors,answer=row.get('answer'),error=row.get('error'))
        if row['family']=='issue_type':
            source=rt['store'][n]
            item.update(source_labels=source['labels'],expected_category=study.prior.fixed.category_for(source['labels']))
            if any('bug' in v.lower() and v.lower()!='bug' for v in source['labels']):
                item['interpretation']='Strict label matching may differ from semantic category; not necessarily a factual falsehood.'
        details.append(item)
    strata=defaultdict(lambda:{'attempted':0,'completed':0,'correct':0})
    for row in rows:
        if row['group']!='primary':continue
        rt=runtimes[row['family']+'|'+row['model']];source=rt['store'][row['issue_number']]
        label=study.prior.fixed.category_for(source['labels']) if rt['name']=='issue_type' else study.family.FAMILIES[rt['name']].class_for(source)
        group=strata['|'.join((row['family'],row['model'],row['arm'],label))]
        group['attempted']+=1;group['completed']+=int(row['status']=='completed')
        group['correct']+=int(row['status']=='completed' and bool(row.get('correct')))
    sensitivity={}
    for key,rt in runtimes.items():
        ns=sealed['cohorts'][rt['name']]['primary']
        selected={(r['issue_number'],r['arm']):r for r in rows if r['family']==rt['name'] and r['model']==rt['model'] and r['group']=='primary'}
        if any((n,a) not in selected for n in ns for a in ('gac','awm_offline_adapted')):continue
        def correct(n,arm):
            r=selected[(n,arm)]
            return int(r['status']=='completed' and bool(r.get('correct')))
        diff=[correct(n,'gac')-correct(n,'awm_offline_adapted') for n in ns]
        day={n:str(raw[n].get('created_at') or 'missing')[:10] for n in ns}
        author={n:str((raw[n].get('user') or {}).get('id') or 'missing') for n in ns}
        sensitivity[key]={'creation_day':cluster_sensitivity(ns,diff,day),'author':cluster_sensitivity(ns,diff,author)}
    memories={key:{'all_family_tools_named':all(t.name in checkpoint['inductions'][key]['memory'] for t in rt['tools']),
        'generic_induction_header_retained':'Software,Issue triage,github',
        'note':'Post-run content audit only; no memory modification or new induction.'} for key,rt in runtimes.items()}
    result={'memory_content_audit':memories,'checkpoint_sha256':analysis['checkpoint_sha256'],'scope':'post-registration author audit; not independent human adjudication',
        'completed_gac_dispatches_checked':checked_dispatches,'dispatch_probe_mismatches':dispatch_mismatches,
        'incorrect_or_failed_episodes':len(details),'failure_types':dict(Counter(r['error']['error_type'] for r in details if r.get('error'))),
        'field_error_counts':dict(Counter(k for r in details for k in r['failed_checks'])),
        'class_disaggregation':dict(strata),'errors':details,'cluster_sensitivity':sensitivity}
    study.shared.write_json(study.OUT/'error_audit.json',result)
    lines=['# Source error and clustering audit','',result['scope']+'. No outcome or cohort is changed.','',
        f"Incorrect or failed episodes, including pilot: {len(details)}.",
        f"Completed live GAC dispatches checked against frozen probes: {checked_dispatches}; mismatches: {len(dispatch_mismatches)}.",
        f"Failure types: {result['failure_types']}.",f"Field-check failures: {result['field_error_counts']}.",'',
        '| Cell | Day groups / largest | Author groups / largest | Day-bootstrap accuracy-difference CI | Author-bootstrap CI |',
        '| --- | ---: | ---: | --- | --- |']
    for key,v in sensitivity.items():
        d,a=v['creation_day'],v['author']
        lines.append(f"| {key.replace('|',' / ')} | {d['groups']} / {d['largest_group']} | {a['groups']} / {a['largest_group']} | {d['descriptive_cluster_bootstrap_ci95']} | {a['descriptive_cluster_bootstrap_ci95']} |")
    lines+=['','Cluster intervals are post-registration descriptive sensitivity; author/day independence is unproven. Zero-width intervals do not prove equality or noninferiority. The registered exact six-cell analysis remains primary.','',
        'The source-only structural screen is in source_audit.json. Labels such as dataset bug can produce strict contract failures without demonstrating a semantically false classification. Full per-episode answers and failed checks are in error_audit.json.']
    (study.OUT/'ERROR_AUDIT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('errors','cluster_sensitivity','class_disaggregation')},indent=2))

if __name__=='__main__':main()
