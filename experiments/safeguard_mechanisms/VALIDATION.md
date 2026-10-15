# Validation and handoff

Completed locally on October 15, 2026, using the existing repository virtual
environment with this worktree's `src` on `PYTHONPATH`.

| Check | Result |
| --- | --- |
| `python -m pytest -o addopts='' -q paper/scripts/test_safeguard_mechanism_study.py` | 18 passed |
| `python -m pytest -o addopts='' -q` | 582 passed, 3 optional-data tests skipped; 193.54 seconds |
| `python paper/scripts/safeguard_mechanism_study.py prepare` | Sealed 408 disjoint issue groups, 576 held-out request cases; zero provider calls |
| Corresponding `run` | 2,880/2,880 arm evaluations completed; zero execution failures; zero provider calls |
| Corresponding `verify` | Complete deterministic candidate/calibration/arm/outcome/summary/report replay passed |
| `python paper/scripts/validate_artifacts.py` | 5,277 checks passed, zero failed |
| `python scripts/verify_release.py` | Passed; three existing checks requiring untracked `docs/` skipped |
| `python scripts/build_pages.py --output _site` | Passed; 9 pages, 32 paths |
| `python -m build --outdir /tmp/gac-mechanism-dist` | Source distribution and wheel built |
| `git diff --check` | Passed |

The artifact validator's generated historical `validation_summary.json` was
restored after validation. Published paper evidence, tables, production runtime,
and release configuration are unchanged. GitHub CI and reviewer state are
recorded on the pull request, separately from these local results. No human
review or independent gold attestation is claimed by this document.

The tests exercise one-component interventions, preservation of type/presence/
manifest/provenance/effect constraints, task-level omissions, harmless refusals,
shared response caps, counted speculative and fallback reads, empty sources,
group-level calibration support, retirement before test, retained failures,
complete outcome matrices, exclusive seals/attempts, and detection of tampering
even when an outcome file's stored digest has been updated.

The source audit inspected count and match-position errors against the pinned
comments; examples and limitations are recorded in [OBSERVED.md](OBSERVED.md).
The separate source oracle is not an independent human review. Provider spend
is exactly zero for this diagnostic; no billing estimate is needed. A future
live pilot is described but has not been implemented or executed by this PR.
