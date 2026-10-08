"""The study driver runs free-form-mapping answer models through the SDK's non-strict wrapper."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "paper" / "scripts"))

import multidomain_study as ms  # noqa: E402
from benchmarks.runtime import HmdaAnswer, SecAnswer, VulnerabilityAnswer  # noqa: E402


def test_hmda_answer_needs_the_non_strict_wrapper() -> None:
    from agents import AgentOutputSchema

    schema, strict = ms._output_schema(HmdaAnswer)
    assert strict is False and isinstance(schema, AgentOutputSchema)


def test_strict_compatible_answers_pass_through() -> None:
    for model in (VulnerabilityAnswer, SecAnswer):
        schema, strict = ms._output_schema(model)
        assert strict is True and schema is model
