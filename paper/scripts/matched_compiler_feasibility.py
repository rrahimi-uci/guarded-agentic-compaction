#!/usr/bin/env python3
"""Read-only feasibility calculations; never calls a model or seals an experiment.

``availability`` makes explicit, count-only GitHub GET requests through gh.
``build`` uses retained sources and writes a reproducible planning report.
Raw source availability, unused-record screening, and compiler-family discovery
are deliberately different quantities. This script cannot authorize execution.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import UTC, datetime
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from typing import Any
from urllib.parse import urlparse

import numpy as np
from scipy.stats import beta, binom

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper/results/matched_compiler_feasibility"
REPOSITORIES = ("huggingface/datasets", "pandas-dev/pandas", "psf/requests",
                "streamlit/streamlit", "pytorch/pytorch")
COMPARISONS = 24
FAMILY_ERROR = 0.05
SAMPLE_GRID = (300, 600, 900, 1200, 1800, 2400)
SCENARIOS = ((0.03, 0.01), (0.04, 0.01), (0.06, 0.01))
REPO_RE = re.compile(r"[\w.-]+/[\w.-]+\Z")
URL_RE = re.compile(r"https://(?:api\.)?github\.com/(?:repos/)?([\w.-]+/[\w.-]+)/(?:issues|pulls?)/(\d+)")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def _probability(value: float, *, open_interval: bool = False) -> None:
    if not math.isfinite(value) or not (0 <= value <= 1):
        raise ValueError("expected finite probability in [0, 1]")
    if open_interval and value in (0, 1):
        raise ValueError("probability must be strictly between zero and one")


@lru_cache(maxsize=256)
def _critical(n: int, error: float) -> np.ndarray:
    """Minimum favorable discordances for a two-sided exact McNemar rejection."""
    m = np.arange(n + 1)
    k = binom.ppf(1 - error / 2, m, 0.5).astype(int) + 1
    # Protect exact tail equality against inverse-CDF floating point rounding.
    previous_passes = (k - 1 > m / 2) & (2 * binom.sf(k - 2, m, 0.5) <= error)
    k = k - previous_passes.astype(int)
    k = k + (2 * binom.sf(k - 1, m, 0.5) > error).astype(int)
    return k


def superiority_power(n: int, better: float, worse: float,
                      error: float = FAMILY_ERROR / COMPARISONS) -> float:
    """Exact favorable-rejection probability under iid paired multinomial outcomes.

    better=P(GAC correct, comparator wrong), worse=P(reverse). Conditional on
    M discordant pairs, favorable pairs are Bin(M, better/(better+worse)).
    This is a conservative Bonferroni planning threshold for the Holm analysis,
    not the probability that every family or the complete study succeeds.
    """
    if type(n) is not int or n < 1:
        raise ValueError("n must be a positive integer")
    for p in (better, worse):
        _probability(p)
    _probability(error, open_interval=True)
    discordance = better + worse
    if discordance > 1:
        raise ValueError("discordance probabilities sum above one")
    if discordance == 0:
        return 0.0
    m = np.arange(n + 1)
    return float(np.dot(binom.pmf(m, n, discordance),
                        binom.sf(_critical(n, error) - 1, m, better / discordance)))


def ni_max_losses(n: int, margin: float = 0.05,
                  error: float = FAMILY_ERROR / COMPARISONS) -> int:
    if type(n) is not int or n < 1:
        raise ValueError("n must be a positive integer")
    _probability(margin, open_interval=True)
    _probability(error, open_interval=True)
    bounds = beta.ppf(1 - error, np.arange(n) + 1, n - np.arange(n))
    accepted = np.flatnonzero(bounds < margin)
    return int(accepted[-1]) if len(accepted) else -1


def power_report() -> dict[str, Any]:
    error = FAMILY_ERROR / COMPARISONS
    rows = []
    for n in SAMPLE_GRID:
        max_losses = ni_max_losses(n)
        rows.append({
            "test_groups_per_family": n,
            "test_episodes_12_families_4_arms": 48 * n,
            "superiority_power": [
                {"gac_only_correct_probability": a, "comparator_only_correct_probability": b,
                 "power": superiority_power(n, a, b)} for a, b in SCENARIOS],
            "zero_loss_upper_bound": 1 - error ** (1 / n),
            "five_point_ni_max_losses": max_losses,
            "five_point_ni_power": [
                {"comparator_only_correct_probability": p,
                 "power": float(binom.cdf(max_losses, n, p))} for p in (0.01, 0.02, 0.03)],
        })
    return {
        "familywise_error": FAMILY_ERROR, "primary_contrasts": COMPARISONS,
        "per_contrast_planning_error": error,
        "assumptions": "iid paired groups; assumed discordance rates; favorable two-sided exact rejection",
        "qualification": "Holm may be less conservative; these are per-contrast powers, not joint study power",
        "zero_loss_minimum_groups_for_strict_ni": {
            str(m): math.floor(math.log(error) / math.log(1 - m)) + 1 for m in (0.05, 0.02, 0.01)},
        "rows": rows,
        "candidate_calibration": {
            "alpha": 0.05, "delta": 0.10, "thresholds": 11,
            "fixed_candidate_zero_error_minimum": math.ceil(math.log(.1 / 11) / math.log(.95)),
            "simultaneous_12_candidate_zero_error_minimum": math.ceil(math.log(.1 / 132) / math.log(.95)),
            "qualification": "Floors apply only to frozen candidates, registered losses and iid calibration groups; not final-answer evidence.",
        },
    }


def mentioned_records(value: Any) -> tuple[dict[str, set[int]], set[int]]:
    """Conservative screening, retaining ambiguity instead of inventing a repo.

    Exact GitHub URLs and explicit repo contexts preserve namespaces. Unqualified
    record ids and selection arrays are excluded from every repository. Unrelated
    numeric selection fields may over-exclude; this is not a sealed lineage audit.
    """
    qualified: dict[str, set[int]] = defaultdict(set)
    ambiguous: set[int] = set()

    def add(number: int, repo: str | None) -> None:
        if number > 0:
            (qualified[repo] if repo else ambiguous).add(number)

    def visit(item: Any, repo: str | None = None, selection: bool = False) -> None:
        if isinstance(item, dict):
            explicit = item.get("repository") or item.get("repo")
            if isinstance(explicit, str) and REPO_RE.fullmatch(explicit):
                repo = explicit
            for key in ("html_url", "url", "repository_url"):
                url = item.get(key)
                if isinstance(url, str):
                    parsed = urlparse(url)
                    parts = parsed.path.strip("/").split("/")
                    if parsed.hostname in {"github.com", "api.github.com"}:
                        parts = parts[1:] if parts[:1] == ["repos"] else parts
                        if len(parts) >= 2:
                            repo = "/".join(parts[:2])
            for key, child in item.items():
                if type(child) is int and (key in {"issue_number", "record_number"} or
                        (key == "number" and (selection or "title" in item or "created_at" in item))):
                    add(child, repo)
                selected = selection or key in {"selection", "selected", "cohort", "cohorts", "splits"} or key.endswith(("_numbers", "_ids"))
                child_repo = key if key in REPOSITORIES else repo
                visit(child, child_repo, selected)
        elif isinstance(item, list):
            for child in item:
                if selection and type(child) is int:
                    add(child, repo)
                else:
                    visit(child, repo, selection)
        elif isinstance(item, str):
            for matched_repo, number in URL_RE.findall(item):
                add(int(number), matched_repo)
            for number in re.findall(r"(?:github[-\w]*issue:|issue:)(\d+)", item):
                add(int(number), repo)
    visit(value)
    return dict(qualified), ambiguous


def exclusion_audit() -> tuple[dict[str, set[int]], set[int], dict[str, Any]]:
    listed = subprocess.run(["git", "ls-files", "-z", "paper/results", "experiments"],
                            cwd=ROOT, check=True, capture_output=True).stdout.decode().split("\0")
    qualified: dict[str, set[int]] = defaultdict(set)
    ambiguous: set[int] = set()
    inputs = {}
    scanned = 0
    for relative in sorted(listed):
        path = ROOT / relative
        if path.suffix != ".json" or "datasets" in path.parts or "vendor" in path.parts or path.is_relative_to(OUT):
            continue
        payload = json.loads(path.read_text())  # malformed evidence is an error, never silently skipped
        scoped, unknown = mentioned_records(payload)
        scanned += 1
        for repo, ids in scoped.items():
            qualified[repo].update(ids)
        ambiguous.update(unknown)
        if scoped or unknown:
            inputs[relative] = digest(path)
    audit = {"status": "conservative_screen_not_sealed", "scanned_tracked_json_files": scanned,
             "input_hashes": inputs, "ambiguous_ids_excluded_from_every_repository": len(ambiguous),
             "qualified_id_counts": {k: len(v) for k, v in sorted(qualified.items())},
             "limitations": ["Unqualified IDs can over-exclude other repositories.",
                            "Raw datasets are not prior experiment outcomes and are excluded from scanning.",
                            "Unrecognized ID encodings and untracked evidence need a separate pre-seal lineage audit."]}
    return dict(qualified), ambiguous, audit


def source_specs() -> list[tuple[str, Path, Path]]:
    data = ROOT / "paper/results/datasets"
    specs = [("huggingface/datasets", data / "github_issues/source_manifest.json",
              data / "github_issues/train-00000-of-00001.parquet")]
    for repo in REPOSITORIES[1:]:
        base = data / "github_multirepo" / repo.replace("/", "__")
        specs.append((repo, base / "source_manifest.json", base / "snapshot.parquet"))
    base = data / "github_time_forward/huggingface__datasets"
    specs.append(("huggingface/datasets", base / "source_manifest.json", base / "snapshot.parquet"))
    return specs


def classify_source_row(row: dict[str, Any]) -> dict[str, Any]:
    """Audit raw schema without manufacturing comment text from a count."""
    comments = row.get("comments")
    if isinstance(comments, np.ndarray):
        comments = comments.tolist()
    comment_text = isinstance(comments, list) and all(isinstance(s, str) for s in comments)
    pr = row.get("pull_request")
    if isinstance(pr, str):
        try:
            pr = json.loads(pr)
        except json.JSONDecodeError:
            pr = None
    is_pr = isinstance(pr, dict) and bool(pr.get("url") or pr.get("html_url"))
    state = row.get("state")
    # A missing merged field is unknown, not evidence of closed-unmerged status.
    outcome = None
    if is_pr:
        if state == "open":
            outcome = "open"
        elif pr.get("merged_at") or pr.get("is_merged") is True:
            outcome = "merged"
        elif state == "closed" and ("merged_at" in pr or pr.get("is_merged") is False):
            outcome = "closed_unmerged"
        else:
            outcome = "unknown"
    title = row.get("title")
    title_ok = isinstance(title, str) and 0 < len(title.strip()) <= 500
    body = row.get("body")
    excerpt = any(isinstance(s, str) and len(s.strip()) >= 20 for s in
                  [title, body, *(comments[:3] if comment_text else [])])
    return {"is_pr": is_pr, "comment_text_available": comment_text,
            "pr_outcome": outcome, "title_representable": title_ok,
            "issue_excerpt_available": not is_pr and excerpt,
            "is_open_issue": not is_pr and state == "open"}


def inventory_source(repo: str, manifest_path: Path, parquet: Path,
                     excluded: set[int]) -> dict[str, Any]:
    result: dict[str, Any] = {"repository": repo, "manifest_path": str(manifest_path.relative_to(ROOT)),
                              "parquet_path": str(parquet.relative_to(ROOT))}
    if not manifest_path.exists():
        return {**result, "status": "missing_manifest"}
    manifest = json.loads(manifest_path.read_text())
    result.update(manifest_sha256=digest(manifest_path), source_revision=manifest.get("revision"),
                  source_schema=manifest.get("schema"), fetched_at=manifest.get("fetch_completed_utc"))
    if not parquet.exists():
        return {**result, "status": "missing_optional_local_snapshot"}
    expected = manifest.get("parquet_sha256") or manifest.get("parquet", {}).get("sha256")
    actual = digest(parquet)
    if not expected or actual != expected:
        raise ValueError(f"snapshot checksum mismatch: {result['parquet_path']}")
    import pyarrow.parquet as pq
    wanted = {"number", "title", "body", "comments", "pull_request", "state", "created_at", "updated_at", "user"}
    schema = pq.read_schema(parquet)
    records = pq.read_table(parquet, columns=[n for n in schema.names if n in wanted]).to_pylist()
    dedup = {}
    for row in records:
        n = int(row["number"])
        old = dedup.get(n)
        if old is None or str(row.get("updated_at")) > str(old.get("updated_at")):
            dedup[n] = row
    counts: Counter[str] = Counter()
    days: Counter[str] = Counter()
    authors: Counter[str] = Counter()
    for number, row in dedup.items():
        if number in excluded:
            counts["excluded_by_prior_screen"] += 1
            continue
        counts["remaining_records"] += 1
        detail = classify_source_row(row)
        for key in ("comment_text_available", "title_representable", "issue_excerpt_available", "is_open_issue"):
            counts[key] += int(detail[key])
        if detail["is_pr"]:
            counts["pull_requests"] += 1
            counts["pr_" + detail["pr_outcome"]] += 1
        else:
            counts["issues"] += 1
        if detail["title_representable"]:
            if detail["is_pr"] and detail["pr_outcome"] != "unknown":
                counts["pr_core_source_eligible"] += 1
                if detail["comment_text_available"]:
                    counts["pr_excerpt_source_eligible"] += 1
            if detail["is_open_issue"] and detail["comment_text_available"]:
                counts["backlog_source_screen"] += 1
            if detail["issue_excerpt_available"] and detail["comment_text_available"]:
                counts["issue_type_source_screen"] += 1
        days[str(row.get("created_at") or "unknown")[:10]] += 1
        author = row.get("user")
        authors[str(author.get("id") or author.get("login") or "unknown") if isinstance(author, dict) else "unknown"] += 1
    dates = sorted(d for d in days if d != "unknown")
    return {**result, "status": "checksum_verified_local_inventory", "parquet_sha256": actual,
            "raw_rows": len(records), "unique_records": len(dedup), "counts": dict(sorted(counts.items())),
            "remaining_created_range": [dates[0], dates[-1]] if dates else [],
            "remaining_distinct_days": len(dates), "remaining_distinct_known_authors": len(authors) - int("unknown" in authors),
            "remaining_unknown_author_records": authors.get("unknown", 0),
            "largest_author_cluster": max(authors.values(), default=0),
            "remaining_ids_sha256": hashlib.sha256(json.dumps(sorted(set(dedup) - excluded)).encode()).hexdigest(),
            "qualification": "Source screens overlap and are not disjoint cohorts, discovered candidates, independent units, or verified grader contracts."}


def refresh_availability(path: Path) -> None:
    """Count-only public queries; retain errors and incomplete-result flags."""
    if path.exists():
        raise ValueError("availability evidence already exists; use a fresh --out directory")
    rows = []
    for repo in REPOSITORIES:
        for cutoff in ("2025-06-14", "2026-10-08"):
            for kind, filters in (("issues", "is:issue"), ("open_issues", "is:issue is:open"), ("pull_requests", "is:pr")):
                query = f"repo:{repo} {filters} created:>={cutoff}"
                row = {"repository": repo, "created_since": cutoff, "kind": kind, "query": query,
                       "retrieved_at": datetime.now(UTC).isoformat()}
                try:
                    response = subprocess.run(["gh", "api", "--method", "GET", "search/issues", "-f", f"q={query}",
                                               "-f", "per_page=1", "--jq", "{total_count, incomplete_results}"],
                                              capture_output=True, text=True, timeout=45)
                    if response.returncode:
                        row.update(status="request_failed", exit_code=response.returncode)
                    else:
                        payload = json.loads(response.stdout)
                        if (type(payload.get("total_count")) is not int or payload["total_count"] < 0
                                or type(payload.get("incomplete_results")) is not bool):
                            raise ValueError("malformed count response")
                        row.update(status="returned", total_count=payload["total_count"],
                                   incomplete_results=payload["incomplete_results"])
                except (subprocess.TimeoutExpired, OSError, ValueError):
                    row.update(status="unavailable")
                rows.append(row)
                print(f"{repo} {cutoff} {kind}: {row.get('total_count', row['status'])}", flush=True)
    write_json(path, {"schema": "gac-source-availability/v1", "queries": rows,
                     "source": "https://docs.github.com/en/rest/search/search#search-issues-and-pull-requests",
                     "qualification": "Mutable search counts, not acquired records; no overlap, field completeness, class balance or independent sampling established."})


def cost_reference(power: dict[str, Any]) -> dict[str, Any]:
    path = ROOT / "experiments/generalization_gate/checkpoint.json"
    rows = json.loads(path.read_text())["rows"]
    cells: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["group"] == "primary" and row["arm"] == "baseline" and row["status"] == "completed":
            cells[row["family"] + "|" + row["model"]].append(row["metrics"])
    means = {key: {metric: sum(r[metric] for r in rs) / len(rs)
                   for metric in ("input_tokens", "output_tokens", "requests", "estimated_cost_usd")}
             for key, rs in sorted(cells.items())}
    lo = min(v["estimated_cost_usd"] for v in means.values())
    hi = max(v["estimated_cost_usd"] for v in means.values())
    designs = []
    for row in power["rows"]:
        test = row["test_episodes_12_families_4_arms"]
        # Illustrative 64 train + 32 dev + 300 calibration + 6 pilot records x 4 arms.
        setup = 12 * (64 + 32 + 300 + 6 * 4)
        designs.append({"test_groups_per_family": row["test_groups_per_family"], "test_episodes": test,
                        "illustrative_setup_episodes": setup, "total_reference_episodes": test + setup,
                        "historical_cost_reference_usd": [(test + setup) * lo, (test + setup) * hi],
                        "fivefold_high_reference_usd": (test + setup) * hi * 5})
    return {"source": str(path.relative_to(ROOT)), "source_sha256": digest(path),
            "completed_baseline_cell_means": means, "designs": designs, "authorized_spend_usd": 0,
            "qualification": "Historical frozen-price references, not current quotes, forecasts, spend caps or upper bounds. Excludes failed-call unknown charges, human work, acquisition, additional discovery and any separate final-answer calibration. New pilot and current pricing required."}


def build(out: Path) -> dict[str, Any]:
    qualified, ambiguous, exclusions = exclusion_audit()
    sources = [inventory_source(repo, manifest, parquet, qualified.get(repo, set()) | ambiguous)
               for repo, manifest, parquet in source_specs()]
    power = power_report()
    availability = out / "availability.json"
    report = {"schema": "gac-matched-compiler-feasibility/v1", "status": "NO_GO_FOR_CONFIRMATORY_EXECUTION",
              "paid_provider_calls": 0, "cohort_sealed": False, "prospective_questions_specified": True,
              "generator_sha256": digest(Path(__file__)), "protocol_sha256": digest(ROOT / "paper/supplementary/matched-compiler-candidate-protocol.md"),
              "exclusions": exclusions, "retained_source_inventory": sources, "power": power,
              "cost_reference": cost_reference(power),
              "availability_sha256": digest(availability) if availability.exists() else None,
              "blockers": ["Fresh complete source snapshots and a sealed overlap audit have not been acquired.",
                           "Twelve candidate families have not been discovered; repository replications are not distinct workflow structures.",
                           "Compiler-level comparator policies and matched continuation packaging are not implemented.",
                           "Final endpoints, sample sizes and independence assumptions require an executable prospective seal.",
                           "Current provider pricing, execution pilot, failure reserve and study-specific spending cap remain unset."],
              "next_action": "Acquire and audit fresh source evidence, then discover candidates on training data under a separately costed plan; no confirmatory provider run yet."}
    write_json(out / "report.json", report)
    live = json.loads(availability.read_text()) if availability.exists() else {"queries": []}
    (out / "REPORT.md").write_text(render(report, live))
    return report


def render(report: dict[str, Any], live: dict[str, Any]) -> str:
    lines = [
        "# Matched compiler study: first-phase feasibility and power report", "",
        "**Decision: NO-GO for confirmatory provider execution; proceed with source acquisition and design preparation.**",
        "No new model calls were made. No final cohort, candidate set, model, numeric spending cap or execution protocol is sealed.",
        "This report is a planning artifact, not new evidence for the paper's performance or a higher review score.", "",
        "The [prospective protocol](../../supplementary/matched-compiler-candidate-protocol.md) fixes the research questions and decision criteria.",
        "The [machine-readable report](report.json) retains inputs, hashes, assumptions and complete calculations;",
        "[availability.json](availability.json) retains the count-only public GitHub queries.", "",
        "## 1. Data that are actually present", "",
        "Each local Parquet file was checked against its retained source checksum. Counts below follow a conservative prior-use screen;",
        "they are not certified fresh cohorts. Unqualified IDs are excluded across repositories, which can over-exclude.",
        "Unrecognized encodings and untracked evidence still need a complete pre-seal lineage audit.",
        "Raw datasets were not mistaken for prior model experiments. The two huggingface snapshots remain separate.", "",
        "| Repository / snapshot | Unique records | Remaining after screen | PR core source screen | PR excerpt source screen | Issue source screen | Backlog source screen |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for source in report["retained_source_inventory"]:
        counts = source.get("counts", {})
        suffix = " / post-cutoff" if "time_forward" in source["manifest_path"] else " / historical"
        vals = [source.get("unique_records", "unavailable"), counts.get("remaining_records", 0),
                counts.get("pr_core_source_eligible", 0), counts.get("pr_excerpt_source_eligible", 0),
                counts.get("issue_type_source_screen", 0), counts.get("backlog_source_screen", 0)]
        lines.append(f"| {source['repository']}{suffix} | " + " | ".join(map(str, vals)) + " |")
    lines += ["", "These screens overlap; issue/backlog counts cannot be added as disjoint cohorts. They do not verify task graders, class balance,",
              "candidate recurrence, full source schemas, or independent groups. Repository replications are not distinct workflow structures.",
              "Four multi-repository mirrors contain comment counts rather than comment bodies. Their existing adapter's synthetic 'comment'",
              "placeholders must not be used as factual excerpt evidence. Those mirrors support only the narrower source screen until complete evidence is acquired.", "",
              "## 2. Live availability, not acquired evidence", "",
              "| Repository | Issues since 2025-06-14 | Open issues since 2025-06-14 | PRs since 2025-06-14 | Issues since 2026-10-08 | PRs since 2026-10-08 |",
              "|---|---:|---:|---:|---:|---:|"]
    index = {(r["repository"], r["created_since"], r["kind"]): r for r in live["queries"]}
    for repo in REPOSITORIES:
        counts = []
        for cutoff, kind in (("2025-06-14", "issues"), ("2025-06-14", "open_issues"),
                             ("2025-06-14", "pull_requests"), ("2026-10-08", "issues"), ("2026-10-08", "pull_requests")):
            row = index.get((repo, cutoff, kind), {})
            counts.append(str(row["total_count"]) if row.get("status") == "returned" and row.get("incomplete_results") is False else "unavailable/incomplete")
        lines.append(f"| {repo} | " + " | ".join(counts) + " |")
    dates = sorted(r["retrieved_at"] for r in live["queries"])
    lines += ["", f"Queries captured: {dates[0] if dates else 'not captured'} through {dates[-1] if dates else 'not captured'}.",
              "The broad window follows the original 2025-06-13 snapshot. The recent window follows the last retained API acquisition on 2026-10-07.",
              "Neither window proves record-level non-overlap. Search totals are mutable and are not counts of usable or independent tasks.",
              "No issue bodies, comments or final cohort were acquired by these probes.",
              "[GitHub documents](https://docs.github.com/en/rest/search/search#search-issues-and-pull-requests) incomplete-result flags and a 1,000-result retrieval cap per search.",
              "A full acquisition must paginate repository endpoints or use auditable date partitions, not treat one search page as a complete corpus.", "",
              "## 3. Prospective power", "",
              "The quality family has 24 paired contrasts (12 families x two simpler compilers). Planned analysis uses two-sided exact McNemar tests",
              "with Holm correction. These conservative power calculations use 0.05/24 for each test, assuming iid paired groups.",
              "The assumed favorable/reverse discordance probabilities are (3%,1%), (4%,1%) and (6%,1%), respectively. They are assumptions, not measured future rates.", "",
              "| Test groups per family | Four-arm test episodes | Power: +2 pp | Power: +3 pp | Power: +5 pp | Five-point NI power at 2% comparator-only success |",
              "|---:|---:|---:|---:|---:|---:|"]
    for row in report["power"]["rows"]:
        vals = [str(row["test_groups_per_family"]), str(row["test_episodes_12_families_4_arms"])]
        vals += [f"{100 * p['power']:.1f}%" for p in row["superiority_power"]]
        vals += [f"{100 * row['five_point_ni_power'][1]['power']:.1f}%"]
        lines.append("| " + " | ".join(vals) + " |")
    lines += ["", "At 300 groups even zero comparator-only losses give a simultaneous upper bound of 2.0369 points: this design cannot establish a two-point margin.",
              "The strict zero-loss minima are 121, 306 and 615 groups for five-, two- and one-point noninferiority, respectively.",
              "At 900 groups, the three-point planning scenario exceeds the 80% per-contrast power target; at 1,200 it reaches about 95%.",
              "Investigate source feasibility at 900–1,200 test groups per family. This range is a planning reference, not a chosen sample size,",
              "not adequate for every two-point scenario, and not a guarantee of joint success across families. Effective cluster counts can be much smaller.",
              "The existing 92-group replay floor is per fixed candidate. Simultaneous correction over 12 fixed candidates and 11 thresholds requires",
              "at least 141 zero-violation groups under alpha=0.05 and delta=0.10. This arithmetic does not establish iid sampling or final-answer reliability.", "",
              "## 4. Resource reference and scope", "",
              "The following is a historical frozen-price reference, not a current quote or spending cap. It applies the minimum/maximum observed completed",
              "baseline mean cost across six retained cells to every planned episode. New tool payloads and model settings may have different costs.",
              "Each row adds 5,040 illustrative setup episodes: 12 x (64 train + 32 development + 300 calibration + six pilot records x four arms).",
              "Additional discovery, unknown failed-call charges, acquisition, human work and a separate end-to-end calibration study are excluded.", "",
              "| Test groups per family | Reference total episodes | Historical cost reference, USD | 5x high reference, USD |",
              "|---:|---:|---:|---:|"]
    for row in report["cost_reference"]["designs"]:
        lo, hi = row["historical_cost_reference_usd"]
        lines.append(f"| {row['test_groups_per_family']} | {row['total_reference_episodes']} | {lo:.2f}–{hi:.2f} | {row['fivefold_high_reference_usd']:.2f} |")
    lines += ["", "No spending is authorized by this report. Current prices, actual discovery volume, pilot token distributions and a failure reserve must inform a later numeric cap.", "",
              "## 5. What is still required", ""]
    lines += [f"- {blocker}" for blocker in report["blockers"]]
    lines += ["", "The current harness offers three task templates plus a narrower PR-core variant. It has not mined twelve fresh candidate families.",
              "The support-only implementation copies an already-admitted registry; it must become a compiler-level policy over the common candidate list.",
              "The first acquisition priority is complete PR evidence from pandas, streamlit and pytorch, where the broad count probes justify investigating volume.",
              "At the illustrative 1,200-test-group design, 64 train + 32 dev + 300 calibration + six pilot records require 1,602 distinct records per unit.",
              "The observed broad-window open-issue pools in pandas and streamlit fall below that count even before exclusions, so a 12-cell grid of the existing",
              "templates must not be assumed feasible. Additional repositories, different legitimate task structures or a prospectively narrower design are needed.",
              "Freeze the acquisition plan before model discovery; acquire source evidence, audit labels/comments/PR state, then mine candidates on training data only.",
              "Do not replace rejected candidates, select families by final accuracy, or extrapolate search counts into an execution-ready cohort.", "",
              "## Reproduction", "", "From the repository root:", "", "```sh",
              "PYTHONDONTWRITEBYTECODE=1 .venv/bin/python paper/scripts/matched_compiler_feasibility.py build",
              "PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider paper/scripts/test_matched_compiler_feasibility.py",
              "```", "", "The local inventory requires the retained optional multi-repository Parquet caches; absent caches are explicitly reported, never downloaded automatically.",
              "The tests use synthetic source fixtures and retained reports, and need no credentials. To collect a new dated count-only availability snapshot,",
              "run the script's `availability` command with a fresh `--out` directory; do not overwrite historical evidence silently.", ""]
    return "\n".join(lines)


def verify(out: Path) -> None:
    """Recompute statistics and derived prose, and check the retained provenance."""
    report = json.loads((out / "report.json").read_text())
    availability = json.loads((out / "availability.json").read_text())

    def same(actual: Any, expected: Any) -> bool:
        if isinstance(actual, dict) and isinstance(expected, dict):
            return actual.keys() == expected.keys() and all(same(actual[k], expected[k]) for k in actual)
        if isinstance(actual, list) and isinstance(expected, list):
            return len(actual) == len(expected) and all(same(a, b) for a, b in zip(actual, expected))
        if type(actual) in (int, float) and type(expected) in (int, float):
            return math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12)
        return type(actual) is type(expected) and actual == expected

    if not same(report["power"], power_report()) or not same(report["cost_reference"], cost_reference(report["power"])):
        raise ValueError("retained statistics or historical cost references do not reproduce")
    if report["status"] != "NO_GO_FOR_CONFIRMATORY_EXECUTION" or report["cohort_sealed"] or report["paid_provider_calls"]:
        raise ValueError("feasibility report overstates execution status")
    paths = {**report["exclusions"]["input_hashes"],
             "paper/supplementary/matched-compiler-candidate-protocol.md": report["protocol_sha256"],
             "paper/scripts/matched_compiler_feasibility.py": report["generator_sha256"]}
    for source in report["retained_source_inventory"]:
        if "manifest_sha256" in source:
            paths[source["manifest_path"]] = source["manifest_sha256"]
        parquet = ROOT / source["parquet_path"]
        if parquet.exists() and source.get("parquet_sha256") and digest(parquet) != source["parquet_sha256"]:
            raise ValueError(f"changed optional source: {source['parquet_path']}")
    for relative, expected in paths.items():
        if digest(ROOT / relative) != expected:
            raise ValueError(f"changed retained input: {relative}")
    if digest(out / "availability.json") != report["availability_sha256"]:
        raise ValueError("changed availability evidence")
    if (out / "REPORT.md").read_text() != render(report, availability):
        raise ValueError("rendered report does not match retained calculations")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("availability", "build", "verify"))
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    if args.command == "availability":
        refresh_availability(args.out / "availability.json")
    elif args.command == "verify":
        verify(args.out)
        print("Retained calculations, report and input hashes verified; study remains unrun.")
    else:
        report = build(args.out)
        print(report["status"])
        for source in report["retained_source_inventory"]:
            print(source["repository"], source["status"], source.get("counts", {}))


if __name__ == "__main__":
    main()
