# Browser boundary development and next experiment gate

This phase follows the six-task WebArena-Verified development baseline in
[the benchmark audit](adaptive-open-benchmark-development.md). It is a research
implementation and mechanism check, not a new manuscript performance result.
The prior baseline, its source seals, and its paid-call ledger remain unchanged.

## What the boundary owns

The entry state is an immutable **fresh-episode blueprint**, containing only the
public task, pinned image, public simulation principal, and request-policy version.
There is no pre-existing live agent, provider conversation, browser context, or
application instance to restore. This restriction is essential: a DOM snapshot
does not restore a server session, JavaScript state, cookies, timers, or effects.

Staging creates a dedicated website container, network, browser context and page.
The single typed tool opens the literal `Submit` anchor at the fresh Reddit root
and checks its destination and form postcondition. The general `browser` tool
remains `UNKNOWN`; filling and submitting remain write barriers. The checked
GAC interpreter and sandbox facade enforce the allowed tool and a one-call limit.
An empty program cannot pass the boundary, even with a permissive verifier.

The staged browser allows same-origin GET requests only to `/`, `/submit`, and
the pinned site's static resources. Five exact static cache-busting queries and
the exact SVG sprite path are allowed. Arbitrary query parameters, other document
routes, POSTs, fetch/XHR requests, external origins and WebSockets are refused.
The immutable image and source audit are part of this narrow interpretation;
GET is not generally read-only. The website container uses its own bridge and a
loopback-only host port, not a networkless environment. Browser filtering does
not prove that arbitrary server software cannot make outbound requests.

Before and after the compiled read, the controller hashes a full PostgreSQL
data dump, including sequence values. This detects the injected business-data
mutation. It does not prove that every possible side effect is absent: session
files, CSRF tokens, access logs and elapsed time are outside that comparison.
They live inside the owned instance, and the session is kept or discarded as a
unit. The reviewed pinned source places submission writes behind valid form
submission; its native file sessions and CSRF protection still require this
ownership model. The login listener can also update persistent last-seen state;
therefore the authenticated entry is established before taking the data digest.

On successful research verification, the **same** application, context and page
continue, retaining the form's CSRF token. The request policy then permits local
continuation writes. On rejection, the entire staged instance is closed before
a fresh baseline is instantiated from the blueprint. Cleanup failure propagates
as an incident. Cleanup is registered before network/container creation, including
the case where Docker creates a resource but its CLI response is lost. The form
and network-policy postcondition are checked again after the data digest, so a
late policy violation cannot promote the session. Cancellation drains the bounded interpreter and closes its
session; it never silently launches the baseline. All staged requests, rejected
requests, HARs and elapsed setup/cleanup time remain evidence. Costs are not
rolled back, and no claim of identical wall-clock execution is made.

This is not an adapter for the production dispatcher's full `Staging` snapshot
contract. It must not be substituted for exact restoration of an arbitrary live
browser. `research_commit` is a mechanism-test outcome, **not GAC admission**.

## Discovery and controls

`browser_prefix_discovery.py` converts all six previously executed development
traces. It preserves 42 provider responses, 36 browser actions and six action
errors. Only the first literal Submit click at the root is represented as the
new typed tool; all other browser calls remain unknown effects. Historical
observations are preserved verbatim. These old calls were not server-attested:
the conversion is explicitly a posthoc representation hypothesis.

The compiler synthesizes one single-call candidate from four template groups
(tasks 634, 600, 622 and 643). It rejects the candidate at `no_dev_groups` and
emits **zero artifacts**. Every group is development/training material; there
are no held-out challenge, calibration or test groups. A root-page check would
also match the retrieval task 69. Neither the task intent nor the selection
decision has been validated sufficiently for automatic dispatch.

The live control harness uses development task 634 only. It separately tests a
handwritten program and the automatically synthesized **unadmitted** candidate
through the checked interpreter, followed by a fixed handwritten continuation.
It also isolates output-verifier rejection, a trusted injected database change,
and a POST blocked before backend execution. The official pinned HAR grader
checks actual posting after handoff/fallback and rejects false completion when
the baseline takes no action. This is an integration check, not adaptive model
continuation or an independent population estimate. The database mutation and
JavaScript POST are trusted test injections, never model-provided code.

The retained [report](../results/browser_staging_boundary/REPORT.md) distinguishes
the final controls from earlier failed setup attempts. No result from this phase
supports a quality, speed, cost, learned-gate, or compiler-necessity advantage.
In particular, a handwritten shortcut performs the same one-call action.

