# Changelog

All notable public changes are documented here. The project follows semantic versioning
for its Python API and artifact schemas while it remains research-alpha software.

## Unreleased

- Renamed the repository to `guarded-agentic-compaction`, matching the method name the
  paper defines. GitHub redirects the previous `agent-compaction` repository URL, so the
  URL printed in the published PDF continues to resolve. The documentation site moved to
  <https://rrahimi-uci.github.io/guarded-agentic-compaction/>; GitHub does not redirect
  project Pages, so the previous docs URL stops working.
- Kept the distribution name `agent-compaction`, the import path `agent_compaction`, and
  the `agent-compaction` console script unchanged. Renaming them would invalidate every
  checksum in the artifact and publication manifests and break the paper's reproduction
  commands for no user-visible benefit.
- Added `[project.urls]` so the distribution points at the renamed repository.

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
