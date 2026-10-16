# SEC provider-free preflight

The [frozen candidate frame](../../cohort/README.md) contains 700 distinct
CIKs from an archived SEC ticker response. The live acquisition inspected 697
candidates, retaining 520 complete issuer groups and recording 177 rejections
in `report.json`. The first selection attempt stopped with only 405/420 groups
after exact-10% hard-state stratification. The
[post hoc amendment](acquisition_amendment.json) treated 10% as a minimum and
filled the 15 ordinary-group shortfall from already qualified hard-state
groups, without changing the CIK list or fetching new SEC data. The corrected
offline replay retained 420 independent issuers, including 57 hard-state
groups (13.6%).

The pool holds SEC submissions, Company Facts, and selected facts from actual
filed XBRL instances. The pinned EdgarTools parser audit passed **420/420**
selected Company Facts observations; the deterministic exact oracle and
separately implemented gold constructor also passed **420/420** in the
three-domain provider-free validator. These are code-level checks over the
retained records. EdgarTools parses the same Company Facts response, and the
gold check is not independent human review of the filing or macro. The
three-domain [review bundle](../../review/three-domain-macro-review-materials.json)
has `approval_generated: false`. No model-provider calls or live agent study
were performed for this preflight.

The original raw SEC responses remain in the ignored local cache. With that
cache, the selected cases and audit can be reproduced without network access:

```bash
python -m benchmarks.acquire sec \
  --ciks paper/results/multidomain/cohort/sec-ciks.json \
  --minimum-groups 420 --offline --edgartools-audit \
  --cache /path/to/original-sec-cache \
  --out paper/results/multidomain/preflight/sec
```

The repository retains source URLs and SHA-256 digests so fresh acquisition
can be compared, but SEC endpoints may have changed since this pool was built.
The amended selection rule and convenience frame limit generalization claims.
