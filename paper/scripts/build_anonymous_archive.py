"""Build the anonymous supplementary archive for the ICLR 2027 submission.

The archive holds the tracked sources, protocols, retained result files, scripts,
and paper sources needed to regenerate every provider-free number in the paper,
with a checksum manifest and a reviewer README. It is assembled from ``git
ls-files`` (so ignored files, credentials, and caches can never enter), copied to
a staging directory, scrubbed of author-identifying strings, verified byte by
byte against the identifying patterns, and zipped. The zip is written outside
the tracked tree (``paper/iclr/build/`` is git-ignored except ``main.pdf``).

Usage: ``python paper/scripts/build_anonymous_archive.py [--out PATH]``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "paper/iclr/build/gac-iclr2027-supplementary.zip"

# Tracked paths to include (prefixes) and to exclude (prefixes or suffixes).
INCLUDE_PREFIXES = (
    "src/", "tests/", "demos/", "paper/scripts/", "paper/results/", "paper/supplementary/",
    "paper/iclr/", "benchmarks/", "experiments/", "configs/", "scripts/", "conftest.py",
    "pyproject.toml", "CHANGELOG.md", "LICENSE",
)
EXCLUDE_PREFIXES = (
    "paper/iclr/template/", "paper/iclr/main-final.pdf",
    "benchmarks/explorer/", "paper/results/slide_generation.json",
    # Site-publishing tooling: not part of the evidence and carries the public repository URLs.
    "scripts/build_article_page.py", "scripts/build_benchmark_explorer.py",
    "scripts/build_paper_page.py", "scripts/build_pages.py",
    # The builder and its test spell out the identifying tokens they scrub for.
    "paper/scripts/build_anonymous_archive.py", "tests/unit/test_build_anonymous_archive.py",
)
EXCLUDE_SUFFIXES = (".pptx", ".pyc")

# Identifying strings. Every file in the archive is scanned for these after scrubbing.
IDENTIFYING = re.compile(rb"(?i)rahimi|rrahimi|jazzx|reza\.rahimi|rezarahimi|leila|jalali")
# Byte-pinned upstream dataset snapshots are third-party public data that cannot be edited
# (their sha256 is pinned in source_manifest.json and checked by the validator). They are
# scanned with the author-specific tokens only, so that an unrelated public GitHub handle
# containing a common surname does not block the build, and their pin is re-verified.
UPSTREAM_SNAPSHOT_PREFIX = "paper/results/datasets/"
AUTHOR_TOKENS = re.compile(rb"(?i)rezarahimi|reza\.rahimi|reza rahimi|rrahimi|jazzx")

# Deterministic rewrites applied to text files before the scan. Each maps an
# identifying token to a neutral placeholder without changing code paths that the
# regeneration commands depend on.
SCRUBS = (
    (re.compile(r"/Users/rezarahimi/[^\s\"']*?(?=/paper/|/src/|/benchmarks/|\"|'|\s)"), "/ARCHIVE_ROOT"),
    (re.compile(r"/Users/rezarahimi"), "/ARCHIVE_ROOT"),
    (re.compile(r"github\.com/rrahimi-uci/guarded-agentic-compaction"), "github.com/ANONYMIZED/guarded-agentic-compaction"),
    (re.compile(r"rrahimi-uci\.github\.io/guarded-agentic-compaction"), "ANONYMIZED.github.io/guarded-agentic-compaction"),
    (re.compile(r"rrahimi-uci"), "ANONYMIZED"),
    (re.compile(r"Reza Rahimi"), "ANONYMIZED AUTHOR"),
    (re.compile(r"JazzX AI|Jazzx AI|jazzx\.ai|JazzX|Jazzx|jazzx"), "ANONYMIZED AFFILIATION"),
    (re.compile(r"reza\.rahimi@[A-Za-z0-9.-]+"), "anonymized@example.org"),
    # The withdrawn HMDA study's independent macro reviewer is a colleague of the author;
    # naming them in a double-blind supplement could identify the authors.
    (re.compile(r"Leila Jalali"), "ANONYMIZED REVIEWER"),
    (re.compile(r"\bLeila\b"), "ANONYMIZED REVIEWER"),
    (re.compile(r"\bJalali\b"), "ANONYMIZED REVIEWER"),
)
TEXT_SUFFIXES = {".py", ".md", ".tex", ".bib", ".sty", ".bst", ".json", ".toml", ".yaml", ".yml",
                 ".txt", ".cfg", ".ini", ".csv", ".tsv", ".html", ".js", ".mjs", ".css", ""}

README = """# Supplementary material: From Traces to Guarded Programs (ICLR 2027 submission)

