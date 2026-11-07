# AppWorld batched baseline competence pilot

This is an **adapted, exposed-development** AppWorld study. It tests whether a
batched API agent can achieve enough independently graded task success to be a
credible comparator for a later GAC quality–cost study. It does not execute
GAC or claim native leaderboard performance. See the [retained findings](../../paper/results/appworld_batched_competence/REPORT.md).

The pinned worker image is
`sha256:d9e0e53e548439321832c2f3a2b424e2f6ce77436bfae4e5ec22e1f2da8a4718`.
For each run, the isolated worker performs two supervisor reads and nine logins
before exposing task context. This changes native AppWorld's entry contract;
the same 11 setup calls are charged to every case. The agent can call only
public AppWorld APIs in ordered batches of 1–8. It supplies `AUTO` for required
access tokens, which the worker binds to its authenticated local session. The
worker saves task state and applies AppWorld's official independent grader.
Reference calls are used only in provider-free controls and never sent to the
agent model.

The V1 runner was frozen before paid execution. After V1 failed the development
competence gate, V2 was frozen as a separate amendment with a stronger model and
an explicit task-completion reminder. Both retain all 12 fixed task outcomes.
The public seals record source and input hashes, prompt, model, tool schema,
limits and budget. Complete raw records and terminal logs live in the local
ignored cache and in round-trip-verified encrypted bundles. The bundle's
encryption is supplied by the pinned upstream distribution utility; do not
publish extracted protected inputs, credentials, reference answers or traces.

With the pinned image, protected source cache, Python dependencies and a
locally configured API key, the commands are:

```sh
python paper/scripts/appworld_batched_competence.py freeze
python paper/scripts/appworld_batched_competence.py controls
python paper/scripts/appworld_batched_rpc_controls.py freeze
python paper/scripts/appworld_batched_rpc_controls.py run
python paper/scripts/appworld_batched_rpc_controls.py report
python paper/scripts/appworld_batched_competence.py run
python paper/scripts/appworld_batched_competence.py export
python paper/scripts/appworld_batched_competence_v2.py freeze
python paper/scripts/appworld_batched_competence_v2.py run
python paper/scripts/appworld_batched_competence_v2.py export
```

The freeze commands refuse to overwrite an existing version, and each paid
request reserves against the same fail-closed $300 ledger. These commands are
the original sequence, **not** an instruction to rerun the sealed attempts.
Provider-free source and boundary tests can run without the protected cache:

```sh
python -m pytest -q paper/scripts/test_appworld_batched_competence.py paper/scripts/test_sol_campaign_budget.py
```
