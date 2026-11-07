# BIRD list-to-schema binder expressivity audit

**Development decision: NO_EXACT_BINDING_IN_TESTED_T_V1_FAMILY.** The current versioned GAC
binding library was tested against the sealed BIRD baseline's varying
`get_schema(table_names=...)` batches. The corrected question file, published
pilot, and earlier [schema-selection probe](../bird_schema_selection_probe/REPORT.md)
were hash-checked before use. No question, SQL, model response, schema content,
or fitted constant is copied here.

The observed input to the binder contained the entry question and evidence,
plus the preceding `list_tables` result. Across **36 cases in
9 databases**, depth-3 search over at
most 200 source paths found **no exact binding** for the
model-selected table lists
(`no_consistent_expression`). Excluding the one case that requested a table absent
from the preceding list left **35 cases** and
again found **no exact binding**
(`no_consistent_expression`). The same call found an identity binding for
the entire list of available tables in **36 cases**; this
positive control verifies that list-valued targets and the grouped-refit path
work (`expr`).

This is an exact reconstruction test of the current `T-v1` library, not a
test of whether a different selector could choose useful tables. The library
has fixed unary transformations and no operator that semantically compares
the entry question with each newly listed table. A new question-conditioned
selector would require a versioned method extension and its own leakage,
grouped-generalization, live-tool, continuation, and matched-control checks.
There was no provider call, new artifact,
matched final-answer arm, cost saving, or independent test.

Reproduce with the pinned corrected BIRD question file:

```sh
python paper/scripts/bird_binder_expressivity_audit.py --questions /path/to/corrected/dev_20251106.json
python paper/scripts/validate_artifacts.py --families bird_binder_expressivity_audit
```

The [machine-readable audit](report.json) retains the code and source hashes,
counts, search bounds, decisions, and limitations. CI checks those public
links and the claim boundary; re-running synthesis requires the external
corrected question file.
