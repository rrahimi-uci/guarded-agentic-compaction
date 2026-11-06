"""Retain auditable pilot evidence without credentials, provider logs or databases."""
import argparse
import gzip
import io
from importlib.metadata import version
import json
import math
from pathlib import Path
import subprocess
import sys
import tarfile

from adaptive_pilot import LOCAL, OUT, ROOT, digest, write


def pack(path, files):
    with path.open("wb") as sink:
        with gzip.GzipFile(filename="", mode="wb", fileobj=sink, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w") as archive:
                for name, data in sorted(files.items()):
                    item = tarfile.TarInfo(name)
                    item.size = len(data)
                    item.mode = 0o644
                    archive.addfile(item, io.BytesIO(data))


def build():
    ledger = json.loads((LOCAL / "ledger.json").read_text())
    if any(r["status"] == "reserved" for r in ledger["requests"]):
        raise RuntimeError("requests still outstanding; do not freeze a partial spending record")
    files = {str(p.relative_to(LOCAL)): p.read_bytes() for pattern in ("*/result.json", "*/candidates.json", "v2/*/result.json", "v2/*/candidates.json") for p in LOCAL.glob(pattern)}
    files["ledger.json"] = (LOCAL / "ledger.json").read_bytes()
    from dotenv import dotenv_values
    secrets = [value.encode() for key, value in dotenv_values(ROOT / ".env").items()
               if value and ("KEY" in key or "TOKEN" in key) and len(value) >= 12]
    if any(secret in data for secret in secrets for data in files.values()):
        raise RuntimeError("credential found in candidate evidence; refusing archive")
    metadata = {"python": sys.version, "packages": {name: version(name) for name in
        ("openai", "openai-agents", "jsonschema", "numpy", "scipy", "scikit-learn")},
        "runtime_source_identity": "source_hashes in each seal; upstream environment resolved by its pinned uv.lock",
        "measurement_host": sys.platform, "provider_endpoint": "https://api.openai.com/v1/chat/completions"}
    files["environment.json"] = (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode()
    files["licenses/Agent-JIT-MIT.txt"] = (ROOT / "experiments/adaptive_compiler_pilot/Agent-JIT-LICENSE.txt").read_bytes()
    seal = json.loads((OUT / "seal.json").read_text())
    write(OUT / "future_exclusions.json", {"schema": "gac-pilot-future-exclusions-v1",
        "split": "dev", "question_sha256": seal["question_sha256"],
        "question_ids": sorted(t["question_id"] for t in seal["tasks"]),
        "rule": "Exclude every ID from future calibration/test, regardless of version, outcome or compiler qualification. Add to the historical prior-use and author-inspection screens, not as a replacement for them."})
    pack(OUT / "raw_evidence.tar.gz", files)
    old = json.loads((OUT / "seal_v1.json").read_text())
    historical = OUT / "source_v1.tar.gz"
    if historical.exists():
        with tarfile.open(historical, "r:gz") as archive:
            sources = {p: archive.extractfile(p).read() for p in old["source_hashes"]}
    else:
        sources = {p: subprocess.check_output(["git", "show", "76bdfe5:" + p]) for p in old["source_hashes"]}
    import hashlib
    for p, data in sources.items():
        if hashlib.sha256(data).hexdigest() != old["source_hashes"][p]:
            raise RuntimeError("historical source mismatch")
    pack(OUT / "source_v1.tar.gz", sources)
    write(OUT / "retention.json", {"schema": "gac-pilot-retention-v1",
        "raw_archive_sha256": digest(OUT / "raw_evidence.tar.gz"),
        "historical_source_archive_sha256": digest(OUT / "source_v1.tar.gz"),
        "files": {p: hashlib.sha256(data).hexdigest() for p, data in sorted(files.items())},
        "scope": "Every attempted arm's observable response/tool trace and generated candidates, plus the shared campaign ledger. Both protocol versions retained. No hidden reasoning, keys, .env, database files or provider logs.",
        "upstream": "https://github.com/agent-jit-compilation/agent-jit-compilation/tree/ad6df6b8d19573efa4a1155951c6a838f6b1b4d7",
        "benchmark": "https://huggingface.co/datasets/birdsql/bird_sql_dev_20251106"})
    verify()


def verify():
    import hashlib
    retention = json.loads((OUT / "retention.json").read_text())
    assert digest(OUT / "raw_evidence.tar.gz") == retention["raw_archive_sha256"]
    assert digest(OUT / "source_v1.tar.gz") == retention["historical_source_archive_sha256"]
    old_seal = json.loads((OUT / "seal_v1.json").read_text())
    with tarfile.open(OUT / "source_v1.tar.gz", "r:gz") as historical:
        assert set(historical.getnames()) == set(old_seal["source_hashes"])
        for name, sha in old_seal["source_hashes"].items():
            assert hashlib.sha256(historical.extractfile(name).read()).hexdigest() == sha
    with tarfile.open(OUT / "raw_evidence.tar.gz", "r:gz") as archive:
        assert set(archive.getnames()) == set(retention["files"])
        content = {}
        for name, sha in retention["files"].items():
            assert not Path(name).is_absolute() and ".." not in Path(name).parts
            member = archive.getmember(name)
            assert member.isfile()
            data = archive.extractfile(member).read()
            assert hashlib.sha256(data).hexdigest() == sha
            if name.endswith(".json"):
                content[name] = json.loads(data)
    ledger = content["ledger.json"]
    excluded = json.loads((OUT / "future_exclusions.json").read_text())
    current_seal = json.loads((OUT / "seal.json").read_text())
    assert set(excluded["question_ids"]) == {t["question_id"] for t in current_seal["tasks"]}
    for name, sha in current_seal["source_hashes"].items():
        assert digest(ROOT / name) == sha
    assert ledger["accounted_upper_usd"] <= ledger["cap_usd"] == 300
    assert not any(r["status"] == "reserved" for r in ledger["requests"])
    charged = lambda r: r.get("accounted_upper_usd", r["reserved_usd"])
    assert math.isclose(ledger["accounted_upper_usd"], math.fsum(charged(r) for r in ledger["requests"]), abs_tol=1e-12)
    for stage, cap in ledger["stage_caps"].items():
        assert math.fsum(charged(r) for r in ledger["requests"] if r["stage"] == stage) <= cap
    for version, prefix in (("", "v2/"), ("_v1", "")):
        report = json.loads((OUT / f"report{version}.json").read_text())
        assert report["seal_sha256"] == digest(OUT / f"seal{version}.json")
        seal = json.loads((OUT / f"seal{version}.json").read_text())
        expected = {(t["question_id"], arm) for t in seal["tasks"] for arm in t["arm_order"]}
        assert len(report["rows"]) == len(expected)
        assert {(r["question_id"], r["arm"]) for r in report["rows"]} == expected
        for row in report["rows"]:
            task = ("v2:" if prefix else "") + str(row["question_id"])
            requests = [r for r in ledger["requests"] if r["task"] == task and r["arm"] == row["arm"]]
            assert row["provider_requests"] == len(requests)
            assert math.isclose(row["accounted_upper_usd"], sum(charged(r) for r in requests), abs_tol=1e-12)
            name = f"{prefix}{row['question_id']}-{row['arm']}/result.json"
            if row["status"] == "unstarted":
                assert name not in content
                continue
            assert row["raw_sha256"] == retention["files"][name]
            assert row["execution_correct"] == content[name]["execution_correct"]
            assert row["status"] == content[name]["status"]
            assert row["tool_calls"] == len(content[name].get("tool_calls", []))
            if "candidates_sha256" in row:
                candidate_name = name.replace("result.json", "candidates.json")
                assert row["candidates_sha256"] == retention["files"][candidate_name]
                candidates = content[candidate_name]["candidates"]
                assert row["generated_candidates"] == len(candidates)
                assert row["valid_candidates"] == sum(bool(c and c.get("is_valid")) for c in candidates)
        for arm, summary in report["summary"].items():
            rows = [r for r in report["rows"] if r["arm"] == arm]
            assert summary["scheduled"] == len(rows)
            assert summary["correct"] == sum(bool(r["execution_correct"]) for r in rows)
    print("Pilot archives, source versions, denominators, outcomes and budget verified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "verify"])
    if parser.parse_args().command == "build":
        build()
    else:
        verify()
