"""A versioned single-domain study may omit canonical domains only with a declared scope note."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from guarded_agentic_compaction.benchmarking.preflight import PreflightError, load_study_manifest

ROOT = Path(__file__).resolve().parents[2]


def _check(payload: dict, tmp_path: Path):
    from guarded_agentic_compaction.benchmarking import preflight

    path = tmp_path / "m.yaml"
    path.write_text(yaml.safe_dump(payload))
    return preflight.preflight_study(str(path), cases_by_domain={}, case_paths_by_domain={}, require_normalized_artifacts=False)


def test_hmda_only_manifest_declares_its_scope() -> None:
    payload = load_study_manifest(ROOT / "benchmarks/manifests/hmda-study-v2.yaml")
    assert set(payload["domains"]) == {"hmda"}
    assert "SEC pool is unavailable" in payload["scope_note"]
    assert payload["study_id"] != load_study_manifest(ROOT / "benchmarks/manifests/multidomain-study.yaml")["study_id"]


def test_subset_without_scope_note_is_refused(tmp_path: Path) -> None:
    payload = load_study_manifest(ROOT / "benchmarks/manifests/hmda-study-v2.yaml")
    payload.pop("scope_note")
    with pytest.raises(PreflightError, match="scope_note"):
        _check(payload, tmp_path)


def test_unknown_domain_is_refused(tmp_path: Path) -> None:
    payload = load_study_manifest(ROOT / "benchmarks/manifests/hmda-study-v2.yaml")
    payload["domains"]["other"] = dict(payload["domains"]["hmda"])
    with pytest.raises(PreflightError, match="subset"):
        _check(payload, tmp_path)
