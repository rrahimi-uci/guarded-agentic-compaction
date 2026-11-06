# Adaptive comparison: source, grader and comparator preflight

Status: **NO-GO for confirmatory execution**. Provider/model calls: **0**. This is completed feasibility work, not a comparative performance result, new certificate, or sealed cohort.

## Verified source inventory

Both outer archives match the historical pinned SHA-256 values. Every nested database archive and all 80 extracted SQLite databases (11 dev, 69 train) were matched byte-for-byte by hash. Missing training databases were extracted only from the verified local archive. Post-query hashes are unchanged. No archive or database is committed; public question IDs, dispositions and hashes are retained.

The prior-use screen remains conservative and limited to retained BIRD study JSON. A question not selected by that screen is not necessarily unseen by the author, the assistant, or the evaluated model's pretraining.

| Split | Screened-in questions | Gold executes | Other gold dispositions | Prior gold-cache entries |
| --- | ---: | ---: | --- | ---: |
| dev | 722 | 720 | resource_limit: 1, timeout: 1 | 278 |
| train | 5,094 | 4,849 | resource_limit: 27, sql_error: 211, timeout: 7 | 1,564 |

A separate content-overlap screen found these screened-in IDs with an exact whitespace-normalized question match to a previously selected ID in the same database: dev: []; train: [1845, 9161]. Exclude these from a future fresh cohort while retaining them in this audit's original denominator. Paraphrases, global author inspection and model-training exposure are not resolved by exact matching.

Every screened-in ID remains in the report, including failures. Gold execution uses a 30-second SQLite VM deadline, 100,000-row and 32 MB returned-payload caps. Resource limits and failed gold are unavailable labels, not zero-error successes. These are execution checks, not a manual audit of gold semantics or independence.

## Corrected dev release

The official release pinned at `3c11fb193e5439b338e23677fa0aae11e8b85db9` changes 619 of 1534 records; 319 changed IDs are in the screened-in pool. SQL text changes on 452 records. Not every field change denotes a gold error: some questions/evidence/difficulty also change.

Source: [official corrected release](https://huggingface.co/datasets/birdsql/bird_sql_dev_20251106). Its dataset card tells existing users to retain their downloaded databases and update the questions. The source snapshot is pinned locally; no old outcome has been relabelled against new questions.

Corrected-release gold execution over every originally screened-in dev ID: ok=720, timeout=2. This still does not certify semantic correctness. IDs 0–17 were visible in the official web viewer during source discovery; record that inspection separately from historical agent calls. Do not call those IDs blinded to this audit.

Decision: pin one release and revalidate its task contracts before discovery. Keep previously used IDs excluded even when their text changes; a new release name does not erase prior exposure. The training release also needs semantic/provenance review.

## Grader boundary

The historical driver and the inspected official BIRD evaluator use unordered sets of rows. That ignores multiplicity and ordering; the historical driver also treats empty results of different column counts as equal. Historical scores are preserved.

The new prospective kernel preserves row shape and offers explicit set, bag (duplicate-sensitive), and sequence contracts. Tests cover duplicates, ordering, NULL, numeric equality, empty shape, invalid SQL, timeouts through fetching, row/byte limits, writes, ATTACH, temporary tables and extension loading. It does not infer task semantics from generated SQL. Order requirements, ties and numeric tolerance must be annotated/frozen independently before this becomes a task-quality oracle.

SQLite authorizers and immutable read-only files constrain SQL; they are not a sandbox for arbitrary generated Python. A live compiler needs a separate isolated executor.

## Named compiler feasibility

Agent JIT checkout: `ad6df6b8d19573efa4a1155951c6a838f6b1b4d7` ([official repository](https://github.com/agent-jit-compilation/agent-jit-compilation)). The unmodified static checker/ranker accepted the valid and redundant programs, rejected missing list/schema prerequisites and a wrong argument type, and ranked the cheaper valid program first. It also accepted a contract-valid wrong-answer program: static contract validity is not task correctness.

This six-program fixture uses synthetic return schemas, not the full BIRD tool payloads. Upstream observation tools are omitted from callable definitions; the fixture maps list_tables as listItems. A live port must separately establish its observer, equal-information tool schema, adaptive inference, isolated runtime, budget/failure accounting and faithful candidate-generation policy. The browser runner cannot simply execute SQLite tools. Native browser reproduction and a SQL adaptation must be labelled separately.

The attempted EvoC2F anonymous code endpoint returned HTTP 401 (`not_connected`); no EvoC2F implementation was inspected and no reproduction is claimed. Agent JIT is the concrete next implementation candidate, not an implemented live baseline.

## Endpoint and power decision

Historical compiled final-answer errors (all scheduled questions in admitted families):

- dev: 53/150 (35.3%).
- train: 228/630 (36.2%).

These observations do not rule out a lower-risk selective subset, but they give no basis for assuming a positive-coverage 5% absolute final-error certificate. A fresh study must distinguish absolute task failure, replay mismatch, and paired quality loss relative to the unchanged agent. A quality noninferiority claim is not an absolute success guarantee.

Illustrative three-contrast design (familywise alpha .05; IID paired groups; assumed gain .04/loss .01):

| Test groups | Exact superiority power | Conservative 2pp NI power at loss .01 | Six-arm test episodes |
| ---: | ---: | ---: | ---: |
| 145 | 11.30% | 0.00% | 870 |
| 312 | 40.87% | 18.05% | 1,872 |
| 900 | 95.51% | 58.74% | 5,400 |
| 1200 | 99.13% | 68.21% | 7,200 |
| 1800 | 99.98% | 90.00% | 10,800 |

These are per-contrast sensitivities, not achieved effects, joint power, or an accepted 2pp margin. The largest prior-screened database has only 312 questions before splitting or gold validation. It cannot support the illustrated 900+ test groups plus discovery/calibration. Pooling databases changes the population and requires a prospective weighting/clustering design. Cost/latency inference needs a variance pilot and error allocation of its own. No final sample size is sealed.

## Next decision

Do not launch the old per-database confirmatory design. Develop an explicitly pooled, release-pinned benchmark comparison or acquire enough new task groups; validate semantic task contracts; implement and test the live Agent JIT port; then set the quality margin, sampling unit, candidate/threshold multiplicity, cost analysis and fixed sample size before presenting a bounded discovery pilot budget. Any unachievable certificate must be reported as unavailable, not repaired by filtering on baseline correctness or collecting until it passes.

## Reproduction

From the repository root:

```sh
python paper/scripts/adaptive_source_preflight.py build  # optional pinned BIRD cache; no provider
python paper/scripts/adaptive_source_preflight.py verify # shipped metadata only
python paper/scripts/audit_bird_revision.py              # pinned corrected JSON in local cache
python paper/scripts/adaptive_comparison_design.py
python paper/scripts/audit_bird_content_overlap.py
python paper/scripts/render_adaptive_preflight.py
pytest paper/scripts/test_adaptive_sql_grader.py paper/scripts/test_adaptive_preflight.py
```

For the upstream probe, clone the official repository, check out the recorded commit, run `uv sync --locked` there, then use its `.venv/bin/python` to run `paper/scripts/probe_agent_jit_sql.py /path/to/checkout`. No browser extra, provider key or model request is used. Regular repository CI reads the retained probe; it does not install or execute upstream code.
