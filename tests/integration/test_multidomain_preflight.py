"""Integration checks for the prospective real-record protocol lock."""

from __future__ import annotations

import json
import hashlib
import shutil
from pathlib import Path

import pytest
import yaml

from agent_compaction.evaluation import BenchmarkCase
from agent_compaction.schema.effects import EffectCatalog, EffectClass
from agent_compaction.benchmarking.preflight import _validate_source_manifest
from benchmarks.preflight import PreflightError, load_study_manifest, preflight_study


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "benchmarks/manifests/multidomain-study.yaml"


def _cases(domain: str, count: int) -> tuple[BenchmarkCase, ...]:
    snapshots = {
        "vulnerability": "2e9912ecb96d5fb15d088977616c8065bb7bea860dd2f0ed25111bfcccc06a32",
        "hmda": "945c176f483bfc736d9faff7f7db226091234c8f5d50f7768481e2dbf3e2dde9",
        "sec": "a" * 64,
    }
    return tuple(
        BenchmarkCase(
            case_id=f"{domain}-case-{index}",
            group_id=f"{domain}-group-{index}",
            domain=domain,
            source_snapshot="sha256:" + snapshots[domain],
            inputs={"public_record_id": f"record-{index}"},
            metadata={
                "real_public_record": True,
                "lineage_ids": [f"{domain}-lineage-{index}"],
                **(
                    {"protected_demographic_fields_exposed": False}
                    if domain == "hmda"
                    else {}
                ),
            },
        )
        for index in range(count)
    )


def test_committed_protocol_is_explicitly_unrun_and_provider_free(monkeypatch) -> None:
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    payload = load_study_manifest(MANIFEST)
    assert payload["status"] == "proposed_unrun"
    assert payload["provider_calls_executed"] == 0
    report = preflight_study(MANIFEST)
    assert not report.eligible
    assert report.errors == ()
    assert report.source_configuration_available == {"sec:SEC_USER_AGENT": False}
    assert all("no normalized cases supplied" in item for item in report.warnings[:3])


def test_effect_catalogs_are_local_qualified_reads() -> None:
    study = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    paths = [ROOT / "benchmarks" / spec["effect_catalog"]
             for spec in study["domains"].values()]
    for path in sorted(paths):
        catalog = EffectCatalog.from_yaml(path)
        assert catalog.tools
        assert all(spec.effect is EffectClass.READ_LOCAL for spec in catalog.tools.values())
        assert all(spec.compilable for spec in catalog.tools.values())


def test_preflight_accepts_420_independent_real_record_slots(monkeypatch) -> None:
    monkeypatch.setenv("SEC_USER_AGENT", "research@example.org agent-compaction")
    pools = {domain: _cases(domain, 420) for domain in ("vulnerability", "sec", "hmda")}
    report = preflight_study(
        MANIFEST,
        cases_by_domain=pools,
        require_source_configuration=True,
        require_normalized_artifacts=False,
    )
    assert report.eligible
    assert report.errors == ()
    assert report.domain_group_counts == {
        "vulnerability": 420,
        "sec": 420,
        "hmda": 420,
    }
    assert report.role_groups_per_domain == 345


def test_sec_configuration_requires_contact_shape_without_exposing_value(monkeypatch) -> None:
    monkeypatch.setenv("SEC_USER_AGENT", "anonymous-client")
    pools = {domain: _cases(domain, 420) for domain in ("vulnerability", "sec", "hmda")}
    report = preflight_study(
        MANIFEST,
        cases_by_domain=pools,
        require_source_configuration=True,
        require_normalized_artifacts=False,
    )
    assert not report.eligible
    assert report.source_configuration_available == {"sec:SEC_USER_AGENT": False}
    assert "anonymous-client" not in json.dumps(report.as_dict())


def test_preflight_rejects_short_pool_duplicate_ids_and_wrong_domain(monkeypatch) -> None:
    monkeypatch.setenv("SEC_USER_AGENT", "research@example.org agent-compaction")
    pools = {domain: _cases(domain, 420) for domain in ("vulnerability", "sec", "hmda")}
    pools["sec"] = _cases("sec", 419)
    first = pools["hmda"][0]
    pools["hmda"] = (
        BenchmarkCase(
            case_id="vulnerability-case-0",
            group_id=first.group_id,
            domain="sec",
            source_snapshot=first.source_snapshot,
            inputs=first.inputs,
        ),
        *pools["hmda"][1:],
    )
    report = preflight_study(
        MANIFEST,
        cases_by_domain=pools,
        require_source_configuration=True,
        require_normalized_artifacts=False,
    )
    assert not report.eligible
    assert any("sec: 419 independent groups < 420" in item for item in report.errors)
    assert any("duplicate case_id" in item for item in report.errors)
    assert any("declares domain sec" in item for item in report.errors)


