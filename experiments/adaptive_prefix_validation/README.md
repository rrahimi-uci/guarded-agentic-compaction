# Adaptive prefix and comparator validation

This provider-free follow-up resolves two feasibility questions raised by the
exploratory SQL pilot. It does not execute a new final-answer comparison or admit
a GAC artifact. All original pilot outcomes, source files, seals, exclusions and
the shared campaign ledger remain unchanged.

1. Run every selected pilot SQL program with the unmodified pinned Agent JIT
   executor inside the isolated Docker boundary. Compare it with a separate
   reference harness using the same executor and identical recorded RPC responses.
2. Reconstruct all 36 baseline traces from the retained archive. Keep the original
   27/9 train/development split and all incorrect answers. Examine a posthoc
   development setting with a one-call window and minimum saving of one request.
3. Inventory remaining source IDs and recompute the existing exact paired power
   sensitivities. Do not choose a favorable test size or label these calculations
   as experimental evidence.

Results and limitations are in the
[report](../../paper/results/adaptive_prefix_validation/REPORT.md). The original
two-call candidate's failure is retained, including the inability to ground the
adaptive choice of schema tables. The one-call program leaves that choice with the
model. Its program, hard guard, verifier, training groups, configuration, source
hashes and development replay dispositions are retained in `candidate.json`.
It is a research candidate, not an active registry artifact or execution seal.

## Reproduction

Ordinary CI needs neither an API key nor a database download. It reconstructs the
candidate from the checked-in archive, checks evidence hashes and recomputes power
calculations. Full SQL parity additionally requires the existing pinned BIRD cache,
Docker image and unmodified upstream checkout described in the pilot README.

```sh
.venv/bin/python paper/scripts/freeze_adaptive_prefix.py
.venv/bin/python paper/scripts/validate_adaptive_sql_programs.py /tmp/gac-agent-jit-preflight
.venv/bin/python paper/scripts/adaptive_prefix_readiness.py
GAC_TEST_PILOT_DOCKER=1 GAC_UPSTREAM_CHECKOUT=/tmp/gac-agent-jit-preflight .venv/bin/python -m pytest paper/scripts/test_adaptive_prefix_validation.py
```

The SQL bridge mounts only the three hash-checked upstream executor modules and
one worker. Generated Python runs as an unprivileged user in a networkless,
read-only, resource-bounded container. SQL stays in the parent process and is
read-only against hash-pinned databases. API credentials and database files are
never mounted. Both harnesses implement only the documented SQL result interface,
not all of Pydantic or native browser behavior. Upstream attribution remains in
[`Agent-JIT-LICENSE.txt`](../adaptive_compiler_pilot/Agent-JIT-LICENSE.txt).

The lone retained runtime-inference response is a fixed fixture. It is not a fresh
model response or evidence of inference-prompt equivalence. A missing fixture is
explicitly recorded; this validator never fills it with a paid request. Budget-stop
exceptions propagate out of the reusable bridge rather than becoming recoverable
errors inside generated code.

Changes to these validation implementations require regeneration of their new
reports and publication manifest. Do not change the sealed historical pilot to
make its results agree with this corrected executor.
