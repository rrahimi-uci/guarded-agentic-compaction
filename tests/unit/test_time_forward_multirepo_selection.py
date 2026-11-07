"""Provider-free tests for the multi-repository generalisation of the time-forward PR-outcome study.

Covers author-distinct selection, disjointness from discovery authors, shortfall handling (n < 106
refuses to run), repository-qualified exclusions, the per-group calibration schema, and that the
default (single-repository) behaviour still reproduces the retained selection digest. No network,
no provider call; synthetic stores only (plus the retained hf snapshot for the default-behaviour
regression).
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / "src", ROOT / "paper" / "scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import github_time_forward_preflight as pre  # noqa: E402
import github_workflow_family_study as fam  # noqa: E402
import time_forward_pr_outcome_study as study  # noqa: E402

RETAINED_DIGEST = "09868598d603225325466cff8d5bcf12b85530ee4656f521e4070ee21336a2bf"
RETAINED_OUT = ROOT / "paper/results/time_forward/pr_outcome"
STATES = (("open", None), ("closed", None), ("closed", "2026-02-02T00:00:00Z"))


def _row(number: int, login: str | None, *, day: int = 1, kind: int | None = None, bot: bool = False) -> dict[str, Any]:
    state, merged = STATES[(number if kind is None else kind) % 3]
    return {
        "number": number, "title": f"PR {number}", "state": state, "id": number, "comments": [], "assignees": [], "labels": [],
        "user": ({"login": login, "type": "Bot" if bot else "User"} if login else None),
        "created_at": f"2026-03-{1 + day % 28:02d}T00:00:00+00:00", "updated_at": f"2026-03-{1 + day % 28:02d}T01:00:00+00:00",
        "pull_request": {"url": f"https://api.github.com/repos/octo/example/pulls/{number}", "merged_at": merged or ""},
        "body": "x" * 100,
    }


def _store(n_authors: int, per_author: int = 2) -> dict[int, dict[str, Any]]:
    store: dict[int, dict[str, Any]] = {}
    number = 1000
    for a in range(n_authors):
        for k in range(per_author):
            store[number] = _row(number, f"User{a}" if k == 0 else f"user{a}", day=a + k, kind=a + k)  # case differs: same author
            number += 1
    return store


def _authors(store, numbers):
    return [study.author_of(store[n]).lower() for n in numbers]


# ---- author-distinct selection ------------------------------------------------------------------


def test_author_unit_selects_one_pr_per_author_lowest_rank_first() -> None:
    store = _store(150)
    sel = study.select_multirepo(fam, store, set(), repo_tag="octo/example", unit="author", calibration_n=120, with_test=False, with_discovery=False)
    assert sel["status"] == "selected" and sel["calibration_n"] == 120 and sel["calibration_shortfall"] == 0
    authors = _authors(store, sel["calibration"])
    assert len(set(authors)) == len(authors) == 120  # pairwise distinct, case-insensitive
    assert sel["authors_pairwise_distinct"] is True and sel["calibration_distinct_authors"] == 120
    # each author's chosen record is that author's lowest-rank record
    rank = lambda n: study._rank(n, "octo/example")  # noqa: E731
    for n in sel["calibration"]:
        mine = [m for m, r in store.items() if study.author_of(r).lower() == study.author_of(store[n]).lower()]
        assert n == min(mine, key=rank)
    # and the order is the global rank order
    assert sel["calibration"] == sorted(sel["calibration"], key=rank)
    assert sel["rank_tag"] == "multirepo-e2e:octo/example:pr_outcome:<number>"


def test_record_unit_keeps_duplicate_authors() -> None:
    store = _store(40)
    sel = study.select_multirepo(fam, store, set(), repo_tag="octo/example", unit="record", calibration_n=60, with_test=False, with_discovery=False, min_n=10)
    assert len(sel["calibration"]) == 60 and sel["calibration_distinct_authors"] < 60 and sel["authors_pairwise_distinct"] is None


def test_hash_tag_changes_rank_and_default_tag_is_the_retained_one() -> None:
    assert study._rank(7) == study._rank(7, None) != study._rank(7, "octo/example")
    import hashlib

    assert study._rank(7, "octo/example") == hashlib.sha256(b"multirepo-e2e:octo/example:pr_outcome:7").hexdigest()
    assert study._rank(7) == hashlib.sha256(b"time-forward:pr_outcome:7").hexdigest()


def test_records_without_login_are_skipped_not_dropped_silently() -> None:
    store = _store(130)
    for n in list(store)[:6]:
        store[n]["user"] = None
    sel = study.select_multirepo(fam, store, set(), repo_tag="octo/example", unit="author", calibration_n=200, with_test=False, with_discovery=False)
    assert sel["records_without_login_skipped"] >= 1
    assert all(study.author_of(store[n]) for n in sel["calibration"])


# ---- disjointness from discovery ----------------------------------------------------------------


def test_calibration_authors_disjoint_from_new_discovery_split() -> None:
    store = _store(400, per_author=2)
    sel = study.select_multirepo(fam, store, set(), repo_tag="octo/example", unit="author", calibration_n=200, with_test=False, with_discovery=True)
    assert len(sel["discovery"]) == 132 and sel["discovery_shortfall"] == 0 and sel["calibration_n"] == 200
    disc_authors = set(_authors(store, sel["discovery"]))
    cal_authors = set(_authors(store, sel["calibration"]))
    assert not (disc_authors & cal_authors)
    assert not (set(sel["discovery"]) & set(sel["calibration"])) and sel["disjoint"] and sel["author_disjoint_from_discovery"]
    assert sel["discovery_class_counts"] == {"open": 44, "closed_unmerged": 44, "merged": 44}


def test_discovery_shortfall_is_filled_in_rank_order_and_recorded() -> None:
    store = {n: _row(n, f"a{n}", kind=0 if n % 10 else 1) for n in range(1000, 1200)}  # almost all one class
    sel = study.select_multirepo(fam, store, set(), repo_tag="octo/example", unit="author", calibration_n=200, with_test=False, with_discovery=True)
    assert len(sel["discovery"]) == 132 and sel["discovery_filled_in_rank_order"] > 0
    assert sel["discovery_class_counts"].get("merged", 0) == 0 and sel["discovery_class_counts"]["closed_unmerged"] == 20
    assert sel["discovery_filled_in_rank_order"] == 68 and sel["discovery_shortfall"] == 0 and sel["calibration_n"] == 68  # 200 - 132 left


def test_supplied_author_file_is_excluded(tmp_path: Path) -> None:
    store = _store(260, per_author=1)
    blocked = {f"user{a}" for a in range(0, 260, 2)}  # logins, any case
    path = tmp_path / "authors.txt"
    path.write_text("\n".join(sorted(blocked)) + "\n")
    assert study.load_discovery_authors(path, store) == blocked
    sel = study.select_multirepo(fam, store, set(), repo_tag="octo/example", unit="author", calibration_n=200, with_test=False, with_discovery=False,
                                 excluded_authors=study.load_discovery_authors(path, store))
    assert not (set(_authors(store, sel["calibration"])) & blocked) and sel["calibration_n"] == 130
    assert sel["author_disjoint_from_discovery"] and sel["excluded_authors_supplied"] == len(blocked)


def test_discovery_authors_file_formats(tmp_path: Path) -> None:
    store = _store(10, per_author=1)
    lst = tmp_path / "list.json"
    lst.write_text(json.dumps(["User1", "user2"]))
    assert study.load_discovery_authors(lst, store) == {"user1", "user2"}
    selection = tmp_path / "selection.json"
    selection.write_text(json.dumps({"discovery": [1000, 1003]}))
    assert study.load_discovery_authors(selection, store) == {"user0", "user3"}
    selection.write_text(json.dumps({"discovery": [999999]}))
    with pytest.raises(RuntimeError):
        study.load_discovery_authors(selection, store)


# ---- shortfall ------------------------------------------------------------------------------------


def test_shortfall_below_floor_is_recorded_and_refuses() -> None:
    store = _store(100)
    sel = study.select_multirepo(fam, store, set(), repo_tag="octo/example", unit="author", calibration_n=200, with_test=False, with_discovery=False)
    assert sel["calibration_n"] == 100 and sel["calibration_available"] == 100 and sel["calibration_shortfall"] == 100
    assert sel["status"] == "shortfall_no_run" and sel["min_calibration_n"] == 106


def test_shortfall_above_floor_runs_with_what_is_available() -> None:
    store = _store(150)
    sel = study.select_multirepo(fam, store, set(), repo_tag="octo/example", unit="author", calibration_n=200, with_test=False, with_discovery=False)
    assert sel["calibration_n"] == 150 and sel["calibration_shortfall"] == 50 and sel["status"] == "selected"
    boundary = study.select_multirepo(fam, _store(106), set(), repo_tag="octo/example", unit="author", calibration_n=200, with_test=False, with_discovery=False)
    assert boundary["calibration_n"] == 106 and boundary["status"] == "selected"
    below = study.select_multirepo(fam, _store(105), set(), repo_tag="octo/example", unit="author", calibration_n=200, with_test=False, with_discovery=False)
    assert below["status"] == "shortfall_no_run"


@pytest.fixture()
def restore_snapshot_binding():
    import github_live_study as fixed

    saved = (fam.DATA_PATH, fixed.DATA_PATH, fixed.HF_REVISION, fixed.HF_PARQUET_SHA256, fixed.HF_DATASET)
    yield
    fam.DATA_PATH, fixed.DATA_PATH, fixed.HF_REVISION, fixed.HF_PARQUET_SHA256, fixed.HF_DATASET = saved


def _write_snapshot(directory: Path, store: dict[int, dict[str, Any]]) -> None:
    import pandas as pd

    directory.mkdir(parents=True, exist_ok=True)
    rows = []
    for r in store.values():
        r = dict(r)
        r["user"] = r["user"] or {"login": None, "type": "User"}
        rows.append(r)
    pd.DataFrame(rows).to_parquet(directory / "snapshot.parquet")
    (directory / "source_manifest.json").write_text(json.dumps({"repository": "octo/example", "parquet_sha256": "0" * 64, "created_after_utc_day": "2026-01-01"}))


def _args(tmp_path: Path, **over: Any) -> SimpleNamespace:
    base = dict(phase="selection", approved_spend_usd=None, pilot=0, concurrency=4, dry_run=False, out=tmp_path / "out", snapshot_dir=tmp_path / "snap",
                registry=None, unit="author", calibration_n=200, no_test=True, arms="compiled,baseline,manual", repo_tag="octo/example",
                discovery_authors_file=None, batch_size=0, qualified_exclusion=False)
    base.update(over)
    return SimpleNamespace(**base)


def test_main_writes_shortfall_selection_and_refuses_live_phases(tmp_path: Path, restore_snapshot_binding, capsys) -> None:
    _write_snapshot(tmp_path / "snap", _store(80, per_author=1))
    # a frozen registry means no discovery split, so all 80 authors are calibration candidates: 80 < 106
    reg = tmp_path / "reg"
    reg.mkdir()
    assert asyncio.run(study.main_async(_args(tmp_path, registry=reg))) == 0  # selection phase records the result
    sel = json.loads((tmp_path / "out" / "selection.json").read_text())
    assert sel["status"] == "shortfall_no_run" and sel["calibration_n"] == 80 and sel["requested_calibration_n"] == 200
    for phase in ("discovery", "calibrate", "test", "all"):
        assert asyncio.run(study.main_async(_args(tmp_path, registry=reg, phase=phase, dry_run=True))) == 3
    assert "SHORTFALL" in capsys.readouterr().out
    assert not (tmp_path / "out" / "calibration_checkpoint.json").exists() and not (tmp_path / "out" / "ledger.json").exists()


def test_main_rejects_mismatched_repo_tag(tmp_path: Path, restore_snapshot_binding) -> None:
    _write_snapshot(tmp_path / "snap", _store(10, per_author=1))
    with pytest.raises(RuntimeError, match="does not match"):
        asyncio.run(study.main_async(_args(tmp_path, repo_tag="other/repo")))


def test_main_selects_and_dry_runs_with_frozen_registry(tmp_path: Path, restore_snapshot_binding, capsys) -> None:
    _write_snapshot(tmp_path / "snap", _store(130, per_author=1))
    reg = tmp_path / "reg"
    reg.mkdir()
    afile = tmp_path / "authors.json"
    afile.write_text(json.dumps(["user0", "user1"]))
    args = _args(tmp_path, registry=reg, discovery_authors_file=afile, phase="calibrate", dry_run=True)
    assert asyncio.run(study.main_async(args)) == 0
    out = capsys.readouterr().out.strip().splitlines()[-1]
    report = json.loads(out)
    assert report["discovery_skipped"] and report["test_skipped"] and report["arms"] == ["compiled", "baseline", "manual"] and report["records"]["calibration"] == 128
    sel = json.loads((tmp_path / "out" / "selection.json").read_text())
    assert sel["status"] == "selected" and sel["registry"] and sel["test"] == [] and sel["discovery"] == []
    assert len(sel["calibration_meta"]) == 128 and {"number", "author", "created_day", "class"} <= set(sel["calibration_meta"][0])


# ---- repository-qualified exclusions ---------------------------------------------------------------


@pytest.fixture()
def results_tree(tmp_path: Path, monkeypatch):
    res, exp = tmp_path / "paper/results", tmp_path / "experiments"

    def put(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload))

    put(res / "github_multirepo_x/repos/pandas-dev__pandas/results.json", {"results": [{"issue_number": 1}, {"issue_number": 2}]})
    put(res / "github_multirepo_x/results.json", {"repositories": {"pandas-dev/pandas": {"results": [{"issue_number": 3}]},
                                                                  "streamlit/streamlit": {"results": [{"issue_number": 4}]}}})
    put(res / "legacy/hf.json", {"dataset": "huggingface/datasets", "results": [{"issue_number": 5}]})
    put(res / "unnamed/other.json", {"results": [{"issue_number": 9}]})
    put(res / "mixed/sel.json", {"selection": {"repository": "pandas-dev/pandas", "discovery": [10, 11], "number": 12},
                                 "other": {"repository": "psf/requests", "discovery": [20], "number": 21}})
    put(res / "multirepo_end_to_end/pandas-dev__pandas/selection.json", {"repository": "pandas-dev/pandas", "discovery": [30], "issue_number": 31})
    put(res / "datasets/skipped/pandas-dev__pandas.json", {"repository": "pandas-dev/pandas", "number": 40})
    put(exp / "foo/checkpoint.json", {"repository": "pandas-dev/pandas", "results": [{"record_number": 6}], "calibration": [7, 8]})
    put(exp / "bar/checkpoint.json", {"repo": "pytorch/pytorch", "results": [{"record_number": 50}]})
    monkeypatch.setattr(pre, "ROOT", tmp_path)
    monkeypatch.setattr(pre, "RESULTS", res)
    monkeypatch.setattr(pre, "EXPERIMENTS", exp)
    monkeypatch.setattr(pre, "OWN_STUDY_DIR", res / "multirepo_end_to_end")
    return tmp_path


def test_exclusions_are_repository_qualified(results_tree: Path) -> None:
    pandas, _ = pre.used_records("pandas-dev/pandas")
    assert pandas == {1, 2, 3, 6, 7, 8, 10, 11, 12}  # own study dir, datasets/, other repos' and unnamed files excluded
    streamlit, _ = pre.used_records("streamlit/streamlit")
    assert streamlit == {4}
    requests, _ = pre.used_records("psf/requests")
    assert requests == {20, 21}
    pytorch, _ = pre.used_records("pytorch/pytorch")
    assert pytorch == {50}
    unknown, _ = pre.used_records("octo/example")
    assert unknown == set()


def test_huggingface_keeps_legacy_behaviour_unless_qualified_requested(results_tree: Path) -> None:
    legacy, _ = pre.used_records("huggingface/datasets")
    default, _ = pre.used_records()
    assert legacy == default
    # legacy: only paper/results, only files containing huggingface/datasets, github-issue or issue_number, every
    # such number whatever the repository (collisions included), plain number lists not read, no own-study exemption
    assert legacy == {1, 2, 3, 4, 5, 9, 31}
    qualified, _ = pre.used_records("huggingface/datasets", qualified=True)
    assert qualified == {5}


def test_exclude_paths_skips_a_studys_own_output(results_tree: Path) -> None:
    skipped, _ = pre.used_records("pandas-dev/pandas", exclude_paths=[results_tree / "experiments/foo"])
    assert not ({6, 7, 8} & skipped) and {1, 2, 3} <= skipped
    legacy, _ = pre.used_records(exclude_paths=[results_tree / "paper/results/legacy"])
    assert 5 not in legacy


def test_preflight_pool_report_counts_authors_days_and_projection(results_tree: Path) -> None:
    rows = list(_store(220, per_author=2).values())
    used = {rows[0]["number"], rows[1]["number"]}  # both records of author 0 are used
    report = pre.pool_report(fam, rows, used, "octo/example", None)
    assert report["pool_size"] == 438 and report["distinct_authors"] == 219 == report["author_distinct_prs_available"]
    assert sum(report["class_counts"].values()) == 438 and report["distinct_days"] > 1
    proj = report["projected_selection"]
    assert proj["registry_reuse_no_discovery"]["calibration_n"] == 200 and proj["registry_reuse_no_discovery"]["status"] == "selected"
    assert proj["with_new_discovery_split"]["discovery_n"] == 132
    # 438 - 132 discovery records leaves authors for fewer than 200 groups once discovery authors are blocked
    assert proj["with_new_discovery_split"]["calibration_n"] < 200
    blocked = {s.lower() for s in (study.author_of(r) for r in rows[2:60])}
    smaller = pre.pool_report(fam, rows, used, "octo/example", blocked)
    assert smaller["projected_selection"]["registry_reuse_no_discovery"]["calibration_n"] <= report["projected_selection"]["registry_reuse_no_discovery"]["calibration_n"]


# ---- per-group schema, resume, no retries ----------------------------------------------------------


class _FakeResult:
    def __init__(self, condition: str, number: int, *, overall: bool, outcome: str, reasons=(), requests=1, cost=0.001) -> None:
        self.metrics = {"estimated_cost_usd": cost, "requests": requests, "total_tokens": 100 * requests, "wall_latency_ms": 10.0 * requests}
        self._d = {"condition": condition, "issue_number": number, "metrics": self.metrics, "quality": {"overall": overall},
                   "dispatch": ({"outcome": outcome, "reasons": list(reasons)} if outcome else {})}

    def public_dict(self) -> dict[str, Any]:
        return dict(self._d)


def _fake_fam(calls: list[tuple[str, list[int]]], *, fail: set[tuple[str, int]] = frozenset(), miss: set[tuple[str, int]] = frozenset()):
    async def run_batch(spec, rows, *, condition, **kwargs):
        numbers = [int(r["number"]) for r in rows]
        calls.append((condition, numbers))
        results, failures = [], []
        for n in numbers:
            if (condition, n) in fail:
                failures.append({"condition": condition, "record_number": n, "error": "TimeoutError: "})
            elif condition == "baseline":
                results.append(_FakeResult(condition, n, overall=True, outcome="", requests=4))
            elif condition == "compiled":
                if n % 5 == 0:
                    results.append(_FakeResult(condition, n, overall=True, outcome="ABSTAINED", reasons=["verifier abstained"], requests=4))
                elif n % 7 == 0:
                    results.append(_FakeResult(condition, n, overall=True, outcome="REJECTED", reasons=["manifest mismatch"], requests=4))
                else:
                    results.append(_FakeResult(condition, n, overall=(condition, n) not in miss, outcome="COMPACTED"))
            else:
                results.append(_FakeResult(condition, n, overall=True, outcome="EXECUTED"))
        return results, failures

    return SimpleNamespace(FAMILIES=fam.FAMILIES, run_batch=run_batch, make_manual_plan=lambda *a, **k: object())


def _calibrate(tmp_path: Path, store, selection, fake, *, arms=("compiled", "baseline", "manual"), pilot=0, cap=5.0, monkeypatch=None):
    import guarded_agentic_compaction.runtime.manual as manual

    monkeypatch.setattr(manual, "ManualPreModelRunner", lambda *a, **k: object())
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    ledger = study.Ledger(out / "ledger.json", cap)
    return asyncio.run(study.calibrate_arms(
        fam=fake, spec=fam.FAMILIES["pr_outcome"], store=store, selection=selection, arms=arms, registry=object(), source_manifest=object(),
        continuation_manifest=object(), baseline_manifest=object(), tools=(), catalog=object(), processor=object(), ledger=ledger, out=out,
        run_meta={"x": 1}, concurrency=2, pilot=pilot, batch_size=8, repo="octo/example")), ledger, out


def test_calibration_groups_schema_and_semantics(tmp_path: Path, monkeypatch) -> None:
    store = _store(30, per_author=1)
    numbers = sorted(store)[:20]
    selection = {"calibration": numbers, "digest": "d"}
    calls: list = []
    n_miss = next(n for n in numbers if n % 5 and n % 7)
    done, ledger, out = _calibrate(tmp_path, store, selection, _fake_fam(calls, miss={("compiled", n_miss)}), monkeypatch=monkeypatch)
    groups = json.loads((out / "calibration_groups.json").read_text())
    assert isinstance(groups, list) and [g["number"] for g in groups] == numbers
    keys = {"eligible", "dispatched", "verifier_abstained", "contract_met", "fallback", "requests", "tokens", "latency_ms", "cost_usd"}
    for g in groups:
        assert {"repo", "number", "author", "created_day", "class", "arms"} <= set(g) and g["repo"] == "octo/example"
        assert g["class"] in ("open", "merged", "closed_unmerged") and g["author"] == study.author_of(store[g["number"]])
        assert set(g["arms"]) == {"compiled", "baseline", "manual"} and all(keys <= set(a) for a in g["arms"].values())
    by = {g["number"]: g["arms"] for g in groups}
    n_ok = next(n for n in numbers if n % 5 and n % 7 and n != n_miss)
    assert by[n_ok]["compiled"] == {"eligible": True, "dispatched": True, "verifier_abstained": False, "contract_met": True, "fallback": False,
                                    "requests": 1, "tokens": 100, "latency_ms": 10.0, "cost_usd": 0.001, "failed": False}
    assert by[n_miss]["compiled"]["contract_met"] is False and by[n_miss]["compiled"]["dispatched"] is True  # a violation
    abstained = next(n for n in numbers if n % 5 == 0)
    assert by[abstained]["compiled"]["verifier_abstained"] and not by[abstained]["compiled"]["dispatched"] and by[abstained]["compiled"]["fallback"]
    assert by[abstained]["compiled"]["requests"] == 4
    inelig = next(n for n in numbers if n % 7 == 0 and n % 5)
    assert by[inelig]["compiled"]["eligible"] is False
    assert by[numbers[0]]["baseline"]["dispatched"] is False and by[numbers[0]]["baseline"]["requests"] == 4 and by[numbers[0]]["baseline"]["fallback"] is False
    assert by[numbers[0]]["manual"]["dispatched"] is True
    assert ledger.state["spent_usd"] > 0 and len(done["results"]) == 60
    assert sorted({c for c, _ in calls}) == ["baseline", "compiled", "manual_pre_model"]


def test_failures_are_final_and_resume_does_not_rerun(tmp_path: Path, monkeypatch) -> None:
    store = _store(30, per_author=1)
    numbers = sorted(store)[:10]
    selection = {"calibration": numbers, "digest": "d"}
    calls: list = []
    fake = _fake_fam(calls, fail={("compiled", numbers[2])})
    done, _, out = _calibrate(tmp_path, store, selection, fake, arms=("compiled", "baseline"), monkeypatch=monkeypatch)
    g = {x["number"]: x for x in json.loads((out / "calibration_groups.json").read_text())}[numbers[2]]
    assert g["arms"]["compiled"]["failed"] is True and g["arms"]["compiled"]["contract_met"] is False and "TimeoutError" in g["arms"]["compiled"]["error"]
    assert g["arms"]["baseline"]["contract_met"] is True
    before = len(calls)
    done2, _, _ = _calibrate(tmp_path, store, selection, fake, arms=("compiled", "baseline"), monkeypatch=monkeypatch)
    assert len(calls) == before  # nothing re-run, the failed episode was not retried
    assert len(done2["results"]) == len(done["results"]) == 19 and len(done2["failures"]) == 1


def test_pilot_limits_groups_and_batches_by_eight(tmp_path: Path, monkeypatch) -> None:
    store = _store(30, per_author=1)
    numbers = sorted(store)[:20]
    calls: list = []
    done, _, out = _calibrate(tmp_path, store, {"calibration": numbers, "digest": "d"}, _fake_fam(calls), arms=("compiled",), pilot=10, monkeypatch=monkeypatch)
    assert len(json.loads((out / "calibration_groups.json").read_text())) == 10
    assert [len(n) for _, n in calls] == [8, 2]  # batches of 8, checkpointed between them


def test_certificate_uses_only_the_compiled_arm() -> None:
    results = [
        {"condition": "compiled", "issue_number": 1, "quality": {"overall": True}, "dispatch": {"outcome": "COMPACTED"}},
        {"condition": "compiled", "issue_number": 2, "quality": {"overall": False}, "dispatch": {"outcome": "COMPACTED"}},
        {"condition": "baseline", "issue_number": 1, "quality": {"overall": False}, "dispatch": {}},
        {"condition": "manual_pre_model", "issue_number": 2, "quality": {"overall": True}, "dispatch": {"outcome": "EXECUTED"}},
    ]
    c = study.certificate(results)
    assert c["n_eligible"] == 2 and c["violations"] == 1 and c["violation_records"] == [2]
    legacy = [{k: v for k, v in r.items() if k != "condition"} for r in results[:2]]  # checkpoints without the field still work
    assert study.certificate(legacy)["violations"] == 1


# ---- default behaviour unchanged -------------------------------------------------------------------


def test_default_selection_reproduces_the_retained_digest(restore_snapshot_binding) -> None:
    """The legacy ``select`` on the retained snapshot reproduces selection.json (digest 09868598...).

    The October ``used`` set cannot be rebuilt from today's results (later studies name more record
    numbers), so the stand-in marks every record outside the 324 selected ones as used; the rank
    structure that determines the splits is unchanged.
    """
    retained = json.loads((RETAINED_OUT / "selection.json").read_text())
    assert retained["digest"] == RETAINED_DIGEST
    fam_, _, _ = study.bind_snapshot()
    store, _ = fam_.load_store()
    keep = set(retained["test"]) | set(retained["discovery"]) | set(retained["calibration"])
    sel = study.select(fam_, store, set(store) - keep)
    assert sel["digest"] == RETAINED_DIGEST
    for k in ("test", "discovery", "calibration", "test_class_counts", "discovery_class_counts", "calibration_class_counts", "disjoint", "schema", "rule"):
        assert sel[k] == retained[k]
    assert "status" not in sel and "unit" not in sel  # the legacy selection record has no new keys


def test_default_dry_run_prints_the_legacy_report(capsys, restore_snapshot_binding) -> None:
    rc = study.main(["--phase", "calibrate", "--dry-run"])
    out = capsys.readouterr().out.strip().splitlines()
    assert rc == 0 and f"selection digest {RETAINED_DIGEST}" in out[0]
    assert set(json.loads(out[-1])) == {"dry_run", "phase", "records", "cap", "spent"}
    assert json.loads(out[-1])["records"] == {"test": 60, "discovery": 132, "calibration": 132}