def test_preflight_detects_manifest_drift(tmp_path) -> None:
    payload = load_study_manifest(MANIFEST)
    payload["actions"].append("cache")
    drifted = tmp_path / "manifests" / "study.yaml"
    drifted.parent.mkdir()
    drifted.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(PreflightError, match="actions must remain frozen"):
        preflight_study(drifted)


def test_preflight_binds_available_real_case_files_to_attested_checksums(
    tmp_path: Path,
) -> None:
    pools = {
        domain: ROOT / f"paper/results/multidomain/preflight/{domain}/cases.jsonl"
        for domain in ("vulnerability", "hmda")
    }
    loaded = {
        domain: tuple(
            BenchmarkCase(
                case_id=row["case_id"],
                group_id=row["group_id"],
                domain=row["domain"],
                source_snapshot=row["source_snapshot"],
                inputs=row["inputs"],
                metadata=row["metadata"],
            )
            for row in map(json.loads, path.read_text().splitlines())
        )
        for domain, path in pools.items()
    }
    report = preflight_study(
        MANIFEST,
        cases_by_domain=loaded,
        case_paths_by_domain=pools,
        require_normalized_artifacts=True,
    )
    assert report.errors == ()
    assert report.domain_group_counts == {
        "vulnerability": 420,
        "sec": 0,
        "hmda": 420,
    }

    tampered = tmp_path / "cases.jsonl"
    tampered.write_bytes(pools["vulnerability"].read_bytes() + b"\n")
    report = preflight_study(
        MANIFEST,
        cases_by_domain={"vulnerability": loaded["vulnerability"]},
        case_paths_by_domain={"vulnerability": tampered},
        require_normalized_artifacts=True,
    )
    assert any("checksum mismatch" in error for error in report.errors)


def test_programmatic_preflight_requires_attested_case_paths_by_default() -> None:
    cases = {"vulnerability": _cases("vulnerability", 420)}
    report = preflight_study(MANIFEST, cases_by_domain=cases)
    assert not report.eligible
    assert "vulnerability: normalized case path is required" in report.errors


def _copy_hmda_attestation(tmp_path: Path) -> tuple[Path, Path]:
    repository = tmp_path / "repository"
    source_path = repository / "benchmarks/manifests/sources/hmda.yaml"
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(
        (ROOT / "benchmarks/manifests/sources/hmda.yaml").read_bytes()
    )
    gold_code = repository / "benchmarks/gold.py"
    gold_code.parent.mkdir(parents=True, exist_ok=True)
    gold_code.write_bytes((ROOT / "benchmarks/gold.py").read_bytes())
    pool = repository / "paper/results/multidomain/preflight/hmda"
    shutil.copytree(ROOT / "paper/results/multidomain/preflight/hmda", pool)
    return source_path, pool


def test_source_attestation_rejects_retained_artifact_tampering(tmp_path: Path) -> None:
    source_path, pool = _copy_hmda_attestation(tmp_path)
    _validate_source_manifest(
        source_path, domain="hmda", repository_root=tmp_path / "repository"
    )
    (pool / "gold.jsonl").write_bytes((pool / "gold.jsonl").read_bytes() + b"\n")
    with pytest.raises(PreflightError, match="gold.jsonl checksum mismatch"):
        _validate_source_manifest(
            source_path, domain="hmda", repository_root=tmp_path / "repository"
        )


def test_source_attestation_semantically_rejects_hmda_schema_leak(
    tmp_path: Path,
) -> None:
    source_path, pool = _copy_hmda_attestation(tmp_path)
    snapshot_path = pool / "snapshot.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    first_row = next(iter(snapshot["records"]["rows"].values()))
    first_row["applicant_race-1"] = "5"
    snapshot_digest = hashlib.sha256(
        json.dumps(
            snapshot["records"], sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    snapshot["snapshot_digest"] = f"sha256:{snapshot_digest}"
    snapshot_path.write_text(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    cases_path = pool / "cases.jsonl"
    cases = [json.loads(line) for line in cases_path.read_text().splitlines()]
    for case in cases:
        case["source_snapshot"] = f"sha256:{snapshot_digest}"
    cases_path.write_text(
        "".join(json.dumps(case, sort_keys=True) + "\n" for case in cases),
        encoding="utf-8",
    )
    report_path = pool / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["snapshot_digest"] = snapshot_digest
    report["case_file_sha256"] = hashlib.sha256(cases_path.read_bytes()).hexdigest()
    report["snapshot_file_sha256"] = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    source = yaml.safe_load(source_path.read_text())
    source["normalized_pool"]["snapshot_digest"] = snapshot_digest
    source_path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")
    with pytest.raises(PreflightError, match="privacy allowlist"):
        _validate_source_manifest(
            source_path, domain="hmda", repository_root=tmp_path / "repository"
        )
