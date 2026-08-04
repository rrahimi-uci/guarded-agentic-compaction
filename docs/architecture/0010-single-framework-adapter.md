# ADR 0010 — One framework adapter, plus a dependency-free store

**Status:** accepted
**Supersedes:** part of [ADR 0001](0001-mlflow-and-sdk-as-backends.md)

## Context

ADR 0001 decided that the compiler owns a typed IR and that MLflow and the OpenAI Agents
SDK are *adapters* under `capture/`. That decision was right and is unchanged. What did not
survive contact with the evidence is the MLflow adapter itself.

By the time the paper was written, the MLflow backend was used by nothing: no experiment, no
demonstration, and none of the paper's three evidence tiers. It was 338 lines, of which the
only functions anything imported were the twelve lines of `read_jsonl`/`write_jsonl` — which
are pure `json` and have no relationship to MLflow at all. Because those two lived in a
module named `mlflow_adapter.py`, the public entry point used by every README example, the
CLI, and every reproduction command appeared to depend on an optional tracing platform.

Keeping it also had a running cost: an `mlflow>=3.14,<4` extra to hold compatible, a
version-pin test that existed precisely because a major bump would break it, and a release
matrix entry for code with no in-repo consumer.

## Decision

1. `read_jsonl`/`write_jsonl` move to `capture/jsonl.py`, which imports only the standard
   library and the IR.
2. The MLflow adapter, its optional extra, and its pytest marker are removed.
3. The OpenAI Agents SDK remains the only framework adapter.
4. The local store remains an immutable snapshot abstraction: strict canonical JSON,
   atomic replacement, streaming validation, duplicate-ID rejection, and line-attributed
   failures. It does not grow into a remote experiment tracker.

## Consequences

**What is preserved.** The IR decision of ADR 0001 is untouched: nothing in `graph/`,
`grc/`, `tgws/` or `evaluation/` imports any framework, and a test now asserts that
`capture/jsonl.py` contains no `import mlflow`, `import agents`, or `import openai`. A
round trip through JSONL still demonstrates that the IR is self-contained — an episode can
be written and rebuilt with no tracing platform installed, so the input representation is
not defined by a vendor.

**What is weakened, and this should be stated plainly.** MLflow was the only adapter that
translated a *foreign* trace model into the IR. A JSONL round trip proves the IR is
serializable; it does not prove the IR is expressive enough to receive a second vendor's
trace shape. Framework-neutrality is therefore now supported by the IR's design and by the
absence of framework imports above `capture/`, and no longer demonstrated by a second
independent mapping. The paper's wording was corrected to match.

**How to reverse.** Adding a second adapter is additive: implement translation into
`Episode` under `capture/`, add an optional extra, and add a round-trip test asserting the
seven application-owned facts survive. Nothing in the compiler needs to change — which is
the property ADR 0001 was protecting.

The full use analysis, migration boundary, and validation matrix are recorded in the
[MLflow removal review](../mlflow-removal-report.md).
