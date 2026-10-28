"""Failed attempts are visible to the operator without widening the retained ledger.

The 2026-10-07 HMDA discovery run retained eighty ``execution_failed`` rows whose only
diagnostic was the class name ``UserError``: the Agents SDK had rejected the strict JSON
schema of ``HmdaAnswer`` before any provider request, and the operator could not tell.
The driver now prints a bounded, secret-masked line per failure to stderr and can stop
after a configurable number of back-to-back failures. The ledger payload is unchanged.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "paper" / "scripts"))

import multidomain_study as ms  # noqa: E402
from guarded_agentic_compaction.benchmarking import ScheduledExecution  # noqa: E402
from guarded_agentic_compaction.cli import build_parser  # noqa: E402


def _item() -> ScheduledExecution:
    return ScheduledExecution(
        sequence=1,
        stage=0,
        domain="hmda",
        case_id="hmda-2024-549300HRKD2IJSOPRA57-f5b1c4745b2dbfd6",
        group_id="549300HRKD2IJSOPRA57",
        role="discovery",
        action="baseline",
        repeat=0,
    )


def test_failure_report_names_the_sdk_error_that_was_hidden_in_october() -> None:
    from agents.exceptions import UserError

    stream = io.StringIO()
    error = UserError(
        "Strict JSON schema is enabled, but the output type is not valid. Either make the "
        "output type strict, or wrap your type with AgentOutputSchema(YourType, "
        "strict_json_schema=False)"
    )
    line = ms._report_failure(error, _item(), 0, stream=stream)
    assert stream.getvalue() == line + "\n"
    assert line.startswith(
        "execution failed: hmda:hmda-2024-549300HRKD2IJSOPRA57-f5b1c4745b2dbfd6:baseline "
        "attempt 0: agents.exceptions.UserError: Strict JSON schema is enabled"
    )


def test_failure_report_masks_credential_like_tokens_and_bounds_length() -> None:
    stream = io.StringIO()
    leaked = "sk-proj-ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdef"
    provider_masked = "sk-proj-" + "*" * 120 + "ajoA"  # the provider's own 401 rendering
    error = RuntimeError(
        f"Incorrect API key provided: {leaked} or {provider_masked}. " + "x" * 2000
    )
    line = ms._report_failure(error, _item(), 1, stream=stream)
    assert leaked not in line and "ajoA" not in line and "sk-[masked]" in line
    assert line.endswith("...") and len(line) < 800


def test_resumed_runs_number_attempts_after_retained_failures(tmp_path: Path) -> None:
    """A re-attempt must not reuse a failed attempt's ledger id with different content."""

    from guarded_agentic_compaction.evaluation import RunLedger

    ledger = RunLedger(tmp_path / "ledger.jsonl")
    event = "hmda:case:baseline:r0"
    for attempt in range(2):
        ledger.append(
            run_id="run",
            event_id=f"{event}:attempt:{attempt}",
            event_type="execution_failed",
            payload={"attempt": attempt, "error_type": "AuthenticationError"},
        )
    ledger.append(
        run_id="run", event_id="other:baseline:r0", event_type="execution_complete", payload={}
    )
    counts = ms._prior_failed_attempts(ledger.records())
    assert counts == {event: 2}
    # The historical numbering would collide on attempt 0 with a different error type.
    with pytest.raises(Exception, match="reused with different content"):
        ledger.append(
            run_id="run",
            event_id=f"{event}:attempt:0",
            event_type="execution_failed",
            payload={"attempt": 0, "error_type": "MaxTurnsExceeded"},
        )
    ledger.append(
        run_id="run",
        event_id=f"{event}:attempt:{counts[event]}",
        event_type="execution_failed",
        payload={"attempt": counts[event], "error_type": "MaxTurnsExceeded"},
    )
    assert ms._prior_failed_attempts(ledger.records()) == {event: 3}


def test_consecutive_failure_stop_is_opt_in_and_forwarded_by_the_cli() -> None:
    parser = ms.build_parser()
    base = [
        "--protocol", "p.json", "--cases", "hmda=c.jsonl", "--pool", "hmda=pool",
        "--phase", "discovery", "--model", "m", "--pricing", "pricing.json",
        "--max-provider-usd", "1", "--reservation-usd-per-execution", "0.04", "--out", "out",
    ]
    assert parser.parse_args(base).stop_after_consecutive_failures == 0
    assert parser.parse_args([*base, "--stop-after-consecutive-failures", "4"]).stop_after_consecutive_failures == 4
    with pytest.raises(SystemExit):
        ms.main([*base, "--stop-after-consecutive-failures", "-1"])

    cli_args = build_parser().parse_args(
        [
            "benchmark", "discovery", "p.json", "--cases", "hmda=c.jsonl", "--pool", "hmda=pool",
            "--model", "m", "--pricing", "pricing.json", "--max-provider-usd", "1",
            "--reservation-usd-per-execution", "0.04", "--out", "out",
            "--stop-after-consecutive-failures", "4", "--dry-run",
        ]
    )
    assert cli_args.stop_after_consecutive_failures == 4
