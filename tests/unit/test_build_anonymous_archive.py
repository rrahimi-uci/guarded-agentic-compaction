"""Guards for the anonymous supplementary-archive builder."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "paper/scripts/build_anonymous_archive.py"


def _module():
    spec = importlib.util.spec_from_file_location("build_anonymous_archive", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_scrub_replaces_every_identifying_token() -> None:
    mod = _module()
    text = (
        "see https://github.com/rrahimi-uci/guarded-agentic-compaction and "
        "https://rrahimi-uci.github.io/guarded-agentic-compaction/ by Reza Rahimi (JazzX AI) "
        "<reza.rahimi@example.com> at /Users/rezarahimi/Documents/GitHub/personal/x/paper/results/a.json"
    )
    cleaned = mod.scrub_text(text.encode("utf-8"))
    assert not mod.IDENTIFYING.search(cleaned), cleaned
    assert b"/ARCHIVE_ROOT/paper/results/a.json" in cleaned
    assert b"github.com/ANONYMIZED/guarded-agentic-compaction" in cleaned


def test_scrub_leaves_binary_bytes_alone() -> None:
    mod = _module()
    blob = b"\xff\xfe\x00rahimi\x80"
    assert mod.scrub_text(blob) == blob


def test_tracked_selection_excludes_identifying_and_untracked_material() -> None:
    mod = _module()
    files = set(mod.tracked_files())
    assert files, "git ls-files returned nothing"
    for forbidden in ("README.md", ".env", ".env.example", "docs/README.md",
                      "paper/iclr/main-final.pdf", "scripts/build_pages.py"):
        assert forbidden not in files, forbidden
    assert not any(path.startswith((".github/", "paper/open_research/", "paper/arxiv/",
                                    "paper/linkedIn_article/", "benchmarks/explorer/", ".claude/"))
                   for path in files)
    for required in ("pyproject.toml", "conftest.py", "paper/scripts/validate_artifacts.py",
                     "paper/iclr/main.tex", "paper/results/datasets/github_issues/source_manifest.json",
                     "src/guarded_agentic_compaction/__init__.py"):
        assert required in files, required


def test_author_tokens_are_a_strict_subset_of_identifying_pattern() -> None:
    mod = _module()
    for token in (b"rezarahimi", b"reza.rahimi", b"rrahimi-uci", b"JazzX"):
        assert mod.AUTHOR_TOKENS.search(token) and mod.IDENTIFYING.search(token)
    # A third-party public handle that merely contains the surname is allowed only in the
    # byte-pinned upstream snapshot, never elsewhere.
    assert mod.IDENTIFYING.search(b"afshinrahimi/mmner")
    assert not mod.AUTHOR_TOKENS.search(b"afshinrahimi/mmner")
