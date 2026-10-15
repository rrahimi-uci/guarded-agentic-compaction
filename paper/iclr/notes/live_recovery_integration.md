# October 15 live-recovery manuscript integration

## Scope and scientific interpretation

The current ICLR source and PDF now incorporate the completed comparison from
PR #81 and the preceding fresh-record/mechanism studies (PRs #78–80). The local OpenReview abstract is synchronized as well. Main-text
results and Appendix I distinguish the ordinary-response scope-guard gain from
the unresolved completeness-check benefit, and report cost, tool-count, and
quality tradeoffs. The earlier drift findings remain negative. No experiment
was rerun against a provider, and no sealed protocol, driver, checkpoint, or
analysis file was edited. Historical six-study/810-episode totals are unchanged
and explicitly scoped to those studies.

The empirical intervention uses hand-specified contracts and constructed
requests; it does not establish end-to-end contract discovery, a learned risk
frontier, quality equivalence, or generalization of guard benefits across
models and workloads. All four timeouts remain unsuccessful scheduled attempts.
The 72 confirmation and 24 replication issue groups remain separate; intervals
resample issues, not correlated request variants, and are descriptive/unadjusted.
The historical review score is not replaced by an asserted acceptance forecast.

## Reproduction and checks

Run from the repository root with its Python environment and `PYTHONPATH=src`.
Tectonic 0.15.0 is the installed compiler used here; the plugin's bundled binary
was absent. No TeX distribution was installed.

```bash
(cd paper/iclr && tectonic --keep-logs --keep-intermediates --outdir build main.tex)
python -m pytest
python scripts/verify_release.py
python scripts/build_pages.py --output _site
python -m build
python paper/scripts/finalize_manifest.py
python paper/scripts/validate_artifacts.py
git diff --check
```

The sealed completion analysis was independently regenerated into a temporary
output directory and compared for exact JSON equality, without changing the
retained evidence:

```python
import json, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, "paper/scripts")
import complete_live_recovery as study
with tempfile.TemporaryDirectory() as directory:
    output = Path(directory)
    for name in ("seal.json", "checkpoint.json"):
        shutil.copyfile(study.OUT / name, output / name)
    assert study.analyze(output) == json.loads(
        (study.OUT / "analysis.json").read_text()
    )
```

This passed the prospective seal, source regrading, tool-output digest, cost,
and paired-analysis checks. Accuracy/resource table cells and all six
confirmation contrasts were checked against the retained JSON; the cited
experiment and script paths resolve. The completed checkpoint retains SHA-256
`fc207e0292ed1c967fd01d1a72ca329dcbf88e628937e6f89e7a83077a317600`.
The publication manifest includes all four new study directories and their
paper-side sources.

Build and validation results are recorded in the PR. The rebuilt PDF has
46 pages including references and appendices; Section 8 ends on page 10 under
the repository's existing revision target. The PDF renders “Anonymous authors,”
has no author metadata, embeds regular/bold/italic Times-compatible fonts, and
has no undefined references/citations or overfull boxes. Visual inspection
covered the abstract, main result, discussion/conclusion, new appendix, tables,
and evidence index. Initial-submission formatting remains a separate nine-page
target; this change preserves the existing ten-page revision configuration.

## Publication boundary

This change updates the canonical `paper/iclr/` manuscript and its tracked
`build/main.pdf`. The older long-form wrappers under `paper/tex/`, their PDFs,
the HTML article, presentation deck, and hosted downloads were not regenerated
or deployed as part of this manuscript revision. The anonymous supplementary
archive remains a separate pre-upload task, as stated in the manuscript. The
publication manifest binds the retained versions of all included artifacts;
it does not imply that every companion presentation incorporates these results.
No runtime, configuration, migration, package-version, or deployment behavior
changes. Reverting this manuscript PR restores the prior presentation without
altering the study evidence.
