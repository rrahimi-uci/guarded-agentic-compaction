"""Render retained descriptive results; does not run or tune the sealed study."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
LABELS = {'baseline': 'Baseline', 'gac': 'GAC', 'awm_offline_adapted': 'AWM adapted'}


def main():
    a = json.loads((OUT/'analysis.json').read_text())
    seal = json.loads((OUT/'seal.json').read_text())
    if hashlib.sha256((OUT/'checkpoint.json').read_bytes()).hexdigest() != a['checkpoint_sha256']:
        raise ValueError('analysis does not bind current checkpoint')
    lines = ['# Matched workflow-memory comparison: retained results', '',
        'This is an API-task adaptation of offline AWM, not a native browser-benchmark reproduction.', '',
        'The primary contrast is GAC minus adapted AWM; comparisons with baseline are secondary.', '',
        f"Attempted {a['attempted']}/{a['scheduled']} evaluation episodes; {a['completed']} completed. "
        f"Halt reason: {a['halt_reason'] or 'none'}. The frozen checkpoint audit passed.", '']
    for group in ('pilot', 'primary'):
        lines += [f'## {group.capitalize()} cohort', '',
            '| Arm | Seven-field correct / scheduled | Four-field factuality | Failed / unattempted | Requests / attempted | Tool calls / attempted | Observed model USD / 1,000 attempted |',
            '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
        for name,row in a['groups'][group]['arms'].items():
            totals=row['observed_resource_totals']; n=row['attempted']
            mean=lambda metric: f'{totals[metric]/n:.3f}' if n else 'NA'
            cost=f"{1000*totals['estimated_cost_usd']/n:.3f}" if n else 'NA'
            lines.append(f"| {LABELS[name]} | {row['correct']}/{row['scheduled']} | {row['factuality_exact']} | "
                f"{row['failed']} / {row['unattempted']} | {mean('requests')} | {mean('total_tool_calls')} | {cost} |")
        lines += ['', 'Resource columns report observed usage per attempted episode. Missing usage is not zero cost; '
            'failure reserves and accounting-completeness flags are retained in the JSON. All scheduled episodes remain in accuracy denominators.', '',
            '| Paired contrast | Accuracy difference, percentage points [descriptive 95% bootstrap] | A-only / B-only correct | Exact McNemar p | Holm p |',
            '| --- | ---: | ---: | ---: | ---: |']
        for name,c in a['groups'][group]['contrasts'].items():
            ci=c['accuracy_difference']; low,high=ci['ci95']
            lines.append(f"| {name} | {100*ci['mean']:.2f} [{100*low:.2f}, {100*high:.2f}] | "
                f"{c['a_only_correct']} / {c['b_only_correct']} | {c['mcnemar_exact_p']:.4f} | {c['mcnemar_holm_p']:.4f} |")
        lines += ['', 'Intervals resample paired issues, not arm episodes. Holm adjustment covers the three accuracy contrasts '
            'within this cohort; other intervals are descriptive. Exact marginal accuracy intervals are in the JSON. '
            'A zero-width paired bootstrap at the boundary does not establish equality or noninferiority.', '']
    induction=a['induction']
    lines += ['## Cost and scope', '',
        'The observed accuracy advantage is not established statistically (primary exact McNemar p=0.50, Holm p=1.00). '
        'A post-run source audit found one structurally unanswerable excerpt task (issue 377); all three arms failed it and '
        'it remains in every primary denominator. See [ERROR_AUDIT.md](ERROR_AUDIT.md) for this limitation and strict-label errors.', '',
        f"New known study cost, including pilot and induction: ${sum(v['observed_resource_totals']['estimated_cost_usd'] for g in a['groups'].values() for v in g['arms'].values())+induction['metrics']['estimated_cost_usd']:.8f}.", '',
        f"New induction estimated cost: ${induction['metrics']['estimated_cost_usd']:.8f}; "
        f"amortized per primary task: ${a['induction_cost_amortized_per_primary_task_usd']:.8f}. "
        f"Induction elapsed time: {induction['metrics']['wall_latency_ms']/1000:.3f} seconds.", '',
        f"GAC reconstruction preflight elapsed time: {a['reconstruction_wall_latency_ms']/1000:.3f} seconds, "
        'including source loading and compatibility checks; this is not a priced compiler-only time.', '',
        'The historical acquisition of the shared 132-trace discovery pool is a sunk, shared cost. '
        'AWM uses the same 130 compiler-eligible traces; GAC retains its historical train/development/calibration split. '
        'The comparison does not price total lifetime development or historical optimization effort.', '',
        f"Aggregate estimates and retained reserves: ${a['aggregate_estimate_and_reserve_usd']:.8f} "
        f"against the ${seal['approved_aggregate_cap_usd']:.0f} authorized cap. This includes "
        f"${seal['budget']['prior_estimate_and_reserve_usd']:.8f} carried forward. This is not a provider billing cap.", '',
        'One model, one workflow, one historical snapshot, one induction output and one stochastic evaluation per arm/issue '
        'limit generalization. Memory placement and compiled execution differ by design; this is a whole-system comparison. '
        'No new risk certificate, isolated gate benefit, broad runtime dominance, equivalence or acceptance probability is established.', '']
    (OUT/'RESULTS.md').write_text('\n'.join(lines))
    tex=[r'\begin{tabular}{lrrrrr}', r'\toprule',
         r'Arm & Correct & Factual & Requests & Tools & USD/1k \\', r'\midrule']
    for name in ('baseline','gac','awm_offline_adapted'):
        r=a['groups']['primary']['arms'][name]; t=r['observed_resource_totals']; n=r['attempted']
        if not n:
            raise ValueError('cannot render a primary table with no attempts')
        tex.append(f"{LABELS[name]} & {r['correct']}/{r['scheduled']} & {r['factuality_exact']}/{r['scheduled']} & "
                   f"{t['requests']/n:.2f} & {t['total_tool_calls']/n:.2f} & {1000*t['estimated_cost_usd']/n:.3f} " + r'\\')
    tex += [r'\bottomrule',r'\end{tabular}']
    (ROOT/'paper/iclr/tables/matched_reuse.tex').write_text('\n'.join(tex)+'\n')
    print('rendered RESULTS.md and primary manuscript table')


if __name__=='__main__':
    main()
