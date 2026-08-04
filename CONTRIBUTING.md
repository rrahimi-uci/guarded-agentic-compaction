# Contributing

Thanks for improving `agent-compaction`. Changes should preserve its fail-closed rule:
an optimizer may abstain, but it must never turn missing evidence into a live rewrite.

## Development

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev,agents,mlflow,figures]'
.venv/bin/python -m pytest
.venv/bin/python scripts/verify_release.py
.venv/bin/python -m build
```

Add focused tests for every behavior change. Safety-boundary changes should include a
fault-injection or mutation test. Benchmark changes must preserve grouped splits, frozen
manifests, negative results, and the `substrate` label.

Do not commit credentials, raw restricted traces, customer payloads, or generated virtual
environments. Describe public API or artifact-schema compatibility changes in the pull
request.