This archive contains tracked sources and retained evidence for the paper. Ignored
files, credentials files named `.env`, and local caches are excluded. Text files
containing configured author-identifying strings are scrubbed; the builder reports
the actual file count and scans the resulting bytes. This is not a general proof
of anonymity. `MANIFEST.sha256` records the shipped bytes. Original repository
publication manifests may describe pre-scrub bytes and are not archive checksums.
Byte-pinned upstream parquet data are preserved and checked separately.

## Layout

- `src/guarded_agentic_compaction/`: the compiler, runtime, schema, and capture packages
  (provenance, region mining, synthesis, contracts, exact calibration, dispatch, the read-only
  prologue, and the Agents-SDK adapters for OpenAI and Anthropic).
- `tests/`, `conftest.py`, `configs/`, `experiments/`: the test suite and the fixtures it needs.
- `paper/scripts/`: every study driver, table generator, recompilation script, and the
  validator `validate_artifacts.py`.
- `paper/results/`: retained result files (per-episode JSON, checkpoints, registries, manifests)
  for the primary families, the cross-repository studies, the gate-frontier study, the external
  substrates, and the studies added after the pre-submission review (recurrence-only replay,
  second model, second provider, extended held-out, prologue measurement, challenge recompile).
  The pinned public GitHub-issues snapshot (`paper/results/datasets/github_issues/`, 12 MB,
  Apache-2.0 per its dataset card, unmodified upstream bytes with sha256 pinned in
  `source_manifest.json`) is included so that the primary-family checks run offline.
- `paper/supplementary/`: every pre-registered protocol with its observed-results section.
- `paper/iclr/`: LaTeX sources, generated tables, figures, the compiled anonymous PDF
  (`build/main.pdf`), notes (number registry, revision log, reviewer response), and the
  compliance checklist.
- `benchmarks/`, `demos/`, `scripts/`: signed effect catalogs, source manifests, the
  external-substrate adapters, the demo runtime, and release tooling.

## Regenerating the paper's numbers without a provider key

```
python -m venv .venv && . .venv/bin/activate && pip install -e ".[live,dev,figures]"   # Python 3.11+
python -m pytest                                        # unit and integration tests
python paper/scripts/validate_artifacts.py --families \
  sources,live,natural_preflight,natural_live,natural_replication,portfolio_live,guarded_composite,\
  optimizer_head_to_head,continuation_replay,nestful,demo_suite,multidomain_preflight,iclr_page_budget,\
  headroom_ablation_preflights,live_extensions,recompile_with_challenge,github_workflow_families,\
  github_multirepo_pr_outcome_core,external_benchmarks,bfcl_compiler,no_secrets
python paper/scripts/recompile_retained_candidates.py   # reproduces the retained artifacts from sealed checkpoints
python paper/scripts/recompile_with_challenge.py        # same, with the perturbation suite and signed registries
python paper/scripts/second_model_replication.py preflight --model gpt-6-luna   # artifact identity check
python paper/scripts/recurrence_only_ablation.py preflight
python paper/scripts/issue_type_extended_heldout.py preflight
```

The command above is a useful provider-free subset, not the complete repository
validator. For checks specifically audited for this revision, use the validation
record in `paper/iclr/notes/final_reviewer_assessment.md`. List available families
with `python paper/scripts/validate_artifacts.py --list-families`.

Full-repository checks for publication hashes, the named preprint, public site,
and slide assets require material intentionally absent or scrubbed here.
`iclr_sources` also regenerates cluster statistics from four cross-repository
parquet snapshots (56 MB, no upstream redistribution licence declared), which are
not included. Their source manifests pin refetchable bytes. To acquire these
public data and run the complete ICLR table-regeneration check:

