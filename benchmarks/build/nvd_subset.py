"""Acquire and retain the NVD records referenced by a frozen case candidate pool.

The implementation uses NVD's annual JSON 2.0 feeds instead of issuing hundreds
of per-CVE API calls. Feed META files are retained and their uncompressed SHA-256
and size declarations are verified before any record is accepted.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

from benchmarks.fetch.common import SourceClient, SourceFetchError
from benchmarks.fetch.vulnerability import PUBLIC_USER_AGENT


BASE = "https://nvd.nist.gov/feeds/json/cve/2.0"
SCHEMA = "agent-compaction-nvd-subset/v1"


def _meta(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip()
    required = {"lastModifiedDate", "size", "gzSize", "sha256"}
    if not required <= set(result):
        raise SourceFetchError(f"NVD META is missing {sorted(required - set(result))}")
    return result


def _verify_gzip(path: Path, meta: dict[str, str]) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with gzip.open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
            size += len(chunk)
    observed = digest.hexdigest()
    if observed.casefold() != meta["sha256"].casefold() or size != int(meta["size"]):
        raise SourceFetchError("NVD feed does not match its META digest/size")
    return observed, size


def _severity(cve: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for metric_name, values in cve.get("metrics", {}).items():
        if not metric_name.startswith("cvssMetric"):
            continue
        for item in values:
            data = item.get("cvssData", {})
            result.append(
                {
                    "type": str(data.get("version", metric_name)),
                    "vector": data.get("vectorString"),
                    "score": data.get("baseScore"),
                }
            )
    return result


def _cwes(cve: dict[str, Any]) -> list[str]:
    return sorted(
        {
            str(item["value"])
            for weakness in cve.get("weaknesses", [])
            for item in weakness.get("description", [])
            if str(item.get("value", "")).startswith("CWE-")
        }
    )


def referenced_cves(cases_path: Path) -> set[str]:
    result: set[str] = set()
    for line in cases_path.read_text(encoding="utf-8").splitlines():
        raw = json.loads(line)
        result.update(
            item
            for item in raw.get("metadata", {}).get("lineage_ids", [])
            if isinstance(item, str) and item.startswith("CVE-")
        )
    return result


def build_subset(
    *, cases_path: Path, cache_dir: Path, output_path: Path, offline: bool = False
) -> dict[str, Any]:
    wanted = referenced_cves(cases_path)
    years = sorted({cve.split("-", 2)[1] for cve in wanted})
    client = SourceClient(
        cache_dir,
        user_agent=PUBLIC_USER_AGENT,
        minimum_interval_s=1.0,
        timeout_s=240,
    )
    records: dict[str, Any] = {}
    feeds: dict[str, Any] = {}
    for year in years:
        stem = f"nvdcve-2.0-{year}"
        meta_record = client.fetch(
            f"{BASE}/{stem}.meta", namespace="vulnerability/nvd-feeds", offline=offline
        )
        gz_record = client.fetch(
            f"{BASE}/{stem}.json.gz", namespace="vulnerability/nvd-feeds", offline=offline
        )
        meta = _meta(Path(meta_record.path).read_text(encoding="utf-8"))
        uncompressed_sha, uncompressed_bytes = _verify_gzip(Path(gz_record.path), meta)
        with gzip.open(gz_record.path, "rt", encoding="utf-8") as handle:
            payload = json.load(handle)
        for wrapper in payload.get("vulnerabilities", []):
            cve = wrapper.get("cve", {})
            cve_id = str(cve.get("id", ""))
            if cve_id not in wanted:
                continue
            records[cve_id] = {
                "cve_id": cve_id,
                "status": cve.get("vulnStatus"),
                "published": cve.get("published"),
                "modified": cve.get("lastModified"),
                "severity": _severity(cve),
                "cwe_ids": _cwes(cve),
                "_source": {
                    "source": "NVD",
                    "record_id": cve_id,
                    "snapshot_digest": gz_record.sha256,
                    "field_families": ["severity", "cwe", "status", "dates"],
                },
            }
        feeds[year] = {
            "url": gz_record.url,
            "compressed_sha256": gz_record.sha256,
            "compressed_bytes": gz_record.bytes,
            "uncompressed_sha256": uncompressed_sha,
            "uncompressed_bytes": uncompressed_bytes,
            "last_modified": meta["lastModifiedDate"],
            "meta_sha256": meta_record.sha256,
        }
    result = {
        "schema": SCHEMA,
        "source": "NVD JSON 2.0 annual feeds",
        "requested_cves": len(wanted),
        "retained_cves": len(records),
        "missing_cves": sorted(wanted - set(records)),
        "feeds": feeds,
        "records": records,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--cache", default=Path("benchmarks/.cache"), type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    result = build_subset(
        cases_path=args.cases,
        cache_dir=args.cache,
        output_path=args.out,
        offline=args.offline,
    )
    print(
        json.dumps(
            {
                "requested_cves": result["requested_cves"],
                "retained_cves": result["retained_cves"],
                "missing_cves": result["missing_cves"],
                "feeds": sorted(result["feeds"]),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
