# Changelog

All notable public changes are documented here. The project follows semantic versioning
for its Python API and artifact schemas while it remains research-alpha software.

## Unreleased

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
