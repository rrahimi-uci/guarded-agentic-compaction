# BIRD one-call continuation: provider-free gate

**Decision: the one-call prefix is mechanically feasible on the 36 exposed
development cases.** This is not a new final-answer result, an admitted GAC
artifact, an independent benchmark test or evidence of superiority over a
handwritten wrapper.

The historical [exploratory pilot](../adaptive_compiler_pilot/REPORT.md)
retained 36 baseline agent traces, all of which first called `list_tables`.
The previous [candidate validation](../adaptive_prefix_validation/REPORT.md)
produced a one-call program but no calibration groups or artifact. For the new
synthetic-continuation policy, we rebuilt that program from the same train/dev
traces under a new manifest. The program is byte-identical to the old one;
the old hard guard correctly rejects the new policy hash. The rebuilt candidate
remains research-only with **zero admitted artifacts**.

The [preflight report](report.json) accounts for all 36 fixed cases. For every
case, the new-policy guard, live program execution and induced verifier passed;
the `list_tables` result exactly matched the retained baseline's first tool
result; and the database file hash remained unchanged. A synthetic assistant
tool-call plus result matched the canonical shape of the baseline's first turn,
ignoring only the arbitrary call ID and empty response-only annotations. This
does not prove how a model will continue from the synthetic history. The
paid pilot must measure final answers and requests directly.

All 36 questions and their nine databases are reused, exposed development
material. The verification relies on the existing source-pinned corrected BIRD
release and the original baseline archive. No model call, fresh calibration,
independent test, new task selection or quality-selected retry occurred.
The exact program can also be written by hand, so its existence alone cannot
show automatic-compilation benefit.

With the pinned BIRD databases available locally, reproduce before any paid
attempt:

```sh
python paper/scripts/bird_one_call_matched_candidate.py
python paper/scripts/bird_one_call_continuation_preflight.py
```

The scripts hash the historical candidate, pilot seal/archive, source files and
database bytes. The [new-policy candidate](candidate.json) and [preflight
report](report.json) are included in the publication manifest. The subsequent
[matched development pilot](../bird_one_call_matched_pilot/REPORT.md) is
reported separately.
