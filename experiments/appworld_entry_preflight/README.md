# Common authenticated entry: provider-free development preflight

This follows the interrupted AppWorld pilot in PR #104. It changes the proposed
entry contract explicitly: every arm would receive the same actual authenticated
state after the same measured setup. Login remains a write barrier. No compiler
catalog is relaxed and no model is invoked here.

The unchanged 12 exposed training scenarios are inventoried with their official
reference programs. Reference/test material stays in isolated trusted control code,
never in an agent prompt or GAC training trace. The first instrumentation version
tried to hash implementation source inside AppWorld's execution sandbox, which
correctly blocked it. All 12 failures and their frozen sources remain retained.
The amended version hashes source only after sandbox execution. All 12 references
then pass; no task, answer, grading assertion or sandbox restriction changed.

A separately frozen common-entry worker loads no full ground truth. It reads the
public supervisor profile and account passwords, then logs into every publicly
exposed app that offers login, in sorted order. Phone uses the profile phone number;
other apps use email. All nine apps are initialized for every task, for 11 setup API
calls. No reference solution selects which apps to initialize. Both future arms must
receive the same setup outputs, costs and starting state.

The host supplies known public reference calls as isolated controls. It removes
only the two supervisor reads and authentication calls already performed by common
setup, binds access tokens from the actual new entry, and retains task writes and
completion. The worker rejects private APIs and reserved Requester arguments,
saves state explicitly, closes the environment, and uses the official independent
saved-state grader. These are reference controls, not model continuations.

For each of 12 scenarios, the sealed controls are:

- A known-correct public sequence: the official nonempty test suite must pass.
- Empty interaction and unsupported completion: the official suite must fail.
- Two fixed song-library pages and two fixed playlist-library pages: successful
  list results and byte-identical saved database state before and after each probe.

All 60 checks passed. The common entry is validated only for these controls and
pinned bytes. State equality is a sampled diagnostic, not a proof covering every
API parameter or hidden effect. Source inspection includes the endpoints and their
authentication/retrieval/serialization helpers. The probe scope fixes page indices
0 and 1, default query/filter/sort; the general compiler effect catalog is unchanged.

The reference inventory has 701 API calls across 12 tasks, ranging from 8 to 145.
Nine reference sequences exceed the former 24-model-request limit, and seven exceed
its 48-API limit. Reference lengths are not lower bounds on possible solutions and
must not be equated with model requests. They justify reassessing the agent interface,
context policy and caps in a separately sealed competence pilot.

Posthoc reference inspection identifies three scenarios starting with two song-library
pages and three starting with two playlist-library pages after common setup. These
are hypotheses for useful application-data read prefixes. They are not model-mined
families, automatically synthesized programs, calibration groups or test outcomes.
A compiler must discover and validate its own candidate from actual model traces.

## Reproduction and evidence

The image, source hashes, task IDs, original failed instrumentation and amended
records are retained in the [report](../../paper/results/appworld_entry_preflight/REPORT.md).
The compatible image and upstream revision are inherited from PR #104. No live
network, host credentials, provider key, or Docker socket enters a worker. Controls
run serially in disposable read-only containers with bounded resources and writable
temporary state. No existing attempt is overwritten or retried.

```sh
.venv/bin/python -m pytest -o addopts='' -q paper/scripts/test_appworld_entry_preflight.py
```

The source inventory and entry controls each have `freeze` and `run` commands in
`paper/scripts/appworld_entry_preflight.py` and `paper/scripts/appworld_entry_controls.py`.
They need the pinned local image/data and historical cache. A fresh reproduction
must use a separate output directory and retain its own provenance. Do not overwrite
existing seals or reset campaign accounting. The original instrumentation source
exists inside the encrypted bundle; current source corresponds to its amendment.

`export_appworld_entry_preflight.py` publishes structural metadata and verifies an
upstream encrypted bundle round trip. Decrypted source, task/reference content,
credentials and API results must not be redistributed as plaintext. Ordinary CI
checks public aggregates, source/bundle hashes and offline boundary tests.

## Next experiment gate

Design a baseline-only competence pilot before any compiler ranking: identical
common setup, explicit API/documentation interface, a context policy that preserves
needed observations, fixed call/time limits informed by the reference inventory,
independent final-state grading, no retries and all scheduled outcomes retained.
Freeze the cohort and numeric local spending allocation within the existing $300
campaign cap before the first call. Do not select tasks after seeing model success.

If the baseline remains near floor, improve the common agent or narrow the task
before comparing compilers; version each development attempt. If it is competent,
collect genuine model traces and test whether the hypothesized prefixes recur and
are grounded. Only then freeze the matched compiler/handwritten/support-only arms.
Fresh unfiltered calibration, independent grouping, learned-score comparisons and
final testing remain separate requirements. This preflight makes no new paper
performance, certificate, maintenance-benefit or acceptance claim.
