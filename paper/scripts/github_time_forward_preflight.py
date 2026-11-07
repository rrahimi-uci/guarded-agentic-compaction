"""Provider-free preflight for the time-forward cohort (workstreams A2 / C2).

Reads the time-forward snapshot acquired from the GitHub API, classes every record under the
three primary families' own class rules, removes every record number that any retained study
under ``paper/results`` has already evaluated or selected (any ``issue_number`` /
``record_number`` field anywhere in a ``huggingface/datasets`` result or checkpoint), and
reports, per family, whether the fresh pool can supply disjoint calibration and test sets:
calibration >= 45 eligible groups (single-rule, m=1, zero violations) or >= 77 (one violation),
test >= 60 class-balanced (20 per class). Writes ``preflight.json`` beside the snapshot.
No provider call; no record is selected here, only counted.

Multi-repository mode (``--snapshot-dir DIR --repo OWNER/NAME --out FILE``): the exclusion is
repository-qualified. For ``huggingface/datasets`` it is exactly the behaviour above. For any other
repository only record numbers mentioned by a retained result that belongs to *that* repository are
excluded: a JSON file under ``paper/results`` or ``experiments`` counts when its path or text names
the repository, and inside a file a number counts when its innermost ``repository`` / ``repo`` /
``full_name`` field or enclosing repository key is the repository (numbers with no repository
context count when the file names no other known repository, so an ambiguous file over-excludes
rather than leaks). The study's own output directory ``paper/results/multirepo_end_to_end`` is never
read as prior use. The report adds the pool size, class counts, distinct authors, distinct creation
days, the number of author-distinct pull requests available, and the calibration n a selection
under the frozen multi-repository protocol would realise.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterator, Sequence

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / "src", ROOT / "paper" / "scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

SNAPSHOT_DIR = ROOT / "paper/results/datasets/github_time_forward/huggingface__datasets"
RESULTS = ROOT / "paper/results"
EXPERIMENTS = ROOT / "experiments"
OWN_STUDY_DIR = RESULTS / "multirepo_end_to_end"
HF_REPO = "huggingface/datasets"
KNOWN_REPOS = ("huggingface/datasets", "pandas-dev/pandas", "streamlit/streamlit", "psf/requests", "pytorch/pytorch")
NUMBER_KEYS = ("issue_number", "record_number", "number")
# plain lists of record numbers that selection / checkpoint files keep under these keys
NUMBER_LIST_KEYS = ("discovery", "test", "calibration", "train", "heldout", "held_out", "selected",
                    "record_numbers", "issue_numbers", "numbers", "discovery_numbers", "test_numbers")
FLOORS = {"calibration_zero_violations_m1": 45, "calibration_one_violation_m1": 77, "calibration_zero_violations_m2": 59,
          "registered_grid_m1": 92, "test_total": 60, "test_per_class": 20}


def _numbers(value: Any) -> Iterator[int]:
    if isinstance(value, dict):
        for k, v in value.items():
            if k in ("issue_number", "record_number", "number") and isinstance(v, (int, str)) and str(v).isdigit():
                yield int(v)
            else:
                yield from _numbers(v)
    elif isinstance(value, list):
        for v in value:
            yield from _numbers(v)


def _under(path: Path, roots: Sequence[Path]) -> bool:
    return any(path == r or r in path.parents for r in roots)


def used_records(repo: str | None = None, *, qualified: bool = False, exclude_paths: Sequence[Path] = ()) -> tuple[set[int], dict[str, int]]:
    """Record numbers any retained result or checkpoint mentions, qualified by repository.

    ``repo`` of ``None``, or ``huggingface/datasets`` with ``qualified`` False, keeps the original
    behaviour: every retained result under ``paper/results`` mentioning a ``number`` /
    ``issue_number`` / ``record_number``, whatever repository it belongs to (so numbers of other
    repositories that collide with huggingface/datasets numbers are excluded too). Any other
    repository, or huggingface/datasets with ``qualified`` True, only counts files and fields that
    belong to that repository, under ``paper/results`` and ``experiments``.
    ``exclude_paths`` skips files under the given files or directories (a study's own output).
    """
    skip = [Path(p).resolve() for p in exclude_paths]
    if repo is None or (repo == HF_REPO and not qualified):
        used: set[int] = set()
        per_file: dict[str, int] = {}
        own = OWN_STUDY_DIR.resolve()
        for path in sorted(RESULTS.rglob("*.json")):
            if "datasets/" in str(path.relative_to(RESULTS)) or path.stat().st_size > 60_000_000:
                continue
            if _under(path.resolve(), [own]):  # the multi-repository study's own outputs are never prior use
                continue
            if skip and _under(path.resolve(), skip):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if "huggingface/datasets" not in text and "github-issue" not in text and "issue_number" not in text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            found = set(_numbers(payload))
            if found:
                per_file[str(path.relative_to(ROOT))] = len(found)
                used |= found
        return used, per_file
    return _used_records_for_repo(repo, skip)


def _slug(repo: str) -> str:
    return repo.replace("/", "__")


def _as_repo(value: Any, known: Sequence[str]) -> str | None:
    """Return the known repository a key or field value names, else None."""
    if not isinstance(value, str):
        return None
    for r in known:
        if value == r or value == _slug(r) or f":{r}:" in f":{value}:" or value.startswith(f"github-api:{r}:"):
            return r
    return None


def _numbers_for_repo(value: Any, repo: str, known: Sequence[str], file_default: bool, ctx: str | None = None, key: str = "") -> Iterator[int]:
    """Numbers attributable to ``repo``: innermost repository context wins, else the file default."""
    if isinstance(value, dict):
        ctx2 = ctx
        for rk in ("repository", "repo", "full_name"):
            named = _as_repo(value.get(rk), known)
            if named:
                ctx2 = named
        for k, v in value.items():
            if k in NUMBER_KEYS and isinstance(v, (int, str)) and str(v).isdigit():
                if (ctx2 == repo) if ctx2 is not None else file_default:
                    yield int(v)
                continue
            named = _as_repo(k, known)
            yield from _numbers_for_repo(v, repo, known, file_default, named or ctx2, k)
    elif isinstance(value, list):
        if key in NUMBER_LIST_KEYS and value and all(isinstance(v, int) and not isinstance(v, bool) for v in value):
            if (ctx == repo) if ctx is not None else file_default:
                yield from (int(v) for v in value)
            return
        for v in value:
            yield from _numbers_for_repo(v, repo, known, file_default, ctx, key)


def _used_records_for_repo(repo: str, skip: list[Path]) -> tuple[set[int], dict[str, int]]:
    known = tuple(dict.fromkeys((*KNOWN_REPOS, repo)))
    slug = _slug(repo)
    others = [r for r in known if r != repo]
    used: set[int] = set()
    per_file: dict[str, int] = {}
    for root in (RESULTS, EXPERIMENTS):
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json")):
            rel = str(path.relative_to(root))
            if "datasets/" in rel or path.stat().st_size > 60_000_000:
                continue
            resolved = path.resolve()
            if _under(resolved, [OWN_STUDY_DIR.resolve(), *skip]):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            path_names_repo = slug in rel
            if not (path_names_repo or repo in text or slug in text):
                continue
            path_names_other = any(_slug(o) in rel for o in others)
            file_default = path_names_repo or not path_names_other
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            found = set(_numbers_for_repo(payload, repo, known, file_default))
            if found:
                per_file[str(path.relative_to(ROOT))] = len(found)
                used |= found
    return used, per_file


def load_rows(snapshot_dir: Path) -> list[dict[str, Any]]:
    import pandas as pd

    frame = pd.read_parquet(snapshot_dir / "snapshot.parquet")
    rows = frame.to_dict(orient="records")
    for row in rows:
        row["number"] = int(row["number"])
        row["comments"] = [str(v) for v in (list(row.get("comments")) if row.get("comments") is not None else [])]
        row["assignees"] = [dict(v) for v in (list(row.get("assignees")) if row.get("assignees") is not None else []) if isinstance(v, dict)]
        row["labels"] = [dict(v) for v in (list(row.get("labels")) if row.get("labels") is not None else []) if isinstance(v, dict)]
        pr = row.get("pull_request")
        row["pull_request"] = dict(pr) if isinstance(pr, dict) and any(v for v in pr.values()) else None
    return rows


def pool_report(fam, rows: list[dict[str, Any]], used: set[int], repo: str, discovery_authors: set[str] | None) -> dict[str, Any]:
    """Pool size, class counts, distinct authors and days, and the realised multi-repository n."""
    import time_forward_pr_outcome_study as study

    fresh_prs = [r for r in rows if r["number"] not in used and fam._is_pr(r)]
    authors = [study.author_of(r) for r in fresh_prs]
    pool: dict[str, Any] = {
        "repository": repo, "pool_size": len(fresh_prs),
        "class_counts": dict(Counter(fam.pr_outcome(r) for r in fresh_prs)),
        "distinct_authors": len({a.lower() for a in authors if a}), "distinct_days": len({study.day_of(r) for r in fresh_prs}),
        "prs_without_login": sum(1 for a in authors if not a),
        "author_distinct_prs_available": len({a.lower() for a in authors if a}),
    }
    store = {r["number"]: r for r in rows}
    for label, with_discovery, excl in (("with_new_discovery_split", True, set()), ("registry_reuse_no_discovery", False, discovery_authors or set())):
        sel = study.select_multirepo(fam, store, used, repo_tag=repo, unit="author", calibration_n=200, with_test=False,
                                     with_discovery=with_discovery, excluded_authors=excl)
        pool.setdefault("projected_selection", {})[label] = {
            "calibration_n": sel["calibration_n"], "status": sel["status"], "discovery_n": len(sel["discovery"]),
            "discovery_shortfall": sel["discovery_shortfall"], "calibration_shortfall": sel["calibration_shortfall"],
            "calibration_distinct_days": sel["calibration_distinct_days"],
        }
    return pool


def main(argv: Sequence[str] | None = None) -> int:
    import pandas as pd

    import github_live_study as fixed
    import github_workflow_family_study as fam

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snapshot-dir", type=Path, default=SNAPSHOT_DIR, help="directory holding snapshot.parquet and source_manifest.json")
    ap.add_argument("--repo", default=None, help="OWNER/NAME; makes the used-record exclusion repository-qualified (requires --out)")
    ap.add_argument("--out", type=Path, default=None, help="write the report here instead of <snapshot-dir>/preflight.json")
    ap.add_argument("--qualified-exclusion", action="store_true",
                    help="for huggingface/datasets also use the repository-qualified exclusion (default keeps the legacy any-repository rule)")
    ap.add_argument("--discovery-authors-file", type=Path, default=None,
                    help="logins (JSON list / one per line) or a selection.json whose discovery numbers name them; used for the projection only")
    args = ap.parse_args(argv)
    if args.repo and args.out is None:
        ap.error("--repo requires --out (the default output is the retained huggingface/datasets preflight)")
    snapshot_dir = args.snapshot_dir

    manifest = json.loads((snapshot_dir / "source_manifest.json").read_text())
    rows = load_rows(snapshot_dir)
    repo = args.repo
    used, per_file = used_records(repo, qualified=args.qualified_exclusion) if repo else used_records()
    fresh = [r for r in rows if r["number"] not in used]
    # the pinned snapshot's own numbers, for a second overlap check
    # (the pinned snapshot is huggingface/datasets; its numbers mean nothing for another repository)
    pinned = set(int(n) for n in pd.read_parquet(fixed.DATA_PATH, columns=["number"])["number"]) if repo in (None, HF_REPO) else set()
    out: dict[str, Any] = {
        "schema": "agent-compaction-time-forward-preflight/v1",
        "snapshot": manifest, "records": len(rows), "created_after": manifest["created_after_utc_day"],
        "used_record_numbers_known": len(used), "used_record_files": len(per_file),
        "overlap_with_used": sorted(r["number"] for r in rows if r["number"] in used),
        "overlap_with_pinned_snapshot": sorted(r["number"] for r in rows if r["number"] in pinned),
        "fresh_records": len(fresh), "provider_calls_executed": 0, "families": {},
    }
    issues = [r for r in fresh if not r.get("pull_request")]
    prs = [r for r in fresh if r.get("pull_request")]
    # issue-type routing: exclusive label category (github_live_study.category_for)
    cats = Counter(fixed.category_for([lab.get("name", "") for lab in r["labels"]]) for r in issues)
    exclusive = {k: v for k, v in cats.items() if k in ("bug", "enhancement", "question")}
    out["families"]["issue_type"] = {
        "pool": len(issues), "classes": dict(cats), "exclusive_classes": exclusive,
        "test_balanced_possible": all(exclusive.get(c, 0) >= FLOORS["test_per_class"] for c in ("bug", "enhancement", "question")),
        "after_test_remaining": sum(exclusive.values()) - 3 * FLOORS["test_per_class"],
    }
    pr_classes = Counter(fam.pr_outcome(r) for r in prs)
    out["families"]["pr_outcome"] = {
        "pool": len(prs), "classes": dict(pr_classes),
        "test_balanced_possible": all(pr_classes.get(c, 0) >= FLOORS["test_per_class"] for c in ("open", "merged", "closed_unmerged")),
        "after_test_remaining": len(prs) - 3 * FLOORS["test_per_class"],
    }
    bl_classes = Counter(fam.backlog_route(r) for r in issues)
    out["families"]["backlog_attention"] = {
        "pool": len(issues), "classes": dict(bl_classes),
        "test_balanced_possible": all(bl_classes.get(c, 0) >= FLOORS["test_per_class"] for c in ("owned", "discussed_unowned", "awaiting_first_response")),
        "after_test_remaining": len(issues) - 3 * FLOORS["test_per_class"],
    }
    for name, f in out["families"].items():
        remaining = f["after_test_remaining"]
        f["calibration_floors"] = {k: v for k, v in FLOORS.items() if k.startswith("calibration") or k == "registered_grid_m1"}
        f["go"] = {k: bool(f["test_balanced_possible"] and remaining >= v) for k, v in f["calibration_floors"].items()}
        f["reading"] = ("GO: balanced test and single-rule zero-violation calibration are both coverable"
                        if f["go"]["calibration_zero_violations_m1"] else "NO-GO at the single-rule floor; see classes")
    if repo:
        import time_forward_pr_outcome_study as study

        dauth = study.load_discovery_authors(args.discovery_authors_file, {r["number"]: r for r in rows}) if args.discovery_authors_file else None
        out["repository"] = repo
        out["exclusion_scope"] = ("legacy (any retained result mentioning a record number, any repository)" if repo == HF_REPO and not args.qualified_exclusion
                                  else f"repository-qualified to {repo}; own study dir excluded")
        out["pr_pool"] = pool_report(fam, rows, used, repo, dauth)
        out.update({k: out["pr_pool"][k] for k in ("pool_size", "class_counts", "distinct_authors", "distinct_days", "author_distinct_prs_available")})
    target = args.out if args.out is not None else snapshot_dir / "preflight.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, indent=2, sort_keys=True, default=str) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k in ("records", "fresh_records", "used_record_numbers_known")}))
    for name, f in out["families"].items():
        print(name, f["classes"], f.get("exclusive_classes", ""), f["reading"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
