# Implementation readiness

The checklist at the end of [execution-plan.md](execution-plan.md), answered against what
is in this repository. "Yes" means there is code and a test; "partial" means the mechanism
exists and its limit is documented; "no" means it is out of scope for v0.x and named as such.

| item | status | where |
|:---|:---|:---|
| Trace semantics verified against pinned Agents SDK and MLflow versions | yes | `openai-agents` 0.19.2 exercised in 22 live provider runs and integration tests; `mlflow` 3.15 exercised locally |
| One authoritative tracer configured; duplicate-span test passes | partial | the adapter returns a capture manifest, flushes and reconciles counts; applications must still audit composition with other installed processors |
| Entry-state, manifest, effect, approval, freshness, outcome schemas frozen | yes | `schema/` plus `configs/effects.schema.json`, validated in tests |
| Raw-trace retention, redaction, deletion, access policies approved | partial | mechanisms exist (`EntryStateContract`, `redact`, `pseudonymize`, content-addressed refs); an organisational policy is not something code can approve |
| Feasibility estimator validated on planted synthetic workloads | yes | `scripts/generate_synthetic.py` plants nine outcome classes; `tests/unit/test_statistics_and_estimate.py` and `tests/property/` assert recovery *and* rejection |
| Simple handwritten/parallel baseline implemented before GRC credit | yes | condition 2 in every demonstration; it beats the compiler on two of four |
| TGWS and GRC candidates emit complete evidence-bearing artifacts | yes | `Artifact.explain()` prints guard, program, verifier and gate; `verify_release.py` checks gate evidence is present |
| Train/development/calibration/test group isolation automatically checked | yes | `make_splits` asserts disjointness; a leakage test and a chronological-order test exist |
| Production replay cannot call effectful tools | yes | enforced by `ToolFacade`, tested in `tests/fault_injection/` |
| Shadow and fault-injection suites prove pre-commit fallback | yes | fault-injection tests cover mode validation, lifecycle isolation, quota-attested reads, dirty aborts, and zero-execution shadowing |
| Promotion, expiry, retirement, kill switch, rollback exercised | yes | `tests/mutation/` covers all five, including the distinct-approver rule |
| Demo targets and hypotheses pre-registered before sealed-test access | yes | [experiments/manifests/preregistration.md](../experiments/manifests/preregistration.md) |
| Provider, offline stress, and illustrative numbers separated | yes | `substrate=openai_api_live` in `experiments/live_results`; offline stress remains explicitly `simulated` |
| Every user-facing demo executes a real SDK scenario | yes | support, RAG, triage, and stdio MCP in [live-results.md](live-results.md) |
| Paper tables and figures reproduce from frozen run manifests | yes | `scripts/reproduce.py` then `scripts/verify_release.py` |

## Gates

| gate | verdict on this substrate |
|:---|:---|
| **Gate 0 — data** | pass on all four demonstrations (span completeness 1.0 on generated corpora, outcome coverage 1.0, ≥400 groups); the smoke test shows it *failing* correctly on 12 episodes |
| **Gate 1 — economics** | pass on A/B/D by ceiling, fail on C by ceiling — and C is where the largest measured reduction came from, because Eq. (10) does not model route savings (see [spec-review D10](spec-review.md)) |
| **Gate 2 — synthesis** | pass on A/B/C; on D every candidate is fully grounded and still retires at the gate |
| **Gate 3 — retrospective evidence** | pass on A/B/C under the frozen protocol; fail on D |
| **Gate 4 — shadow** | mechanism implemented and exercised offline; live API demos validate tracing and execution but are not a prospective production shadow window |
| **Gate 5 — live** | demo execution only: 22 provider runs passed on fictional fixtures. No production deployment or canary is claimed |

## What is explicitly not done

* transactional staged writes (ADR 0002);
* streaming, hosted tools and handoff-spanning regions — these reject rather than degrade;
* a control-plane service (the CLI is the interface; §10.3 says add the service only when
  several teams need it);
* online adaptation of any kind: artifact generation is offline and immutable.
