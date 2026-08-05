"""Integration evidence for GCS using archived real-provider traces.

This test deliberately performs no paid provider request.  It reconstructs the
sealed OpenAI tool decisions from the publication checkpoint, recompiles the
region, and executes it against the pinned real GitHub-issue snapshot.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from paper.scripts import validate_guarded_composite as validation


def test_real_trace_compilation_and_projection_replay(tmp_path: Path) -> None:
    payload = validation.validate(
        argparse.Namespace(
            checkpoint=validation.DEFAULT_CHECKPOINT,
            regraded_results=validation.DEFAULT_REGRADED,
            output=tmp_path / "gcs-provider-free.json",
            train_cases=16,
            dev_cases=8,
            calibration_cases=92,
        )
    )

    assert payload["provider_calls_executed"] == 0
    assert payload["source_provider_trace_count"] == 132
    assert payload["compiler"]["complete_region_steps"] == 3
    assert payload["compiler"]["exposed_interfaces"] == 1
    assert payload["replay"] == {
        "attempted": 132,
        # Identifier fields are nominal rather than bounded by the training
        # extrema; the semantic-contract fix therefore admits six additional
        # schema-compatible traces without weakening the projection check.
        "dispatched": 130,
        "fallback": 2,
        "exact_projected_matches": 130,
        "projection_failures": [],
        "all_dispatched_exact": True,
    }
