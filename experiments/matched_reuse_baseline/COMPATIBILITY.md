# External baseline compatibility audit

Checked 2026-10-15. This updates the dated external-baseline search, without
altering any earlier sealed comparator protocol or result.

| Candidate | Official evidence checked | Decision for this task |
| --- | --- | --- |
| Agent Workflow Memory (AWM) | [Paper](https://arxiv.org/abs/2409.07429), [official source](https://github.com/zorazrw/agent-workflow-memory), commit `8c0ff8cd11d648c8fceb99e4e42f37e3b75381b1` | Feasible as an explicitly adapted offline workflow-memory baseline. Native implementation targets Mind2Web/WebArena; API-task transport and environment require adaptation. |
| Agentic Workflow Optimization (AWO) | [Paper](https://arxiv.org/html/2601.22037v1), code-release footnote | Footnote says release link removed for double-blind review; this search did not verify an official implementation suitable for execution. Not evidence of permanent unavailability. |
| EvoC2F | [Official proceedings](https://proceedings.mlr.press/v306/wei26q.html) and linked paper PDF | No official implementation verified from these sources; a third-party reproduction is not an official baseline. |
| AgentJIT (Winston et al.) | [Official proceedings](https://proceedings.mlr.press/v306/winston26b.html), [paper](https://arxiv.org/html/2605.21470v1), linked [BLAST commit](https://github.com/stanford-mast/blast/tree/1ded566c7512ceaf25ab6c935f4d14990eb92739) | Browser planner, cached browser histories and browser-use executor; no drop-in API-trace compiler verified. Current BLAST main is a different Rust VM implementation, so using it would not reproduce the cited paper. |
| Agentic Plan Caching | [Authors' project](https://ace-agent.github.io/), [paper](https://arxiv.org/abs/2506.14852) | Plan-caching code link did not resolve to an implementation in this audit; the ACE repository is a different method. |

## Exact AWM reuse and deviations

Apache-2.0 source files are retained verbatim under `vendor/awm`, with license,
commit and SHA256 pins. The adapter extracts only named unchanged function bodies
from those pinned files; this avoids upstream import-time provider clients and
unneeded browser packages. The used functions are `llm_generate`,
`format_examples`, `filter_workflows`, `is_website_header` and `get_exemplars`.
No call to the upstream full browser evaluation loop is claimed.

The domain phrase, tool-schema context, discovery-action serialization, model and
Responses transport are adapted. Upstream one-shot text, workflow formatting,
filtering, and workflow-only prompt insertion remain. Concrete-example retrieval
is disabled, using upstream's top-k=0 option. The induced memory is fixed before
evaluation and no online update occurs.

This compares two different reuse placements: AWM adds learned workflow text to
model context; GAC removes selected model decisions through compiled SDK calls.
That difference is the research question. It does not satisfy an equivalent-
placement compiler-only causal comparison, and cannot fill that stronger gap.
No performance improvement follows from compatibility alone.
