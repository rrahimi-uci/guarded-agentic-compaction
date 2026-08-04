"""Integration: the public API, the CLI, and the config schemas.

These are the paths a user actually touches, so they are exercised end to end on a
synthetic snapshot: write traces, validate the catalog, report data quality, estimate,
compile, explain, diff, promote.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

import agent_compaction as ac
from agent_compaction.cli import main as cli_main
from agent_compaction.registry.store import Registry
from agent_compaction.schema.artifacts import Lifecycle

from scripts.generate_synthetic import ENTRY_ALLOWLIST, SYNTHETIC_CATALOG, generate

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def traces_file(tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("traces") / "synth.jsonl"
    ac.write_jsonl(generate(n_episodes=260, seed=17), path)
    return path


@pytest.fixture(scope="module")
def catalog_file(tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("cfg") / "effects.yaml"
    payload = json.loads(SYNTHETIC_CATALOG.model_dump_json())
    # drop empty optional fields so the file reads like a hand-written catalog
    payload["tools"] = {
        name: {k: v for k, v in spec.items() if v not in ((), [], None, "", False)}
        for name, spec in payload["tools"].items()
    }
    for spec in payload["tools"].values():
        spec.pop("tool", None)
    path.write_text(yaml.safe_dump(payload, sort_keys=True))
    return path


def test_jsonl_roundtrip_preserves_episodes(traces_file):
    episodes = ac.read_jsonl(traces_file)
    assert len(episodes) == 260
    assert episodes[0].n_requests() > 0
    assert episodes[0].events[0].kind.value == "MODEL_REQ"


def test_config_examples_validate_against_their_schemas():
    import jsonschema

    for cfg, sch in (
        ("configs/effects.example.yaml", "configs/effects.schema.json"),
        ("configs/promotion.example.yaml", "configs/promotion.schema.json"),
    ):
        jsonschema.validate(
            yaml.safe_load((ROOT / cfg).read_text()), json.loads((ROOT / sch).read_text())
        )


def test_cli_validate_catalog_flags_undeclared_tools(catalog_file, capsys):
    rc = cli_main(["validate-catalog", str(catalog_file), "--tools", "auth.token", "shadow.undeclared"])
    out = capsys.readouterr().out
    assert rc == 1  # an undeclared tool is a non-zero exit for CI
    assert "shadow.undeclared" in out


def test_cli_quality_and_estimate(traces_file, catalog_file, capsys):
    assert cli_main(["quality", str(traces_file), "--effects", str(catalog_file)]) == 0
    assert "data-quality report" in capsys.readouterr().out
    rc = cli_main(
        ["estimate", str(traces_file), "--effects", str(catalog_file), "--entry", *ENTRY_ALLOWLIST]
    )
    out = capsys.readouterr().out
    assert rc in (0, 2)  # 2 == "not feasible", a legitimate answer
    assert "ceiling: phi=" in out


def test_cli_compile_explain_diff_promote(traces_file, catalog_file, tmp_path, capsys):
    out_dir = tmp_path / "v1"
    rc = cli_main(
        [
            "compile",
            str(traces_file),
            "--effects",
            str(catalog_file),
            "--entry",
            *ENTRY_ALLOWLIST,
            "--alpha",
            "0.30",
            "--out",
            str(out_dir),
        ]
    )
    printed = capsys.readouterr().out
    assert "GRC compile report" in printed
    assert rc in (0, 3)
    if rc != 0:
        pytest.skip("no artifact on this snapshot; the compile path itself is covered")

    assert cli_main(["explain", str(out_dir)]) == 0
    assert "artifact" in capsys.readouterr().out

    reg = Registry.load(out_dir)
    assert reg.artifacts
    v2 = tmp_path / "v2"
    Registry(name="v2").save(v2)
    assert cli_main(["diff", str(out_dir), str(v2)]) == 1  # v2 lost every artifact

    assert cli_main(["promote", str(out_dir), "--stage", "shadow"]) == 0
    assert Registry.load(out_dir).artifacts[0].lifecycle is Lifecycle.SHADOW


def test_api_optimize_requires_explicit_mode_and_evaluator():
    episodes = generate(n_episodes=40, seed=3)
    with pytest.raises(ValueError):
        ac.optimize(episodes, SYNTHETIC_CATALOG, mode="magic")
    with pytest.raises(ValueError):
        ac.optimize(episodes, SYNTHETIC_CATALOG, algorithms=["tgws"], mode="offline")


def test_api_optimize_and_validate_reports_unclaimed_perturbations():
    episodes = generate(n_episodes=300, seed=23)
    episodes = ac.manifest_partitions(episodes)[episodes[0].manifest.compatibility_key()]
    job = ac.optimize(
        episodes,
        SYNTHETIC_CATALOG,
        algorithms=["grc"],
        mode="offline",
        entry_schema=ENTRY_ALLOWLIST,
        alpha=0.30,
        job_id="job-test",
    )
    report = ac.validate(job, suites=["replay", "perturbation"])
    assert report["suites"] == ["replay", "perturbation"]
    for entry in report["artifacts"].values():
        # no sandbox was supplied, so the suite must be reported as *not claimed*
        assert entry["perturbation"]["claimed"] is False
        assert "unverified" in entry["perturbation"]["note"]


def test_promotion_requires_a_distinct_human_approver():
    from agent_compaction.registry.lifecycle import LifecycleError

    episodes = generate(n_episodes=300, seed=29)
    episodes = ac.manifest_partitions(episodes)[episodes[0].manifest.compatibility_key()]
    job = ac.optimize(
        episodes,
        SYNTHETIC_CATALOG,
        algorithms=["grc"],
        mode="offline",
        entry_schema=ENTRY_ALLOWLIST,
        alpha=0.30,
        job_id="job-approve",
    )
    if not job.artifacts:
        pytest.skip("no artifact on this snapshot")
    ac.promote(job, stage="shadow")
    with pytest.raises(LifecycleError):
        ac.promote(job, stage="approved", approved_by="optimizer", job_identity="optimizer")
    with pytest.raises(LifecycleError):
        ac.promote(job, stage="approved", approved_by="human@example", evaluation_split="train")
    ac.promote(job, stage="approved", approved_by="human@example", evaluation_split="dev")
    assert job.artifacts[0].lifecycle is Lifecycle.APPROVED
