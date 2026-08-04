"""Provider-free checks for the real-record prospective portfolio protocol."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "paper/scripts/portfolio_live_study.py"
SPEC = importlib.util.spec_from_file_location("portfolio_live_study", SCRIPT)
assert SPEC and SPEC.loader
study = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(study)


def test_retained_replication_selects_reviewed_macro() -> None:
    decision, config, payload = study.select_action(model="gpt-5.6-luna")
    assert decision.selected_action == "macro"
    assert decision.requires_review is True
    assert len({row["issue_number"] for row in payload["results"] if row["condition"] == "baseline"}) == 30
    assert config.minimum_groups == 30
    assert all(item.support_groups == 30 for item in decision.evidence)


def test_fresh_selection_excludes_every_prior_evaluation_record() -> None:
    import pandas as pd

    frame = pd.read_parquet(study.fixed.DATA_PATH)
    store, _ = study.fixed.build_store(frame)
    scenarios, _ = study.fresh_scenarios(store, cases_per_class=1, seed=20260804)
    prior = study.prior_issue_numbers()
    assert len(scenarios) == 3
    assert not ({item.issue_number for item in scenarios} & prior)
