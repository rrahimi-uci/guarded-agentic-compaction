# BIRD dependent schema-read feasibility probe

**Development decision: no paid matched arm for the tested selectors.** This
provider-free posthoc audit inspects the already exposed 36-case BIRD baseline
in the [sealed matched pilot](../bird_one_call_matched_pilot/REPORT.md). It
verifies the corrected public question-file hash, the published raw archive
and pilot seal, and every baseline record hash before counting. No question,
evidence, SQL, tool result, model response or protected database content is
copied into this report.

All **36/36** baseline traces opened with
`list_tables` followed by `get_schema`; the schema call occupied the second
model request in **36/36**.
The baseline selected **79** table
occurrences from **256** listed occurrences
(median **2** selected versus
**7** listed per case). It answered
**28/36** development questions correctly.
In **1** case, its schema request
included **1** table name absent
from the immediately preceding listing; a literal selector limited to listed
names cannot reproduce that request.
This exposes at most one *additional* model-request boundary beyond the
already tested one-call `list_tables` prefetch; it is not an executed saving.

The deliberately simple literal-name rule selects tables whose full names
occur case-insensitively in the entry question or evidence. It selects at
least one table in **26/36** cases,
matches the entire baseline-selected set in **10/36**,
and recovers **35/79** selected-table
occurrences. It has no safe behavior when it selects no table. A proposed
`get_schema` call for *all* listed tables would match the baseline's selected
set in only **1/36** cases
and request **256** table schemas versus
**79** in the observed baseline.
That all-table path may change continuation quality and token cost; neither
path was executed or evaluated on final answers.

These observations do not prove that no semantic selector could work. They
show that the specific literal rule is too weak and that fetching every schema
is a different, potentially expensive context. Both rules are equally
available to a handwritten workflow. The exposed cases cannot serve as fresh
calibration or independent evaluation of a tuned selector. There is no new
admitted GAC artifact, matched comparison, quality--cost claim, or charge to
the shared $300 API budget. The paper's development-gate conclusion remains
unchanged.

Reproduce with the pinned corrected question file and retained archive:

```sh
python paper/scripts/bird_schema_selection_probe.py \
  --questions /path/to/corrected/dev_20251106.json
python paper/scripts/validate_artifacts.py --families bird_schema_selection_probe
```

The exact baseline record hashes and source versions are recorded in the
referenced pilot seal, report and [machine-readable probe](report.json).
CI can check their published hash links and this report's claim boundary;
recomputing literal matches also needs the pinned external question file.
