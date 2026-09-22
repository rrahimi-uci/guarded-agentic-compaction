"""Pin the numbers ``iclr_revision_statistics.py`` derives from retained results.

Every expectation below is a value the ICLR manuscript quotes; a change here is a
change to the paper and must be reviewed as one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import iclr_revision_statistics as stats  # noqa: E402


@pytest.fixture(scope="module")
def absolute():
    return stats.cmd_absolute()


@pytest.fixture(scope="module")
def paired():
    return stats.cmd_paired()


@pytest.fixture(scope="module")
def multiplicity():
    return stats.cmd_multiplicity()


@pytest.fixture(scope="module")
def frontier():
    return stats.cmd_frontier()


@pytest.fixture(scope="module")
def overlap():
    return stats.cmd_overlap()


@pytest.fixture(scope="module")
def clusters():
    return stats.cmd_clusters()


def test_exact_bound_arithmetic() -> None:
    assert stats.cp_upper(0, 92, 1 - stats.gamma_for(1)) == pytest.approx(0.049809, abs=1e-6)
    assert stats.cp_upper(0, 91, 1 - stats.gamma_for(1)) == pytest.approx(0.050342, abs=1e-6)
    assert stats.cp_upper(0, 92, 1 - stats.gamma_for(2)) == pytest.approx(0.056941, abs=1e-6)
    assert stats.cp_upper(0, 106, 1 - stats.gamma_for(2)) == pytest.approx(0.049610, abs=1e-6)
    assert [stats.n_min(m) for m in (1, 2, 3, 4, 8, 16)] == [92, 106, 114, 119, 133, 146]
    assert stats.one_sided_upper_95(0, 90) == pytest.approx(0.0327, abs=5e-4)


def test_absolute_means_and_medians(absolute) -> None:
    fam = absolute["families"]
    def mm(f, arm, m):
        b = fam[f]["arms"][arm][m]
        return round(b["mean"], 1), round(b["median"], 1)
    assert mm("issue_type", "baseline", "requests") == (4.0, 4.0)
    assert mm("issue_type", "baseline", "total_tokens") == (4259.4, 4320.0)
    assert mm("issue_type", "compiled", "total_tokens") == (2576.5, 2602.5)
    assert mm("issue_type", "manual", "total_tokens") == (1780.8, 1734.0)
    assert mm("pr_outcome", "baseline", "total_tokens") == (2718.2, 2676.5)
    assert mm("pr_outcome", "compiled", "total_tokens") == (521.5, 461.5)
    assert mm("backlog_attention", "baseline", "requests") == (4.0, 4.0)
    assert fam["backlog_attention"]["arms"]["baseline"]["requests"]["mean"] == pytest.approx(3.9667, abs=1e-3)
    assert mm("backlog_attention", "compiled", "total_tokens") == (529.9, 468.0)
    assert fam["pr_outcome"]["arms"]["compiled"]["estimated_cost_usd"]["mean"] == pytest.approx(1.68e-4, abs=1e-6)
    assert fam["backlog_attention"]["arms"]["baseline"]["exact"] == 29
    assert sum(fam[f]["arms"]["compiled"]["exact"] for f in fam) == 90
    assert absolute["pooled"]["baseline"]["requests"]["sum"] == 359
    assert absolute["pooled"]["compiled"]["requests"]["sum"] == 120


def test_paired_reproduces_retained_intervals(paired) -> None:
    pr = paired["families"]["pr_outcome"]["compiled"]
    assert pr["total_tokens"]["mean_difference"] == pytest.approx(-2196.7, abs=0.1)
    assert pr["total_tokens"]["mean_ci95"] == pytest.approx([-2211.1, -2182.5], abs=0.1)
    assert pr["wall_latency_ms"]["mean_ci95"] == pytest.approx([-4499, -3346], abs=1.0)
    bl = paired["families"]["backlog_attention"]["compiled"]
    assert bl["total_tokens"]["mean_ci95"] == pytest.approx([-2366.0, -2224.1], abs=0.1)
    it = paired["families"]["issue_type"]["compiled"]
    assert it["total_tokens"]["mean_ci95"] == pytest.approx([-1772.5, -1596.7], abs=0.1)
    for fam in paired["families"].values():
        for m in ("total_tokens", "wall_latency_ms", "estimated_cost_usd"):
            lo, hi = fam["compiled"][m]["mean_ci95"]
            assert lo < hi < 0
        assert fam["compiled"]["wall_latency_ms"]["median_ci95"][1] < 0


def test_discordance_cells(paired) -> None:
    d = paired["discordance"]
    assert d["backlog_attention"]["compiled_only"] == 1
    assert d["backlog_attention"]["compiled_only_records"] == [5189]
    assert d["backlog_attention"]["baseline_only"] == 0
    assert d["pooled"]["n"] == 90 and d["pooled"]["both"] == 89
    assert d["pooled"]["baseline_only"] == 0 and d["pooled"]["compiled_only"] == 1
    assert d["pooled"]["mcnemar_exact_p"] == 1.0
    assert d["pooled"]["compiled_only_failure_upper95"] == pytest.approx(0.0327, abs=5e-4)


def test_multiplicity_accounting(multiplicity) -> None:
    a = multiplicity["artifacts"]
    assert a["issue_type"]["m"] == 1 and a["issue_type"]["certificate_at_alpha"] == "compiler-wide"
    for fam in ("pr_outcome", "backlog_attention"):
        assert a[fam]["m"] == 2
        assert a[fam]["u_candidate_wide"] == pytest.approx(0.056941, abs=1e-6)
        assert a[fam]["certificate_at_alpha"] == "per-candidate"
        assert a[fam]["groups_for_compiler_wide"] == 106
    assert multiplicity["n_min"]["2"] == 106
    assert a["core:psf/requests"]["frozen"] is True


def test_gate_frontier_accounting(frontier) -> None:
    pooled = frontier["gate_frontier"]["pooled"]
    assert pooled["baseline"]["exact"] == 240 and pooled["baseline"]["completed"] == 240
    assert pooled["learned_gate"]["exact"] == 240 and pooled["learned_gate"]["compacted"] == 160
    assert pooled["support_only"]["exact"] == 239 and pooled["support_only"]["completed"] == 239
    assert frontier["gate_frontier"]["failures"][0]["record_number"] == 6708
    assert frontier["gate_frontier"]["retained_cost_usd_successful_attempts"] == pytest.approx(0.4058, abs=5e-4)
    hf = frontier["gate_frontier"]["repositories"]["huggingface/datasets"]
    assert hf["coverage_curves"]["learned_gate_distinct_nonzero_coverage_levels"] == [0.1087, 1.0]
    assert hf["gates"]["support_only"]["grid_size"] == 12
    assert hf["gates"]["support_only"]["U"] == pytest.approx(0.0507, abs=5e-4)
    assert frontier["core"]["pooled"] == {"compacted": 80, "held_out": 120}
    assert frontier["balanced"]["pooled"] == {"compacted": 180, "held_out": 180}
    for repo, e in frontier["core"].items():
        if repo != "pooled" and "held_out" in e:
            assert e["fallback_reasons"] == {"range:pr.state": 10}


def test_cohort_overlap(overlap) -> None:
    t = overlap["totals"]
    assert t["core_gf_test"] == 130
    assert t["core_gf_discovery"] == 561
    assert t["core_bal_test"] == 46
    hf = overlap["repositories"]["huggingface/datasets"]["core_vs_gate_frontier"]
    assert hf["test"] == 23 and hf["discovery"] == 106


def test_effective_units(clusters) -> None:
    prim = {k: v for k, v in clusters["cohorts"].items() if k in stats.FAMILIES}
    assert all(v["matched"] == 92 for v in prim.values())
    assert clusters["primary_ranges"]["distinct_days"] == [86, 90]
    assert clusters["primary_ranges"]["distinct_authors"] == [60, 82]
    for v in prim.values():
        assert v["distinct_days"] < 92 and v["U_at_distinct_days"] > stats.ALPHA
        assert v["distinct_authors"] < 92 and v["U_at_distinct_authors"] > stats.ALPHA


def test_generated_tables_exist_and_are_marked() -> None:
    for name in ("absolute_resources", "paired_statistics", "discordance", "multiplicity_accounting",
                 "live_provider_manifest", "live_catalog", "multirepo_dispatch",
                 "gate_frontier_disaggregated", "effective_units", "mechanism_removal"):
        text = (stats.TABLES / f"{name}.tex").read_text()
        assert text.startswith("% generated by paper/scripts/iclr_revision_statistics.py")
        assert "\\bottomrule" in text
    frontier_json = json.loads((stats.OUT / "gate_frontier_reanalysis.json").read_text())
    assert frontier_json["gate_frontier"]["pooled"]["support_only"]["completed"] == 239
