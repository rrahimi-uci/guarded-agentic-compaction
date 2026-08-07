# Contributing

Thanks for improving `guarded-agentic-compaction`. Changes should preserve its fail-closed rule:
an optimizer may abstain, but it must never turn missing evidence into a live rewrite.

Useful contribution areas include trace adapters, conservative compiler checks, benchmark
contracts, perturbation suites, runtime controls, documentation, and reproducibility.
Start with a small issue that states the intended evidence class and safety boundary.

## Development

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev,live,figures]'
.venv/bin/python -m pytest
.venv/bin/python scripts/verify_release.py
.venv/bin/python paper/scripts/validate_artifacts.py
.venv/bin/python scripts/build_pages.py --output _site
.venv/bin/python -m build
```

`docs/` is **untracked** (see `.gitignore`): part of it is generated, and it is kept
out of version control by choice. It is still the right place for engineering notes,
and several tools write into it, so regenerate it locally before relying on it:

```bash
.venv/bin/python experiments/analysis/report.py     # docs/results.md
.venv/bin/python scripts/build_html_report.py       # docs/agent-compaction-report.html
```

Because it is untracked, do not add repository links that point into `docs/` —
`scripts/verify_release.py` fails on dangling relative links, and those links would
404 for anyone browsing the repository. Reference local paths as inline code instead.

Paper artifacts live in `paper/`: sources in `paper/tex/`, compiled manuscripts in
`paper/open_research/`, and the conference submission in `paper/ICLR/`. After changing
anything the publication manifest covers, re-run:

```bash
.venv/bin/python paper/scripts/finalize_manifest.py
.venv/bin/python paper/scripts/validate_artifacts.py
```

Add focused tests for every behavior change. Safety-boundary changes should include a
fault-injection or mutation test. Benchmark changes must preserve grouped splits, frozen
manifests, negative results, and the `substrate` label.

Do not commit credentials, raw restricted traces, customer payloads, or generated virtual
environments. Describe public API or artifact-schema compatibility changes in the pull
request.

## Engineering standards

- Keep the compiler framework-neutral; adapters translate into the typed Episode IR.
- Treat unknown effects, permissions, provenance, freshness, runtime position, and
  compatibility as rejection conditions.
- Preserve partition isolation. Never pool tenants, principals, repositories, or policy
  versions merely to raise support.
- Keep synthesis bounded and inspectable. New DSL operators need semantics, interpreter
  coverage, serialization tests, and adversarial examples.
- Report observed, recomputed, environment-gated, and proposed results separately.
- Never relabel simulator or fixture evidence as a real-world demonstration.

## Benchmark contract

A compiler benchmark must expose task boundaries, ordered calls, arguments, observations,
effects, and a replayable outcome contract. A dataset with tasks or gold calls but no
observations may support planning or structural evaluation; it is not silently promoted to
a trace-complete compiler substrate. Pin revisions and licenses, preserve upstream
denominators, group related samples, and retain rejection results.

## Pull requests

Explain the behavioral change, exact validation commands, compatibility implications, and
whether refusal, fallback, isolation, permission, or effect behavior can change. Generated
paper artifacts must be rebuilt from their maintained scripts. Do not hand-edit generated
tables, figures, manifests, or publication decks.

Conduct expectations are in [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Report
vulnerabilities privately as described in [SECURITY.md](SECURITY.md).
