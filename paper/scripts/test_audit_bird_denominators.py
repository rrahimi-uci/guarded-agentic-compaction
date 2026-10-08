"""Failure accounting must not silently change another arm's quality denominator."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_bird_denominators import CONDITIONS, audit_cohort, build


def test_comparator_timeout_and_compiled_failure_keep_all_scheduled_questions(tmp_path):
    (tmp_path / "preflight.json").write_text(json.dumps({"selections": {"db": {"test": [1, 2]}}}))
    target = tmp_path / "schema_first/db"
    target.mkdir(parents=True)
    (target / "compile.json").write_text('{"status":"admitted"}')
    results = [{"condition": c, "issue_number": q, "quality": {"overall": True},
                "metrics": {m: 1 for m in ("requests", "total_tokens", "wall_latency_ms", "estimated_cost_usd")}}
               for c in CONDITIONS for q in (1, 2)
               if (c, q) not in {("manual_schema_prefetch", 1), ("compiled", 2)}]
    (target / "evaluation.json").write_text(json.dumps({"results": results, "failures": [
        {"condition": "manual_schema_prefetch", "question_id": 1},
        {"condition": "compiled", "question_id": 2}]}))
    actual = audit_cohort(tmp_path)
    assert actual["scheduled_questions"] == 2
    assert actual["four_arm_complete_questions"] == 0
    assert actual["arms"]["baseline"]["correct"] == 2
    assert actual["arms"]["compiled"]["correct"] == 1
    assert actual["baseline_compiled_resource_pairs"] == 1
    assert actual["baseline_only_correct"] == 1


def test_retained_denominator_audit_regenerates():
    root = Path(__file__).resolve().parents[2]
    assert build() == json.loads((root / "paper/results/bird/denominator_audit.json").read_text())
