# Adaptive benchmark selection and development evidence

**Decision: use WebArena-Verified for the next browser-runtime development phase.**
The six-task baseline pilot completed with **6/6 official grader successes**, 42 provider
requests, 36 browser actions (including six action errors), and **$0.0939408** in conservative
API accounting. This establishes an operational evaluation path, not a GAC performance result.
The campaign ledger accounts for $1.6077511 of the authorized $300 cap; $298.3922489 remains.
These are ledger estimates, not invoices, and exclude local compute costs.

## Why the ranking changed after source inspection

| Source | Verified finding | Decision |
|---|---|---|
| [τ²-Bench-Verified](https://github.com/amazon-agi/tau2-bench-verified/tree/864350a8971a8f8ee9e7b8472e2edc380a806b0c) | All 50 airline, 114 retail, and 2,285 telecom task IDs overlap the older source already analyzed by this project. These are records, not 2,449 independent scenarios. | Useful for replication; no fresh-confirmation claim from this release. Changed answers do not erase task lineage. |
| [Original WebArena](https://github.com/web-arena-x/webarena/tree/dce04686a56253aefba7b18a4fa0937cf1dc987b) | 812 tasks / 190 templates; 118 configurations contain `fuzzy_match`, including cases with a model-judged fallback. | Prefer the verified release's deterministic graders. |
| [WebArena-Verified](https://github.com/ServiceNow/webarena-verified/tree/6473f72db5dcefc97b5725b59e734504edc28a21) | 812 tasks / 190 templates; 812 response evaluators and 663 network-event evaluator configurations; 106 single-site Reddit tasks. | Selected for development. Actual browser actions and captured HAR are evaluated by the unmodified official grader. |
| AppWorld 0.2.0 | The official reference passes 2/2 tests on one exposed training case; doing nothing and false completion each fail the task. Private API and reserved-argument calls are refused. | Working development control path; paid study deferred. Historical train/dev solutions and test trajectories were already inspected. |

[screen.json](screen.json) is recomputable from pinned source files and includes their hashes.
Only metadata and identifiers were used for benchmark/cohort selection; task outcomes did not
influence the selection. Fetching a public benchmark is not evidence of model-training cleanliness.

## What was actually executed

Six Reddit tasks were selected with a fixed hash ordering, one instance per template, after
excluding entire templates encountered in the inspected Agent JIT catalog/documentation.
The selected IDs are 634, 409, 600, 69, 622, and 643. All remain development-only, as do every
other variant of those templates. Five involve writing a post/comment and one retrieves information.
Six template IDs do not establish six independent kinds of workflow; several share posting behavior.

The baseline receives only the upstream public agent-input fields and an accessibility snapshot.
It can use a bounded browser-action tool and a structured finish tool. It receives no evaluator
configuration or expected answer. Each task starts with a new application container and browser
context; the application port binds to loopback. Browser requests are restricted to that one origin.
The website has a dedicated Docker bridge, not a networkless container. The synthetic benchmark
account uses upstream's documented header authentication. No production service or account is used.

The immutable website image is
`am1n3e/webarena-verified-reddit@sha256:0594908059a03e5f610005689440a95c05e776e734006197c7b1eba12734cb46`.
Its amd64 code ran on an arm64 host. Elapsed times include setup and emulation and must not be
presented as native performance or compared with native compiler timings.

Before paid execution, a handwritten **control** completed development task 634 through the UI
and passed the official grader. Twelve no-action/false-completion controls failed as expected.
This is one positive integration control, not a positive reference run for every selected task and
not a handwritten comparator measurement. Separately, 469 unmodified upstream evaluation/type
tests passed and four skipped. Their dependency's Python 3.13 `SyntaxWarning` was ignored;
the grader source was not patched.

The original negative-control attempt passed an empty trace list, which the official parser
rejected as an error. The v2 protocol instead records a real no-action page visit. The v1 seal,
sources, positive HAR and twelve format errors remain in the archive. The amendment preceded
all model calls; task selection, model, request cap and spending cap did not change.

The complete records are in [webarena_development/report.json](webarena_development/report.json),
[seal.json](webarena_development/seal.json), [ledger excerpt](webarena_development/ledger_excerpt.json),
and [raw evidence](webarena_development/raw_evidence.tar.gz). The archive includes unsuccessful
browser actions and both control versions. No task was replaced or rerun to improve the score.
The official grader checks responses and network traces; it does not certify arbitrary safety
properties or all possible collateral database changes.

AppWorld operational records are separately retained in
[appworld_controls/report.json](appworld_controls/report.json). Protected source-derived output
is redistributed only in the upstream encrypted bundle format, with its license notices.
The local image is identified, but has not been published; rebuilds require dependency and data
verification rather than assuming a byte-identical image.

## What remains before a paper-strength comparison

1. Separate browser actions by audited effects. The present `browser` tool mixes navigation,
   filling forms, and submitting writes. It must remain non-compilable until an explicit effect
   policy and transactional browser-state handoff exist; a link named “Submit” is not a safety proof.
2. Implement and test GAC's guarded execution and fallback using the same continuation interface
   as the unchanged agent and simpler controls. Actual writes stay in adaptive continuation.
3. Freeze discovery, calibration and test populations after a complete prior-use/grouping audit.
   The 174 remaining candidate template IDs are not a certified fresh or power-qualified holdout.
   Do not count repeated seeds or task variants as independent families.
4. Specify the matched comparison before outcomes: unchanged agent, GAC, handwritten/composite
   retrieval, unguarded reuse, and a faithful compiler comparator where supported. The inspected
   Agent JIT implementation uses original WebArena evaluators and specifies native x86 execution;
   this verified/emulated pilot is not a native Agent JIT comparison.
5. Measure end-to-end success, coverage, fallback, all model requests/tokens, setup/maintenance
   costs and amortization. Specify a separate change/stress evaluation and report unfavorable cases.

No manuscript accuracy, savings, admission, learned-selection, or superiority claim was updated.
The next milestone is a tested GAC browser adapter and a frozen matched protocol, not a larger
uncontrolled baseline run. See the [protocol and reproduction instructions](../../supplementary/adaptive-open-benchmark-development.md).