## Next experimental decision

Do not spend the remaining campaign allowance on repeated variants of this
single form-opening action just to obtain a larger success count. The unresolved
reviewer question is whether guarded compilation provides a useful advantage
over an equally capable simpler compiler after accounting for rejected attempts
and lifecycle cost. The next study must meet the following conditions:

1. **Task suitability before outcome inspection.** Enumerate public task metadata
   and task families with independently executable graders. Exclude every prior
   exposed template and all six current development templates from fresh evidence.
   The 174 remaining candidate template IDs from the earlier metadata screen are
   not automatically eligible or independent. Establish distinct read-prefix
   behaviors and natural guard failures; a second useful workflow should be
   demonstrated before treating this benchmark as a multi-family comparison.
2. **Freeze a development-only candidate and routing rule.** Use only observable
   public entry fields and actual tool results, never hidden grader fields or test
   outcomes. A task-ID allowlist is not a generalizing guard. Log the entire
   compiler rejection funnel and retain failed tasks. Reject unsafe effect ports.
3. **Demonstrate adaptive continuation.** In a new versioned runner, give each arm
   the same agent/model/tool catalog, history policy, request limits and official
   grader. After a compiled prefix, explicitly inject the equivalent action and
   observation history into the model's continuation. Verify first that this
   changes neither tool access nor hidden-answer isolation. Keep the six current
   tasks available only for development and debugging.
4. **Use meaningful comparators and splits.** Compare baseline, the handwritten
   shortcut, recurrence-only compilation and GAC with identical typed tools,
   owned-instance boundaries, train/challenge/calibration/test groups and resource
   limits. Freeze candidates before calibration. If GAC rejects the candidate,
   record baseline fallback; never force the research program into an admitted arm.
   A support-only arm must differ at compiler admission, not merely dispatch over
   an already-admitted registry. Cluster repeated variants by their shared family.
5. **Predeclare endpoints and affordability.** Use official task success as the
   primary quality endpoint. Count all scheduled attempts, API failures, fallback
   and setup failures. Measure total provider calls/tokens, staged and continuation
   tool calls, latency including provisioning/data hashes/cleanup, offline build
   cost and amortization. Estimate feasible sample size and paired uncertainty
   before claiming power. A full data dump may cost more than one saved model call;
   these controls do not establish economic feasibility.
6. **Keep the go/no-go rule binding.** Freeze group IDs, hypotheses, stopping rules,
   prices, run limits and analysis before paid execution using the existing shared
   $300 campaign ledger. Report null or negative results. If no diverse, useful
   candidate or affordable uncertainty target survives, retain this mechanism
   evidence and pivot to the prepared AppWorld reference-graded development path
   rather than presenting a one-action WebArena control as the missing experiment.

## Reproduction

Discovery and ordinary tests use the repository environment and committed archive:

```sh
.venv/bin/python paper/scripts/browser_prefix_discovery.py
.venv/bin/python -m pytest -o addopts='' -q paper/scripts/test_browser_staging_boundary.py
```

Live controls require Docker with the pinned image, the pinned WebArena-Verified
checkout from the prior benchmark protocol, and an isolated Python environment.
Use the exact packages in the retained successful seal, including Playwright
1.61.0 and its matching Chromium installation. Installing that package alone does
not install the browser. The new environment must remain separate from the old
development runner's sealed environment. For an operational reproduction:

```sh
uv venv benchmarks/.cache/browser_boundary/venv --python 3.13
uv pip install --python benchmarks/.cache/browser_boundary/venv/bin/python -e . \
  -e benchmarks/.cache/adaptive_benchmark_screen/webarena-verified \
  playwright==1.61.0 pytest openai python-dotenv
benchmarks/.cache/browser_boundary/venv/bin/python -m playwright install chromium
benchmarks/.cache/browser_boundary/venv/bin/python paper/scripts/browser_boundary_controls.py \
  --output benchmarks/.cache/browser_boundary/new-versioned-attempt
```

The unpinned ancillary dependency installation above is a setup recipe; use the
seal's complete package versions for exact reproduction. The runner refuses an
existing output directory, records source copies before execution and never
calls a provider. Keep every failed attempt and the shared campaign ledger.
No manuscript table, abstract or compiled PDF is changed by this phase.
