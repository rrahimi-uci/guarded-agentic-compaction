# AgentHop section-lookahead timing audit

**Development decision: timing opportunity only. No derived selector, admitted GAC artifact, matched arm, or superiority claim.** This provider-free posthoc audit follows the [sealed 24-case baseline pilot](../agenthop_baseline_trace_pilot/REPORT.md). It checks the exact protected raw-trace hashes, public tool-call projection, pinned public QA hash, and model-visible `list_sections` output before counting transitions. The [machine-readable report](report.json) retains only navigation counts and case IDs, not questions, paper text, model reasoning, or answer labels.

Across all 24 cases, **42 adjacent model-turn transitions in 22 cases** had a `list_sections` result followed by at least one `read_section` call on a listed paper. In **41/42** transitions, the entire next tool-call batch consisted of those same-paper section reads. There were **65** such reads, and **61** targeted a heading or alphabet alias present in the section list visible to the model. These are observed next-turn choices. If a future compiled selector had predicted the *entire* next batch correctly and an equivalent synthetic continuation preserved behavior, it might remove one model request per such transition. The audit did not execute that intervention; the count is an opportunity ceiling, not saved requests or final-answer quality.

A narrow posthoc diagnostic fixes the paper already selected by the model and examines **19** transitions with one listed paper, one next `read_section`, and a visible target heading. Four simple choices matched the model-selected heading as follows: first experimental/results heading or first otherwise **7/19**; `Introduction` or first otherwise **6/19**; longest section **5/19**; question–header lexical overlap **5/19**. The rules and subset were inspected after these cases were exposed. They are neither a trained GAC selector nor an independent validation set, and they receive the model-selected paper for free. They do not justify a paid matched GAC arm.

The bottleneck is a grounded *semantic section choice* after the list result and often after earlier paper content. GAC's current closed binder cannot be declared successful from this timing pattern. A new selector would require separate training trajectories, a frozen rule, held-out source-aware evaluation, live-tool and continuation parity, and cost accounting. The same rule must be available to the handwritten and simpler compiler controls. The current AgentHop subtype has one full-neighborhood source component, so a source-independent risk certificate cannot be claimed from this cohort. Repeating these exposed cases or prefetching extra sections until one is useful would not answer the reviewer comparison.

Reproduce the provider-free audit with the pinned QA file and retained protected traces from the baseline pilot:

```sh
python paper/scripts/agenthop_section_lookahead.py \
  --qa /path/to/qa/full.jsonl \
  --raw-dir /path/to/protected/agenthop_baseline_trace_pilot/raw
python paper/scripts/validate_artifacts.py --families agenthop_section_lookahead
```

No provider request was made, no new benchmark case was selected, and the manuscript's numerical claims remain unchanged. The local raw-trace parity check cannot be rerun without the protected cache; CI checks the retained aggregate, hash links, and claim boundary.
