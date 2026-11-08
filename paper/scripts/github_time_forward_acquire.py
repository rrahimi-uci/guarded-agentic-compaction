"""Acquire a time-forward GitHub snapshot: records created after the pinned dataset's last day.

The pinned Hugging Face dataset (``helmo/github-issues``) stops at 2025-06-13 and has not been
revised since, so a time-forward cohort must come from the GitHub REST API. This script pulls
every issue and pull request of one repository created strictly after a cutoff, plus the bodies
of each record's comments, and writes a parquet whose columns mirror the pinned snapshot (the
REST issue object plus ``comments`` as a list of comment bodies), with a source manifest carrying
the cutoff, fetch time, counts and the parquet digest. Provider-free; read-only public data;
authenticated through ``gh auth token`` for rate-limit headroom.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[2]
API = "https://api.github.com"


#: Credential-shaped strings that public issue text sometimes carries (pasted keys). They
#: are not part of any task contract and GitHub push protection refuses a commit holding
#: them, so they are replaced before the snapshot is written; each replacement is counted.
REDACT = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "<redacted-aws-key-id>"),
    (re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}"), "<redacted-github-token>"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "<redacted-github-token>"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"), "<redacted-api-key>"),
    (re.compile(r"\bhf_[A-Za-z0-9]{20,}"), "<redacted-hf-token>"),
    (re.compile(r"\bxox[abpr]-[A-Za-z0-9-]{10,}"), "<redacted-slack-token>"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"), "<redacted-private-key>"),
]


def redact(text: Any, counter: dict[str, int]) -> Any:
    if not isinstance(text, str):
        return text
    for pattern, replacement in REDACT:
        text, n = pattern.subn(replacement, text)
        if n:
            counter[replacement] = counter.get(replacement, 0) + n
    return text


def redact_records(records: list[dict[str, Any]]) -> dict[str, int]:
    counter: dict[str, int] = {}
    for row in records:
        row["title"] = redact(row.get("title"), counter)
        row["body"] = redact(row.get("body"), counter)
        row["comments"] = [redact(c, counter) for c in (row.get("comments") or [])]
    return counter


def _token() -> str:
    return subprocess.run(["gh", "auth", "token"], check=True, capture_output=True, text=True).stdout.strip()


def _get(url: str, token: str) -> tuple[Any, dict[str, str]]:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                                               "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "guarded-agentic-compaction-acquire"})
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8")), {k.lower(): v for k, v in resp.headers.items()}
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 429):
                reset = float(exc.headers.get("x-ratelimit-reset", time.time() + 60))
                time.sleep(max(5.0, reset - time.time() + 1))
                continue
            if exc.code >= 500:
                time.sleep(2 ** attempt)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException):
            # transient network failure (timeout, reset): back off and retry
            time.sleep(min(60, 5 * 2 ** attempt))
    raise RuntimeError(f"gave up on {url}")


def _issues(repo: str, cutoff: str, token: str) -> Iterator[dict[str, Any]]:
    page = 1
    while True:
        q = urllib.parse.urlencode({"state": "all", "sort": "created", "direction": "desc", "per_page": 100, "page": page})
        batch, _ = _get(f"{API}/repos/{repo}/issues?{q}", token)
        if not batch:
            return
        for item in batch:
            if item["created_at"][:10] <= cutoff:
                return
            yield item
        page += 1


def _search_pull_requests(repo: str, cutoff: str, token: str, until: str) -> Iterator[dict[str, Any]]:
    """Same records as ``_issues`` restricted to pull requests, listed one creation day at a time.

    ``/repos/{repo}/issues`` refuses deep pagination (HTTP 422) on very active repositories; the
    search API returns the same issue-shaped objects (``pull_request.merged_at``, ``comments`` count)
    and caps each query at 1,000 results, so each UTC day is one query. Newest day first, as ``_issues``.
    """

    import datetime as dt

    day = dt.date.fromisoformat(until)
    stop = dt.date.fromisoformat(cutoff)
    while day > stop:
        page, seen, items = 1, 0, []
        while True:
            q = urllib.parse.urlencode({"q": f"repo:{repo} is:pr created:{day.isoformat()}", "sort": "created",
                                        "order": "desc", "per_page": 100, "page": page})
            batch, _ = _get(f"{API}/search/issues?{q}", token)
            time.sleep(2.2)  # search API: 30 requests per minute
            total = int(batch.get("total_count", 0))
            if total > 1000:
                raise RuntimeError(f"{repo} {day}: {total} pull requests exceed the search cap of 1,000 per query")
            items.extend(batch.get("items") or [])
            seen += len(batch.get("items") or [])
            if seen >= total or not batch.get("items"):
                break
            page += 1
        items.sort(key=lambda it: it["created_at"], reverse=True)
        yield from (it for it in items if it.get("pull_request"))
        day -= dt.timedelta(days=1)


def _comments(repo: str, number: int, token: str) -> list[str]:
    bodies: list[str] = []
    page = 1
    while True:
        q = urllib.parse.urlencode({"per_page": 100, "page": page})
        batch, _ = _get(f"{API}/repos/{repo}/issues/{number}/comments?{q}", token)
        if not batch:
            return bodies
        bodies.extend(str(c.get("body") or "") for c in batch)
        if len(batch) < 100:
            return bodies
        page += 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default="huggingface/datasets")
    ap.add_argument("--cutoff", default="2025-06-13", help="records created strictly after this UTC day are kept")
    ap.add_argument("--out", type=Path, default=ROOT / "paper/results/datasets/github_time_forward/huggingface__datasets")
    ap.add_argument("--list-via-search", default=None, metavar="UNTIL_DAY",
                    help="list pull requests through the search API one creation day at a time, from UNTIL_DAY back to "
                         "the cutoff (for repositories where /issues refuses deep pagination); implies --pull-requests-only")
    ap.add_argument("--pull-requests-only", action="store_true",
                    help="keep only pull requests (the PR-outcome study never reads plain issues); saves the comment requests for issues")
    args = ap.parse_args(argv)
    import pandas as pd

    token = _token()
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    records: list[dict[str, Any]] = []
    # Resumable: comment bodies already fetched are kept on disk next to the snapshot, so an
    # interrupted acquisition restarts without re-spending its comment requests. The cache is not
    # part of the snapshot; the parquet and manifest are written only after a complete listing.
    args.out.mkdir(parents=True, exist_ok=True)
    cache_path = args.out / ".comments_cache.jsonl"
    cache: dict[int, list[str]] = {}
    if cache_path.exists():
        for line in cache_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                cache[int(row["number"])] = list(row["comments"])
    cache_handle = cache_path.open("a", encoding="utf-8")
    if args.list_via_search:
        args.pull_requests_only = True
        items = _search_pull_requests(args.repo, args.cutoff, token, args.list_via_search)
    else:
        items = _issues(args.repo, args.cutoff, token)
    if args.pull_requests_only:
        items = (item for item in items if item.get("pull_request"))
    for i, item in enumerate(items):
        row = dict(item)
        number = int(item["number"])
        if not int(item.get("comments") or 0):
            row["comments"] = []
        elif number in cache:
            row["comments"] = cache[number]
        else:
            row["comments"] = _comments(args.repo, number, token)
            cache_handle.write(json.dumps({"number": number, "comments": row["comments"]}) + "\n")
            cache_handle.flush()
        records.append(row)
        if (i + 1) % 100 == 0:
            print(f"[acquire] {i + 1} records, latest created {item['created_at']}", flush=True)
    if not records:
        print("[acquire] no records after cutoff")
        return 1
    redactions = redact_records(records)
    frame = pd.DataFrame(records)
    for col in ("created_at", "updated_at", "closed_at"):
        frame[col] = pd.to_datetime(frame[col], utc=True)
    args.out.mkdir(parents=True, exist_ok=True)
    parquet = args.out / "snapshot.parquet"
    frame.to_parquet(parquet, index=False)
    digest = hashlib.sha256(parquet.read_bytes()).hexdigest()
    manifest = {
        "schema": "agent-compaction-time-forward-snapshot/v1",
        "repository": args.repo, "source": "GitHub REST API v2022-11-28, /repos/{repo}/issues (state=all) and /issues/{n}/comments",
        "created_after_utc_day": args.cutoff, "fetch_started_utc": started, "fetch_completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "records": len(records), "pull_requests": int(sum(1 for r in records if r.get("pull_request"))),
        "issues": int(sum(1 for r in records if not r.get("pull_request"))),
        "created_at_range": [frame["created_at"].min().isoformat(), frame["created_at"].max().isoformat()],
        "parquet_path": str(parquet.relative_to(ROOT)) if parquet.is_relative_to(ROOT) else str(parquet), "parquet_bytes": parquet.stat().st_size, "parquet_sha256": digest,
        "columns_mirroring_pinned_snapshot": True,
        "pull_requests_only": bool(args.pull_requests_only),
        "listing": ("GET /search/issues q='repo:{repo} is:pr created:DAY', one query per UTC day, through "
                    + args.list_via_search) if args.list_via_search else "GET /repos/{repo}/issues state=all",
        "credential_shaped_strings_redacted": redactions,
        "licence_note": "public GitHub issue and pull-request metadata and comment bodies; same provenance class as the pinned snapshot",
    }
    (args.out / "source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"[acquire] wrote {parquet} ({len(records)} records, sha256 {digest[:12]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