```
python paper/scripts/github_multirepo_pr_outcome_core.py --preflight-only --force-download
python paper/scripts/validate_artifacts.py --families iclr_sources
```

External substrates (provider-free after their pinned sources are acquired; see Appendix C):

```
python paper/scripts/bfcl_compiler_benchmark.py --source-root "$BENCHMARK_SOURCE_ROOT"
python paper/scripts/appworld_compiler_benchmark.py --source-root "$BENCHMARK_SOURCE_ROOT" --appworld-python "$APPWORLD_VENV/bin/python"
python paper/scripts/appworld_dispatch_preflight.py --source-root "$BENCHMARK_SOURCE_ROOT"
python paper/scripts/appworld_dispatch_prologue_preflight.py --source-root "$BENCHMARK_SOURCE_ROOT"
```

## Live studies (need a provider key; costs at list prices)

The retained results are the evidence; reruns are not required to check any claim. If rerun:
historical spend estimates are recorded in each retained result and protocol. They
are not current price quotes or rerun budgets, and provider aliases may have changed.
Each driver refuses to run without an explicit `--approved-spend-usd` where the protocol
requires one, and every protocol in `paper/supplementary/` states its decision rule in advance.
"""


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True).stdout
    files = []
    for line in out.splitlines():
        if not line.startswith(INCLUDE_PREFIXES):
            continue
        if line.startswith(EXCLUDE_PREFIXES) or line.endswith(EXCLUDE_SUFFIXES):
            continue
        if Path(line).name in (".env", ".env.example") or "/.cache/" in line:
            continue
        files.append(line)
    return files


def scrub_text(data: bytes) -> bytes:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    for pattern, replacement in SCRUBS:
        text = pattern.sub(replacement, text)
    return text.encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    files = tracked_files()
    with tempfile.TemporaryDirectory(prefix="gac-supplementary-") as tmp:
        stage = Path(tmp) / "gac-iclr2027-supplementary"
        stage.mkdir()
        scrubbed = 0
        for rel in files:
            src = ROOT / rel
            if not src.is_file():
                continue
            dst = stage / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            data = src.read_bytes()
            if Path(rel).suffix in TEXT_SUFFIXES:
                cleaned = scrub_text(data)
                if cleaned != data:
                    scrubbed += 1
                data = cleaned
            dst.write_bytes(data)
        (stage / "README-REVIEWERS.md").write_text(README, encoding="utf-8")
        # Verify: no identifying string survives anywhere, including binaries.
        offenders = []
        for path in sorted(stage.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(stage).as_posix()
            data = path.read_bytes()
            if rel.startswith(UPSTREAM_SNAPSHOT_PREFIX) and path.suffix == ".parquet":
                manifest = json.loads((path.parent / "source_manifest.json").read_text())
                # Two manifest formats exist: {"parquet": {"sha256": ...}} (pinned snapshot) and a
                # flat "parquet_sha256" (cross-repository and post-cutoff snapshots).
                expected = (manifest.get("parquet") or {}).get("sha256") or manifest.get("parquet_sha256")
                if not expected or hashlib.sha256(data).hexdigest() != expected:
                    offenders.append(f"{rel} (upstream sha256 missing or mismatched)")
                elif AUTHOR_TOKENS.search(data):
                    offenders.append(rel)
            elif IDENTIFYING.search(data):
                offenders.append(rel)
        if offenders:
            print("REFUSED: identifying strings remain in", offenders, file=sys.stderr)
            return 1
        # Manifest (excludes itself), then zip.
        lines = []
        for path in sorted(p for p in stage.rglob("*") if p.is_file()):
            lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(stage).as_posix()}")
        (stage / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        if args.out.exists():
            args.out.unlink()
        with zipfile.ZipFile(args.out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for path in sorted(p for p in stage.rglob("*") if p.is_file()):
                zf.write(path, arcname=path.relative_to(stage.parent).as_posix())
        count = len(lines)
    size_mb = args.out.stat().st_size / (1024 * 1024)
    print(f"wrote {args.out} ({size_mb:.1f} MB, {count} files, {scrubbed} files scrubbed); scan clean")
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
