# Changelog

All notable public changes are documented here. The project follows semantic versioning
for its Python API and artifact schemas while it remains research-alpha software.

## Unreleased

## Gac-v0.0.1 — 2026-08-12

First public GitHub research-artifact release. This tag packages the validated
guarded-agentic-compaction 0.7.0 implementation together with its reproducible paper,
benchmark audit, HTML article, editable technical deck, evidence manifests, and the
GitHub Pages publication shelf. The release preserves the project's research-alpha
boundary: refusal, fallback, and claim limits remain part of the artifact rather than
being presented as production certification.

### Paper and publication artifacts

- **Retitled** to *From Traces to Guarded Programs: Evidence-Gated Compilation of
  Recurrent Agent Workflows*, across the article build, the conference build, the
  ICLR submission, the LinkedIn write-up, and both slide decks.
- Added `paper/ICLR/`, a condensed 9-page conference submission with its own style
  files: formal problem statement, four algorithms, an architecture diagram, a
  refusal-funnel table, and admission certificates.
- Renamed `paper/build/` to `paper/open_research/`. The compiled manuscripts live
  there; LaTeX auxiliaries stay ignored.
- Rebuilt the LinkedIn figures on an HTML/headless-Chrome pipeline. The previous
  hand-authored SVGs hard-coded line breaks with no text measurement and overflowed
  their containers in four of six images.
- Cited context-compression middleware (Headroom) in both bibliographies and in
  `docs/related-work-matrix.md`, and recorded the matching limitation: every
  reported reduction compares against an *uncompressed* baseline.
- Corrected the confidence budget in the manuscripts to `delta = 0.1`. That is the
  value the runs used and the one that yields the 92-group requirement recorded in
  `paper/results/admission_register.json`.

### Repository

- **`docs/` is no longer tracked.** It stays on disk and is partly generated
  (`experiments/analysis/report.py`, `experiments/live_run.py`,
  `scripts/build_html_report.py` all write into it). `scripts/verify_release.py`
  reports its three docs-dependent checks as SKIPPED on a clean checkout rather
  than failing or silently passing.
- `.gitignore` reorganized by category, with LaTeX auxiliaries ignored repo-wide.
- Removed superseded artifacts: a duplicate copy of an old paper build and two
  LinkedIn exports that had drifted to an older image set and title.

**Breaking:** the project is renamed from `agent-compaction` to
`guarded-agentic-compaction`, matching the method name the paper defines.

- Repository renamed. GitHub permanently redirects the previous repository URL, so the
  URL printed in the published PDF continues to resolve. The documentation site moved to
  <https://rrahimi-uci.github.io/guarded-agentic-compaction/>; GitHub does not redirect
  project Pages, so the previous docs URL stops working.
- Distribution renamed to `guarded-agentic-compaction`. The previous name was never
  published to PyPI, so no release is superseded and no alias is needed.
- Import path renamed to `guarded_agentic_compaction`. **Update imports:**
  `import agent_compaction as ac` becomes `import guarded_agentic_compaction as gac`.
- Console script renamed to `guarded-agentic-compaction`, with `gac` added as a short
  alias because the full name is 26 characters.
- Added `[project.urls]` pointing at the renamed repository.

The serialized schema namespace is deliberately **unchanged**. Every result artifact
records `"schema": "agent-compaction-*/vN"`, and those strings are recorded evidence
emitted by the runs that produced them: renaming the namespace in source would either
invalidate validation against 65 sealed result files or require rewriting the sealed
files themselves. `tracer_version`, `sdk_workflow_name`, and JSON Schema `$id` values are
unchanged for the same reason. A namespace migration is a versioned wire-format change,
not a rename, and is not attempted here.

## 0.7.0 — 2026-08

- Added guarded composite synthesis with continuation-pinned pre-model execution.
- Added the exact-risk measured-action portfolio and review-gated macro recommendation.
- Added OpenAI Agents SDK trace capture and guarded runtime integration.
- Added real-record GitHub studies, a fair pre-model manual comparator, and bounded
  official GEPA evaluation.
- Added revision-pinned NESTFUL, API-Bank, BFCL, ToolSandbox, tau, BrowseComp, ToolBench,
  AgentBench, GAIA, and SWE-bench dispositions without pooling unlike evidence.
- Removed MLflow from the dependency and runtime surface in favor of canonical atomic
  local Episode snapshots.
- Added the publication artifact, editable decks, experiment audit, and GitHub Pages site.

## Compatibility

Unknown, write-bearing, permissioned, streaming, hosted-tool, handoff, or incompatible
paths remain baseline/fallback boundaries. Schema or public API changes must be called out
in future entries.
