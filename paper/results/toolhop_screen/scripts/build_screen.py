import json, sys, collections
A = sys.argv[1]  # analysis dir
OUT = sys.argv[2]
C = collections.Counter
a2 = json.load(open(A + '/a2.json')) if False else None
# query-level openings (a2.json written by a2.py)
q = json.load(open(A + '/openings_queries.json'))
g = json.load(open(A + '/openings_grouped.json'))
der = json.load(open(A + '/derivability.json'))
chain = json.load(open(A + '/chain_level.json'))
dep = json.load(open(A + '/dep_binder.json'))
static = json.load(open(A + '/a3.json'))
runs = [json.loads(l) for l in open(A + '/../out/all.jsonl')]
st = C(); hop0 = C(); hopn = C()
for r in runs:
    for s in r['steps']:
        k = 'unsafe_screen' if s['status'].startswith('unsafe') else s['status']
        st[k] += 1
        (hop0 if s['i'] == 0 else hopn)[k] += 1
def slim(o):
    return {k: v for k, v in o.items() if k != 'top'}
screen = {
    'schema': 'gac-toolhop-screen-v1',
    'decision': 'NO_GO',
    'provider_calls': 0,
    'source': {
        'hf_dataset': 'bytedance-research/ToolHop',
        'revision': 'b439d7279af359fda46e8117ae4f0245b75f5c6b',
        'data_file_sha256': '0a51f71a44b7025645e452123af3caf2e348301922af91778e268db0188a7fab',
        'data_licence': 'CC BY 4.0', 'code_licence': 'Apache-2.0',
        'queries': 995, 'tools': 3912, 'hops': {'3': 428, '4': 353, '5': 136, '6': 10, '7': 68},
        'mean_hops': 3.9317, 'distinct_tool_names': 622, 'distinct_function_bodies': 3912,
        'function_bodies_shared_across_queries': 0, 'distinct_full_parameter_schemas_at_first_hop': 994,
        'gold_call_chain_released': False,
        'gold_sequence_released_as': 'ordered sub_task dict (sub-question -> intermediate answer) aligned with tools and functions',
        'grader': 'deterministic Python (eval equality or lowercase substring; final tool message containing the answer also counts); no LLM judge',
        'answers_single_character': 311, 'answers_numeric_literal': 639,
    },
    'tool_static_audit': static,
    'tool_static_audit_notes': {
        'file_write_tools': 2, 'eval_or_exec_of_caller_string_tools': 2,
        'network_tools': 0,
        'retrieval_named_tools_embedding_gold_answer_literal': '1842/2028 (90.8%)',
    },
    'reconstruction_run': {
        'method': 'sandbox-exec (no network, no writes) execution of AST-screened tool code with candidate kwargs; success = non-error output containing the sub-task answer',
        'steps': sum(st.values()), 'step_status': dict(st), 'hop0_status': dict(hop0), 'hop_ge1_status': dict(hopn),
        'queries_all_steps_reconstructed': chain['qsum'].get('full'),
    },
    'recurrence_by_query': {k: slim(v) for k, v in q.items()},
    'recurrence_by_independent_group': g,
    'independent_groups': {'distinct_first_sub_questions': 298, 'components_shared_first_subquestion_or_first_hop_answer': 286,
                           'largest_component': 17, 'entity_sharing_components': 263,
                           'mean_requests_per_baseline_episode_est': 4.93, 'prefix1_ceiling_fraction': 0.2028},
    'baseline_competence': {'best_forced_tool_published': 0.5558, 'best_forced_tool_model': 'Qwen3-32B Thinking',
                            'gpt_5_4_mandatory': 0.5447, 'gpt_5_4_free': 0.5538, 'o3_free': 0.7568,
                            'o3_direct_no_tools': 0.6844, 'claude_opus_4_6_direct_no_tools': 0.6412,
                            'gpt_4o_paper_mandatory': 0.4904,
                            'source': 'HF Space Junjie-Ye/ToolHop index.html sha bce3797505b1ccc4b5f3f64613ccfba45949aff2 (accessed 2026-11-06); ACL 2025 paper Table 4'},
    'cost_estimate_per_episode_usd': {'basis': 'tool schemas ~5.6k chars; ~4.9 requests; ~9.5k input + ~0.27k visible output tokens; excludes reasoning tokens and caching',
                                      'list_price_1.25_10': 0.0145, 'list_price_2.5_15': 0.0276, 'with_reasoning_3x_to_6x': [0.05, 0.15]},
    'derivability': {
        'dependent_steps_reconstructed': 2320,
        'dependent_argument_leaves': 2260,
        'output_relation_counts': der['tab'],
        'answer_relation_counts': der['answer_relation'],
        'hop0_string_args_substring_of_question': der['hop0_args'],
        'hop0_instance_level_T_v1_chain_non_baked': der['hop0_instance_chain'],
        'hop0_cross_instance_binder_families_tested': len(der['fam_res']),
        'hop0_cross_instance_binder_families_bound': sum(1 for r in der['fam_res'] if r['binding_found']),
        'hop0_bound_family_detail': [r for r in der['fam_res'] if r['binding_found']],
        'chain_level': chain,
        'dependent_binder_by_previous_tool_family': {'families_ge5_groups': len(dep), 'bound': sum(1 for r in dep if r['binding_found']),
            'groups_covered': sum(r['groups'] for r in dep)},
        'manual_sample': {'rows': 120, 'seed': 0, 'note': 'random sample of dependent-argument leaves; rules in REPORT.md'},
    },
}
json.dump(screen, open(OUT, 'w'), indent=1, sort_keys=True, default=str)
print(json.dumps({k: screen[k] for k in ('reconstruction_run',)}, indent=1))
