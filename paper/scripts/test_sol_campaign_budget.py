"""Mixed-model accounting stays inside one fail-closed campaign ledger."""
import json

from adaptive_campaign_budget import Ledger, MODEL as LUNA
from sol_campaign_budget import SolLedger, MODEL as SOL


def test_sol_and_luna_share_campaign_cap_without_rate_reset(tmp_path):
    path = tmp_path / "ledger.json"
    luna = Ledger(path)
    sol = SolLedger(path)
    luna_payload = {"model": LUNA, "max_completion_tokens": 100, "messages": []}
    sol_payload = {"model": SOL, "max_completion_tokens": 100, "messages": []}
    luna_id = luna.reserve(luna_payload, stage="discovery", task="luna", arm="baseline")
    sol_id = sol.reserve(sol_payload, stage="discovery", task="sol", arm="baseline")
    luna.finish(luna_id, {"prompt_tokens": 10, "completion_tokens": 5})
    sol.finish(sol_id, {"prompt_tokens": 10, "completion_tokens": 5})
    value = json.loads(path.read_text())
    assert len(value["requests"]) == 2
    assert {r["model"] for r in value["requests"]} == {LUNA, SOL}
    expected_luna = (10 * .5 + 5 * 1.2) / 1e6
    expected_sol = (10 * 5 + 5 * 20) / 1e6
    assert abs(value["accounted_upper_usd"] - expected_luna - expected_sol) < 1e-12
    assert value["cap_usd"] == 300
    assert value["stage_caps"]["discovery"] == 30


def test_unknown_sol_usage_keeps_full_reservation(tmp_path):
    path = tmp_path / "ledger.json"
    ledger = SolLedger(path)
    rid = ledger.reserve({"model": SOL, "max_completion_tokens": 100, "messages": []},
                         stage="discovery", task="unknown", arm="baseline")
    ledger.finish(rid, status="provider_request_failed")
    row = json.loads(path.read_text())["requests"][0]
    assert row["status"] == "provider_request_failed_usage_unknown"
    assert row["reserved_usd"] == json.loads(path.read_text())["accounted_upper_usd"]
