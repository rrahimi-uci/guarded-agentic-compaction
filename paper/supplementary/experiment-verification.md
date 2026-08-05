# Experiment verification report

**Audit date:** 2026-08-05<br>
**Scope:** checked-in evidence only; no provider or benchmark-service calls were made.

## Verification protocol

The audit rebuilt every deterministic table and figure, recomputed registered oracles and
paired summaries from retained row-level results, checked source revisions and SHA-256
digests, verified split disjointness and condition ordering, inspected LaTeX build
diagnostics, and ran the repository claim validator. The validator checks raw evidence
rather than trusting manuscript prose.

    .venv/bin/python paper/scripts/build_artifacts.py
    .venv/bin/coverage run -m pytest -q
    .venv/bin/coverage json -o paper/results/coverage.json
    .venv/bin/python scripts/verify_release.py
    .venv/bin/python paper/scripts/validate_artifacts.py

The existing live outputs record API-key use while explicitly recording that no secret
was serialized. This review read environment variable names only and did not execute a
paid demo.

## Claim-by-claim result

| Claim family | Recomputed evidence | Audit conclusion |
|:---|:---|:---|
| Expanded GitHub replication | 132 discovery traces; 30 disjoint held-out issues; all six condition orders occur five times | design and split claims match retained data |
| Partial GAC quality | baseline, compiled, and macro each pass 30/30 exact factual and task contracts | observed equality is correct; it is not proof of equivalence |
| Partial GAC efficiency | requests −50.0%, total tokens −39.5%, observed wall latency −51.7%, estimated cost −32.0% | all aggregate reductions recompute from rows |
| Manual macro comparison | macro passes 30/30 and beats partial GAC on tool calls, tokens, and estimated cost | manuscript correctly treats the macro as the practical baseline |
| Aggressive compiler | compiled 17/18 versus 18/18 for both comparators | the retained compiler-only factual miss is real and bounds the depth claim |
| GCS comparison | GCS and provider-visible macro each pass 12/12; GCS uses one versus two requests | exact quality and resource summaries recompute |
| Fair pre-model comparison | GCS and independent manual program each pass 6/6 and tie on requests, interfaces, and input tokens | no automatic-runtime-superiority claim is licensed |
| GEPA | official 0.1.4; 14 task evaluations; 59 optimization requests; seed retained | valid bounded negative result, not evidence against GEPA generally |
| NESTFUL | 1,415 traces; 24/12/0 split; maximum family support 26 versus required 92 | every family correctly retires |
| API-Bank | 212 complete traces; 48 candidate windows; two synthesized families; no held-out admission | second compiler substrate reproduces refusal, not a positive efficiency result |
| Ten-source audit | 5,419 tasks; 17,836 reference actions; two trace-complete compiler substrates | ledger totals and all explicit gates match evidence |

## Statistical interpretation

- Zero observed failures in 30 cases has a one-sided 95% Clopper--Pearson upper bound of
  approximately 9.5%; the paper must not call this semantic equivalence or production
  certification.
- One compiled failure in 18 cases has a one-sided 95% upper bound of approximately
  23.8%. McNemar p=1 on such sparse discordance does not establish equivalence.
- Latency is wall-clock provider evidence and is noisy. Paired intervals, not point
  estimates, govern comparative claims.
- The exact gate is a valid finite-sample rule over the registered replay contract, but in
  current data it behaves as an all-or-none support threshold. It has not demonstrated a
  useful risk--coverage frontier.
- NESTFUL, API-Bank, hosted benchmark runs, simulated benchmark environments, and the
  real-record GitHub intervention measure different objects. They are intentionally
  reported as a ledger and never pooled into one performance score.

## Residual threats

The strongest paired causal evidence covers one extractive GitHub workflow, one model
configuration, and small held-out cohorts. Manual construction effort is not measured.
Continuation-level factual preservation is checked after execution rather than being the
compiler's primary admission endpoint. Multidomain vulnerability and HMDA assets are
provider-free preflight evidence only; SEC acquisition and the live multidomain protocol
remain gated. These limits are reflected in the manuscript, site, and review rather than
treated as future results.

## Audit disposition

The checked-in quantitative claims are internally consistent and reproducible from
retained artifacts. The evidence supports a guarded-specialization and refusal result,
not state-of-the-art quality, macro superiority, cross-domain generalization, or production
readiness.
