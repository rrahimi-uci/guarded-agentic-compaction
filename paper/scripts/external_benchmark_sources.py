#!/usr/bin/env python3
"""Acquire or verify every external benchmark at its sealed revision.

Benchmark checkouts belong in a disposable directory, not the repository.  The emitted
report contains only source identities, checksums, and availability states; credentials
are read by environment-variable name and are never serialized.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "benchmarks/manifests/external-benchmarks.yaml"


def _load_repository_env() -> None:
    """Load simple KEY=VALUE entries without ever returning or printing values."""

    env_file = ROOT / ".env"
    if not env_file.is_file():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        normalized = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), normalized)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(command: Sequence[str], *, cwd: Path | None = None) -> str:
    result = subprocess.run(
        list(command),
        cwd=cwd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode:
        message = result.stderr.strip().splitlines()[-1:] or ["command failed"]
        raise RuntimeError(message[0])
    return result.stdout.strip()


def _safe_root(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if resolved in {Path("/").resolve(), Path.home().resolve(), ROOT.resolve()}:
        raise ValueError("external source root must be a dedicated non-repository directory")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _load_manifest(path: Path) -> Mapping[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping) or payload.get("schema") != (
        "agent-compaction-external-benchmark-sources/v1"
    ):
        raise ValueError("unsupported external benchmark manifest")
    sources = payload.get("sources")
    if not isinstance(sources, Mapping) or not sources:
        raise ValueError("external benchmark manifest contains no sources")
    return payload


def _git_source(name: str, spec: Mapping[str, Any], root: Path) -> dict[str, Any]:
    checkout = root / str(spec["checkout_name"])
    expected = str(spec["revision"])
    if not (checkout / ".git").is_dir():
        _run(
            [
                "git",
                "clone",
                "--filter=blob:none",
                "--no-checkout",
                str(spec["repository"]),
                str(checkout),
            ]
        )
    _run(["git", "fetch", "--depth=1", "origin", expected], cwd=checkout)
    sparse = spec.get("sparse_paths") or []
    if sparse:
        _run(["git", "sparse-checkout", "init", "--cone"], cwd=checkout)
        _run(["git", "sparse-checkout", "set", *map(str, sparse)], cwd=checkout)
    _run(["git", "checkout", "--detach", expected], cwd=checkout)
    observed = _run(["git", "rev-parse", "HEAD"], cwd=checkout)
    if observed != expected:
        raise RuntimeError(f"{name} checkout revision mismatch")
    return {
        "status": "available",
        "kind": "git",
        "path": checkout.name,
        "revision": observed,
        "tree": _run(["git", "rev-parse", "HEAD^{tree}"], cwd=checkout),
        "license": spec.get("license"),
        "benchmark_scope": spec.get("benchmark_scope"),
    }


def _http_source(name: str, spec: Mapping[str, Any], root: Path) -> dict[str, Any]:
    target = root / str(spec["checkout_name"])
    auth_name = str(spec.get("auth_env") or "")
    headers: dict[str, str] = {}
    if auth_name:
        token = os.environ.get(auth_name, "")
        if not token:
            return {
                "status": "gated",
                "kind": spec["kind"],
                "path": target.name,
                "revision": spec["revision"],
                "reason": f"{auth_name} is unavailable",
                "credential_name": auth_name,
                "credential_value_serialized": False,
                "license": spec.get("license"),
                "benchmark_scope": spec.get("benchmark_scope"),
            }
        headers["Authorization"] = f"Bearer {token}"
    try:
        request = urllib.request.Request(str(spec["url"]), headers=headers)
        with urllib.request.urlopen(request, timeout=180) as response:
            data = response.read()
        target.write_bytes(data)
    except urllib.error.HTTPError as exc:
        if spec["kind"] == "gated_http" and exc.code in {401, 403}:
            return {
                "status": "gated",
                "kind": spec["kind"],
                "path": target.name,
                "revision": spec["revision"],
                "reason": f"upstream authorization denied with HTTP {exc.code}",
                "credential_name": auth_name,
                "credential_value_serialized": False,
                "license": spec.get("license"),
                "benchmark_scope": spec.get("benchmark_scope"),
            }
        raise
    observed_hash = _sha256(target)
    observed_bytes = target.stat().st_size
    if observed_hash != spec["sha256"] or observed_bytes != int(spec["bytes"]):
        raise RuntimeError(f"{name} downloaded bytes do not match the sealed manifest")
    return {
        "status": "available",
        "kind": spec["kind"],
        "path": target.name,
        "revision": spec["revision"],
        "sha256": observed_hash,
        "bytes": observed_bytes,
        "credential_name": auth_name or None,
        "credential_value_serialized": False,
        "license": spec.get("license"),
        "benchmark_scope": spec.get("benchmark_scope"),
    }


def _pip_source(name: str, spec: Mapping[str, Any], root: Path) -> dict[str, Any]:
    """A distribution pinned by version rather than by revision.

    AppWorld ships its apps and its task data through its own installer rather than
    through the repository tree, and it pins ``pydantic<2``, so it cannot share this
    repository's interpreter.  The manifest therefore records the exact distribution and
    data versions, and this check reports whether an environment satisfying them has been
    prepared under the disposable source root.  Nothing is installed here: the environment
    is created by the reproduction commands in the protocol, because a pip install into an
    arbitrary interpreter is not a checksum-verifiable acquisition.
    """

    target = root / str(spec["checkout_name"])
    marker = target / "data" / "version.txt"
    if not marker.is_file():
        return {
            "status": "unprepared",
            "kind": "pip",
            "path": target.name,
            "revision": spec["revision"],
            "reason": (
                "no installed AppWorld data found; run the protocol's "
                "`appworld install` and `appworld download data` commands"
            ),
            "license": spec.get("license"),
            "benchmark_scope": spec.get("benchmark_scope"),
        }
    observed_data_version = marker.read_text(encoding="utf-8").strip()
    expected_data_version = str(spec.get("data_version") or "")
    if expected_data_version and observed_data_version != expected_data_version:
        raise RuntimeError(
            f"{name} installed data version {observed_data_version!r} does not match the "
            f"sealed manifest {expected_data_version!r}"
        )
    return {
        "status": "available",
        "kind": "pip",
        "path": target.name,
        "revision": spec["revision"],
        "data_version": observed_data_version,
        "requirements": spec.get("requirements"),
        "license": spec.get("license"),
        "benchmark_scope": spec.get("benchmark_scope"),
    }


def acquire(manifest_path: Path, source_root: Path) -> dict[str, Any]:
    manifest = _load_manifest(manifest_path)
    records: dict[str, Any] = {}
    for name, raw_spec in manifest["sources"].items():
        spec = dict(raw_spec)
        try:
            if spec["kind"] == "git":
                records[str(name)] = _git_source(str(name), spec, source_root)
            elif spec["kind"] in {"http", "gated_http"}:
                records[str(name)] = _http_source(str(name), spec, source_root)
            elif spec["kind"] == "pip":
                records[str(name)] = _pip_source(str(name), spec, source_root)
            else:
                raise ValueError(f"unsupported source kind {spec['kind']!r}")
        except Exception as exc:
            records[str(name)] = {
                "status": "failed",
                "kind": spec.get("kind"),
                "revision": spec.get("revision"),
                "reason": f"{type(exc).__name__}: {exc}",
                "license": spec.get("license"),
                "benchmark_scope": spec.get("benchmark_scope"),
            }
    try:
        manifest_label = str(manifest_path.relative_to(ROOT))
    except ValueError:
        manifest_label = manifest_path.name
    return {
        "schema": "agent-compaction-external-source-preflight/v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "manifest": manifest_label,
        "manifest_sha256": _sha256(manifest_path),
        "source_root_serialized": False,
        "sources": records,
        "counts": {
            "available": sum(item["status"] == "available" for item in records.values()),
            "gated": sum(item["status"] == "gated" for item in records.values()),
            "failed": sum(item["status"] == "failed" for item in records.values()),
        },
        "secrets_serialized": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    _load_repository_env()
    report = acquire(args.manifest.resolve(), _safe_root(args.root))
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 1 if report["counts"]["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
