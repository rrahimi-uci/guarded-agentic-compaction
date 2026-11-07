"""Check fixed selection and cross-model budget behavior without provider calls."""

import json
import random

from agenthop_baseline_trace_pilot import N_CASES, selected_ids
from agenthop_campaign_budget import AgentHopBudget, MAX_OUTPUT, MODEL, TASK_PREFIX


def test_selection_ignores_answers_and_row_order():
    rows = []
    for i in range(478):
        # 198 pairs plus 82 singletons = 280 path-overlap components.
        bridge = f"paired-{i // 2}" if i < 396 else f"single-{i}"
        rows.append({"id": f"st_{i:04d}", "question_type": "single-target",
            "depth": 2, "seed_paper_id": f"seed-{i}",
            "bridge_paper_ids": [bridge], "gold_paper_ids": [f"gold-{i}"],
            "correct_index": i % 4})
    first = selected_ids(rows)
    assert len(first) == len(set(first)) == N_CASES
    shuffled = list(rows)
    random.Random(17).shuffle(shuffled)
    for row in shuffled:
        row["correct_index"] = (row["correct_index"] + 1) % 4
    assert selected_ids(shuffled) == first
    assert len({rows[int(sid[3:])]["bridge_paper_ids"][0] for sid in first}) == N_CASES


def test_responses_usage_charges_shared_ledger_without_reset(tmp_path):
    path = tmp_path / "ledger.json"
    budget = AgentHopBudget(path)
    payload = {"model": MODEL, "max_output_tokens": MAX_OUTPUT,
               "input": [{"role": "user", "content": "public task"}]}
    rid = budget.reserve(payload, task=TASK_PREFIX + "st_0001")
    budget.finish(rid, {"input_tokens": 100, "output_tokens": 10}, response_model=MODEL)
    data = json.loads(path.read_text())
    assert data["cap_usd"] == 300
    assert data["stage_caps"]["pilot"] == 30
    assert data["requests"][0]["model"] == MODEL
    assert abs(data["accounted_upper_usd"] - (100 * 3.125 + 10 * 15) / 1e6) < 1e-12


def test_missing_usage_retains_reservation(tmp_path):
    path = tmp_path / "ledger.json"
    budget = AgentHopBudget(path)
    rid = budget.reserve({"model": MODEL, "max_output_tokens": MAX_OUTPUT,
                          "input": "public task"}, task=TASK_PREFIX + "st_0001")
    budget.finish(rid, status="provider_request_failed")
    data = json.loads(path.read_text())
    assert data["requests"][0]["status"] == "provider_request_failed_usage_unknown"
    assert data["accounted_upper_usd"] == data["requests"][0]["reserved_usd"]
