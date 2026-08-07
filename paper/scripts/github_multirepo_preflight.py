#!/usr/bin/env python3
"""Provider-free multirepo, time-forward cohort preflight for future GitHub studies."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence
from urllib.parse import urlparse

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "src", ROOT / "paper" / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import github_live_study as issue_type  # noqa: E402
import github_workflow_family_study as workflow_family  # noqa: E402


DEFAULT_OUT = ROOT / "paper" / "results" / "github_multirepo" / "preflight.json"
LEGACY_DEFAULT_REPO = "huggingface/datasets"
RESULT_ROOTS = (
    ROOT / "paper/results/github_live",
    ROOT / "paper/results/github_natural_live",
    ROOT / "paper/results/github_natural_replication",
    ROOT / "paper/results/gcs_live",
    ROOT / "paper/results/optimizer_head_to_head",
    ROOT / "paper/results/portfolio_live",
    ROOT / "paper/results/github_workflow_families",
)


class PreflightDesignError(RuntimeError):
    """Raised when a requested repo/family cannot satisfy the frozen protocol."""


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _split_csv(values: Sequence[str]) -> tuple[str, ...]:
    parts: list[str] = []
    for value in values:
        for item in str(value).split(","):
            item = item.strip()
            if item:
                parts.append(item)
    return tuple(parts)


def infer_repository(row: Mapping[str, Any]) -> str | None:
    """Infer ``owner/name`` from GitHub or GitHub API URLs."""

    urls = [
        row.get("html_url"),
        row.get("repository_url"),
        (row.get("pull_request") or {}).get("html_url")
        if isinstance(row.get("pull_request"), dict)
        else None,
        (row.get("pull_request") or {}).get("url")
        if isinstance(row.get("pull_request"), dict)
        else None,
    ]
    for raw in urls:
        value = str(raw or "").strip()
        if not value:
            continue
        parsed = urlparse(value)
        host = parsed.netloc.lower()
        parts = [part for part in parsed.path.split("/") if part]
        if host == "api.github.com" and len(parts) >= 3 and parts[0] == "repos":
            return f"{parts[1]}/{parts[2]}"
        if host.endswith("github.com") and len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
    return None


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if hasattr(value, "tolist"):
        converted = value.tolist()
        return converted if isinstance(converted, list) else [converted]
    return [value]


def _labels_from_row(row: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(
        sorted(
            str(item.get("name"))
            for item in _as_list(row.get("labels"))
            if isinstance(item, dict) and item.get("name")
        )
    )


def _day_from_row(row: Mapping[str, Any]) -> str:
    for key in ("created_at", "updated_at", "closed_at"):
        value = row.get(key)
        if hasattr(value, "date"):
            return value.date().isoformat()
        if isinstance(value, str) and value:
            return value[:10]
    raise PreflightDesignError("row lacks a usable date field")


def _updated_key(row: Mapping[str, Any]) -> tuple[str, int]:
    return (str(row.get("updated_at") or ""), int(row.get("id") or 0))


def normalize_row(row: Mapping[str, Any], *, repository: str) -> dict[str, Any]:
    raw_body = row.get("body")
    pull_request = row.get("pull_request")
    return {
        "repository": repository,
        "number": int(row["number"]),
        "title": str(row.get("title") or ""),
        "body": raw_body if isinstance(raw_body, str) else "",
        "labels": _labels_from_row(row),
        "state": str(row.get("state") or ""),
        "comments": [str(value) for value in _as_list(row.get("comments"))],
        "assignees": [
            dict(value) for value in _as_list(row.get("assignees")) if isinstance(value, dict)
        ],
        "pull_request": pull_request if isinstance(pull_request, dict) else None,
        "html_url": str(row.get("html_url") or ""),
        "repository_url": str(row.get("repository_url") or ""),
        "day": _day_from_row(row),
        "created_at": str(row.get("created_at") or ""),
        "updated_at": str(row.get("updated_at") or ""),
        "id": int(row.get("id") or 0),
    }


def load_snapshot_stores(
    snapshot_paths: Sequence[Path],
) -> tuple[dict[str, dict[int, dict[str, Any]]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    stores: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    repo_duplicates: Counter[str] = Counter()
    snapshot_audits: list[dict[str, Any]] = []
    repo_sources: dict[str, set[str]] = defaultdict(set)

    for path in snapshot_paths:
        frame = pd.read_parquet(path)
        discovered: Counter[str] = Counter()
        unresolved = 0
        duplicate_rows = 0
        for raw in frame.to_dict(orient="records"):
            repository = infer_repository(raw)
            if repository is None:
                unresolved += 1
                continue
            discovered[repository] += 1
            repo_sources[repository].add(_display_path(path))
            row = normalize_row(raw, repository=repository)
            number = int(row["number"])
            current = stores[repository].get(number)
            if current is not None:
                duplicate_rows += 1
                repo_duplicates[repository] += 1
                if _updated_key(row) <= _updated_key(current):
                    continue
            stores[repository][number] = row
        snapshot_audits.append(
            {
                "path": _display_path(path),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
                "raw_rows": len(frame),
                "unresolved_repository_rows": unresolved,
                "duplicate_rows_replaced_or_ignored": duplicate_rows,
                "repositories_discovered": dict(discovered),
            }
        )

    repo_audits: dict[str, dict[str, Any]] = {}
    for repository, store in sorted(stores.items()):
        days = sorted({row["day"] for row in store.values()})
        repo_audits[repository] = {
            "deduplicated_records": len(store),
            "duplicate_rows_replaced_or_ignored": repo_duplicates[repository],
            "snapshot_sources": sorted(repo_sources[repository]),
            "day_range": {
                "min": days[0] if days else None,
                "max": days[-1] if days else None,
                "unique_days": len(days),
            },
        }
    return dict(stores), snapshot_audits, repo_audits


def _parse_day(value: str) -> date:
    return date.fromisoformat(value)


def _stable_rank(repository: str, seed: int, namespace: str, number: int) -> str:
    return hashlib.sha256(f"{seed}:{repository}:{namespace}:{number}".encode()).hexdigest()


def _record_stub(repository: str, row: Mapping[str, Any], class_name: str) -> dict[str, Any]:
    return {
        "repository": repository,
        "issue_number": int(row["number"]),
        "class": class_name,
        "day": str(row["day"]),
        "html_url": str(row["html_url"]),
    }


def _choose_test_start_day(
    rows_by_class: Mapping[str, Sequence[Mapping[str, Any]]],
    need_by_class: Mapping[str, int],
) -> date:
    by_day: dict[date, Counter[str]] = defaultdict(Counter)
    for class_name, rows in rows_by_class.items():
        for row in rows:
            by_day[_parse_day(str(row["day"]))][class_name] += 1
    counts: Counter[str] = Counter()
    for current_day in sorted(by_day, reverse=True):
        counts.update(by_day[current_day])
        if all(counts[class_name] >= need for class_name, need in need_by_class.items()):
            return current_day
    raise PreflightDesignError(
        "insufficient recent class support for a strict time-forward held-out window"
    )


def _time_forward_metadata(
    discovery: Sequence[Mapping[str, Any]],
    test: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    discovery_days = sorted({_parse_day(str(row["day"])) for row in discovery})
    test_days = sorted({_parse_day(str(row["day"])) for row in test})
    if not discovery_days or not test_days:
        raise PreflightDesignError("empty discovery or test selection")
    strict = discovery_days[-1] < test_days[0]
    if not strict:
        raise PreflightDesignError("selection is not strictly time-forward")
    return {
        "strict_time_forward": strict,
        "discovery_day_range": {
            "min": discovery_days[0].isoformat(),
            "max": discovery_days[-1].isoformat(),
            "unique_days": len(discovery_days),
        },
        "test_day_range": {
            "min": test_days[0].isoformat(),
            "max": test_days[-1].isoformat(),
            "unique_days": len(test_days),
        },
        "gap_days": (test_days[0] - discovery_days[-1]).days - 1,
    }


def select_issue_type_timeforward(
    repository: str,
    store: Mapping[int, Mapping[str, Any]],
    *,
    discovery_cases: int,
    test_cases: int,
    seed: int,
    minimum_gap_days: int,
    excluded_numbers: set[int],
) -> dict[str, Any]:
    classes = ("bug", "enhancement", "question")
    if test_cases % len(classes) != 0:
        raise PreflightDesignError("issue_type test_cases must divide evenly across three classes")
    test_per_class = test_cases // len(classes)
    exclusive: dict[str, list[dict[str, Any]]] = defaultdict(list)
    candidates: list[dict[str, Any]] = []
    for number, item in store.items():
        if number in excluded_numbers:
            continue
        if item["pull_request"] or len(str(item["body"]).strip()) < 80:
            continue
        candidates.append(dict(item))
        category = issue_type.category_for(item["labels"])
        if category != "other" and set(item["labels"]).intersection(set(classes)) == {category}:
            exclusive[category].append(dict(item))
    need = {class_name: test_per_class for class_name in classes}
    short = {
        class_name: need[class_name] - len(exclusive[class_name])
        for class_name in classes
        if len(exclusive[class_name]) < need[class_name]
    }
    if short:
        raise PreflightDesignError(f"insufficient exclusive issue-type support: {short}")
    test_start_day = _choose_test_start_day(exclusive, need)
    discovery_end_day = test_start_day - timedelta(days=minimum_gap_days + 1)
    discovery_pool = [
        row for row in candidates if _parse_day(str(row["day"])) <= discovery_end_day
    ]
    if len(discovery_pool) < discovery_cases:
        raise PreflightDesignError(
            f"only {len(discovery_pool)} older discovery candidates remain after the time split; "
            f"need {discovery_cases}"
        )
    test_by_class = {
        class_name: [
            row
            for row in exclusive[class_name]
            if _parse_day(str(row["day"])) >= test_start_day
        ]
        for class_name in classes
    }
    short_recent = {
        class_name: test_per_class - len(test_by_class[class_name])
        for class_name in classes
        if len(test_by_class[class_name]) < test_per_class
    }
    if short_recent:
        raise PreflightDesignError(
            f"recent exclusive issue-type pool is too small after the time split: {short_recent}"
        )
    for class_name in classes:
        test_by_class[class_name].sort(
            key=lambda row: _stable_rank(
                repository, seed, f"issue_type:test:{class_name}", int(row["number"])
            )
        )
    test = [
        test_by_class[class_name][index]
        for class_name in classes
        for index in range(test_per_class)
    ]
    discovery_pool.sort(
        key=lambda row: _stable_rank(repository, seed, "issue_type:discovery", int(row["number"]))
    )
    discovery = discovery_pool[:discovery_cases]
    selection = {
        "schema": "agent-compaction-github-multirepo-selection/v1",
        "family": "issue_type",
        "repository": repository,
        "seed": seed,
        "selection_uses_provider_outcomes": False,
        "filters": {
            "exclude_pull_requests": True,
            "minimum_body_characters": 80,
            "test_requires_exactly_one_of_bug_enhancement_question": True,
            "minimum_gap_days": minimum_gap_days,
        },
        "excluded_prior_record_numbers": len(excluded_numbers),
        "discovery": [
            _record_stub(repository, row, issue_type.category_for(row["labels"]))
            for row in discovery
        ],
        "test": [
            _record_stub(repository, row, issue_type.category_for(row["labels"]))
            for row in test
        ],
        "discovery_class_counts": dict(
            Counter(issue_type.category_for(row["labels"]) for row in discovery)
        ),
        "test_class_counts": dict(
            Counter(issue_type.category_for(row["labels"]) for row in test)
        ),
        "class_balance_rule": (
            "test is balanced across exclusive bug/enhancement/question cases; "
            "discovery is drawn from the older eligible pool without provider outcomes"
        ),
    }
    selection["time_forward"] = _time_forward_metadata(discovery, test)
    selection["selection_sha256"] = hashlib.sha256(
        json.dumps(selection, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return selection


def select_balanced_timeforward(
    repository: str,
    spec: workflow_family.FamilySpec,
    store: Mapping[int, Mapping[str, Any]],
    *,
    discovery_cases: int,
    test_cases: int,
    seed: int,
    minimum_gap_days: int,
    excluded_numbers: set[int],
) -> dict[str, Any]:
    if test_cases % len(spec.classes) != 0 or discovery_cases % len(spec.classes) != 0:
        raise PreflightDesignError(
            f"{spec.name} discovery_cases and test_cases must divide evenly across {len(spec.classes)} classes"
        )
    discovery_per_class = discovery_cases // len(spec.classes)
    test_per_class = test_cases // len(spec.classes)
    rows_by_class: dict[str, list[dict[str, Any]]] = {name: [] for name in spec.classes}
    for number, row in store.items():
        if number in excluded_numbers or not spec.eligible(dict(row)):
            continue
        label = spec.class_for(dict(row))
        if label in rows_by_class:
            rows_by_class[label].append(dict(row))
    need = {
        class_name: test_per_class for class_name in spec.classes
    }
    short = {
        class_name: need[class_name] - len(rows_by_class[class_name])
        for class_name in spec.classes
        if len(rows_by_class[class_name]) < need[class_name]
    }
    if short:
        raise PreflightDesignError(f"insufficient total class support for {spec.name}: {short}")
    test_start_day = _choose_test_start_day(rows_by_class, need)
    discovery_end_day = test_start_day - timedelta(days=minimum_gap_days + 1)
    discovery_by_class = {
        class_name: [
            row
            for row in rows_by_class[class_name]
            if _parse_day(str(row["day"])) <= discovery_end_day
        ]
        for class_name in spec.classes
    }
    discovery_short = {
        class_name: discovery_per_class - len(discovery_by_class[class_name])
        for class_name in spec.classes
        if len(discovery_by_class[class_name]) < discovery_per_class
    }
    if discovery_short:
        raise PreflightDesignError(
            f"older discovery pool is too small for {spec.name}: {discovery_short}"
        )
    test_by_class = {
        class_name: [
            row
            for row in rows_by_class[class_name]
            if _parse_day(str(row["day"])) >= test_start_day
        ]
        for class_name in spec.classes
    }
    recent_short = {
        class_name: test_per_class - len(test_by_class[class_name])
        for class_name in spec.classes
        if len(test_by_class[class_name]) < test_per_class
    }
    if recent_short:
        raise PreflightDesignError(
            f"recent held-out pool is too small for {spec.name}: {recent_short}"
        )
    for class_name in spec.classes:
        discovery_by_class[class_name].sort(
            key=lambda row: _stable_rank(
                repository, seed, f"{spec.name}:discovery:{class_name}", int(row["number"])
            )
        )
        test_by_class[class_name].sort(
            key=lambda row: _stable_rank(
                repository, seed, f"{spec.name}:test:{class_name}", int(row["number"])
            )
        )
    discovery = [
        discovery_by_class[class_name][index]
        for class_name in spec.classes
        for index in range(discovery_per_class)
    ]
    test = [
        test_by_class[class_name][index]
        for class_name in spec.classes
        for index in range(test_per_class)
    ]
    selection = {
        "schema": "agent-compaction-github-multirepo-selection/v1",
        "family": spec.name,
        "repository": repository,
        "seed": seed,
        "selection_uses_provider_outcomes": False,
        "filters": {
            "minimum_gap_days": minimum_gap_days,
            "family_eligibility": spec.name,
        },
        "excluded_prior_record_numbers": len(excluded_numbers),
        "discovery": [_record_stub(repository, row, spec.class_for(row)) for row in discovery],
        "test": [_record_stub(repository, row, spec.class_for(row)) for row in test],
        "discovery_class_counts": dict(Counter(spec.class_for(row) for row in discovery)),
        "test_class_counts": dict(Counter(spec.class_for(row) for row in test)),
        "class_balance_rule": (
            "fixed class order with round-robin allocation before provider execution, "
            "subject to a strict time-forward split"
        ),
    }
    selection["time_forward"] = _time_forward_metadata(discovery, test)
    selection["selection_sha256"] = hashlib.sha256(
        json.dumps(selection, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return selection


def prior_records(default_repository: str = LEGACY_DEFAULT_REPO) -> dict[str, set[int]]:
    """Collect previously used GitHub record numbers with repo-aware fallbacks."""

    excluded: dict[str, set[int]] = defaultdict(set)
    for root in RESULT_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.json"):
            if root.name == "github_workflow_families" and path.name == "preflight.json":
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue

            def visit(value: Any, *, current_repo: str | None = None, key: str = "") -> None:
                repo = current_repo
                if isinstance(value, dict):
                    inferred = (
                        value.get("repository")
                        or value.get("repo")
                        or infer_repository(value)
                    )
                    next_repo = str(inferred) if inferred else repo
                    for child_key, child in value.items():
                        visit(child, current_repo=next_repo, key=child_key)
                    return
                if isinstance(value, list):
                    for child in value:
                        visit(child, current_repo=repo, key=key)
                    return
                if key in {"issue_number", "record_number"}:
                    try:
                        excluded[repo or default_repository].add(int(value))
                    except (TypeError, ValueError):
                        return

            visit(payload)
    return {repo: values for repo, values in excluded.items()}


def _family_names(requested: Sequence[str]) -> tuple[str, ...]:
    families = _split_csv(requested)
    if not families:
        return ("issue_type", "pr_outcome", "backlog_attention")
    return families


def _repositories(requested: Sequence[str]) -> tuple[str, ...]:
    return _split_csv(requested)


def design_preflight(
    *,
    snapshot_paths: Sequence[Path],
    repositories: Sequence[str] = (),
    families: Sequence[str] = ("issue_type", "pr_outcome", "backlog_attention"),
    discovery_cases: int = 132,
    test_cases: int = 30,
    seed: int = 20260801,
    minimum_gap_days: int = 0,
    minimum_complete_repos: int = 3,
    exclude_existing_paper_results: bool = True,
) -> dict[str, Any]:
    stores, snapshot_audits, repo_audits = load_snapshot_stores(snapshot_paths)
    requested_repositories = tuple(repositories) or tuple(sorted(stores))
    unknown = sorted(set(requested_repositories) - set(stores))
    if unknown:
        raise PreflightDesignError(f"requested repositories are unavailable: {unknown}")

    excluded = prior_records() if exclude_existing_paper_results else {}
    family_names = tuple(families)
    unsupported = sorted(set(family_names) - {"issue_type", *workflow_family.FAMILIES})
    if unsupported:
        raise PreflightDesignError(f"unsupported families: {unsupported}")

    repo_results: dict[str, Any] = {}
    complete_repos = 0
    for repository in requested_repositories:
        store = stores[repository]
        family_results: dict[str, Any] = {}
        complete = True
        for family_name in family_names:
            try:
                if family_name == "issue_type":
                    selection = select_issue_type_timeforward(
                        repository,
                        store,
                        discovery_cases=discovery_cases,
                        test_cases=test_cases,
                        seed=seed,
                        minimum_gap_days=minimum_gap_days,
                        excluded_numbers=excluded.get(repository, set()),
                    )
                else:
                    selection = select_balanced_timeforward(
                        repository,
                        workflow_family.FAMILIES[family_name],
                        store,
                        discovery_cases=discovery_cases,
                        test_cases=test_cases,
                        seed=seed,
                        minimum_gap_days=minimum_gap_days,
                        excluded_numbers=excluded.get(repository, set()),
                    )
            except PreflightDesignError as exc:
                complete = False
                family_results[family_name] = {
                    "status": "unavailable",
                    "reason": str(exc),
                }
            else:
                family_results[family_name] = {
                    "status": "selected",
                    "selection": selection,
                }
        repo_results[repository] = {
            "audit": repo_audits[repository],
            "families": family_results,
            "complete_for_requested_families": complete,
        }
        if complete:
            complete_repos += 1

    payload = {
        "schema": "agent-compaction-github-multirepo-preflight/v1",
        "status": "designed_not_run",
        "provider_calls_executed": 0,
        "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "real_public_records": True,
        "simulated": False,
        "resolved_config": {
            "snapshot_paths": [_display_path(path) for path in snapshot_paths],
            "repositories": list(requested_repositories),
            "families": list(family_names),
            "discovery_cases": discovery_cases,
            "test_cases": test_cases,
            "minimum_gap_days": minimum_gap_days,
            "minimum_complete_repos": minimum_complete_repos,
            "seed": seed,
            "exclude_existing_paper_results": exclude_existing_paper_results,
        },
        "sources": {
            "snapshots": snapshot_audits,
            "repositories_discovered": sorted(stores),
        },
        "repositories": repo_results,
        "global_checks": {
            "complete_repo_count": complete_repos,
            "minimum_complete_repos": minimum_complete_repos,
            "satisfies_minimum_complete_repos": complete_repos >= minimum_complete_repos,
            "all_selected_families_time_forward": all(
                family_result.get("status") != "selected"
                or family_result["selection"]["time_forward"]["strict_time_forward"]
                for repo in repo_results.values()
                for family_result in repo["families"].values()
            ),
        },
    }
    payload["preflight_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return payload


def write_preflight(payload: Mapping[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot",
        action="append",
        type=Path,
        default=[],
        help="Parquet snapshot path; may be repeated",
    )
    parser.add_argument(
        "--repos",
        action="append",
        default=[],
        help="Comma-separated owner/name repositories to include",
    )
    parser.add_argument(
        "--families",
        action="append",
        default=[],
        help="Comma-separated family names from issue_type, pr_outcome, backlog_attention",
    )
    parser.add_argument("--discovery-cases", type=int, default=132)
    parser.add_argument("--test-cases", type=int, default=30)
    parser.add_argument("--minimum-gap-days", type=int, default=0)
    parser.add_argument("--minimum-complete-repos", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20260801)
    parser.add_argument(
        "--exclude-existing-paper-results",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="exclude records already used by checked-in GitHub paper results",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    snapshots = tuple(args.snapshot) or (issue_type.DATA_PATH,)
    payload = design_preflight(
        snapshot_paths=snapshots,
        repositories=_repositories(args.repos),
        families=_family_names(args.families),
        discovery_cases=args.discovery_cases,
        test_cases=args.test_cases,
        seed=args.seed,
        minimum_gap_days=args.minimum_gap_days,
        minimum_complete_repos=args.minimum_complete_repos,
        exclude_existing_paper_results=bool(args.exclude_existing_paper_results),
    )
    write_preflight(payload, args.out)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["global_checks"]["satisfies_minimum_complete_repos"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
