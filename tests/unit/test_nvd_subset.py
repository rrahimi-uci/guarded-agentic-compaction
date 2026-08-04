from __future__ import annotations

from benchmarks.build.nvd_subset import _cwes, _meta, _severity


def test_nvd_meta_requires_digest_and_sizes() -> None:
    parsed = _meta(
        "lastModifiedDate:2026-08-04T00:00:00-04:00\n"
        "size:12\ngzSize:8\nsha256:" + "a" * 64
    )
    assert parsed["size"] == "12"


def test_nvd_normalization_extracts_cwes_and_cvss() -> None:
    cve = {
        "weaknesses": [{"description": [{"lang": "en", "value": "CWE-79"}]}],
        "metrics": {
            "cvssMetricV31": [
                {"cvssData": {"version": "3.1", "vectorString": "CVSS:3.1/X", "baseScore": 7.5}}
            ]
        },
    }
    assert _cwes(cve) == ["CWE-79"]
    assert _severity(cve) == [
        {"type": "3.1", "vector": "CVSS:3.1/X", "score": 7.5}
    ]
