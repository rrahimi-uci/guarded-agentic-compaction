"""Policy-gated SEC submissions, Company Facts, and filing acquisition."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from .common import FetchRecord, SourceClient, SourceFetchError, validate_sec_user_agent


_CLIENTS: dict[tuple[str, str], SourceClient] = {}
_CLIENTS_LOCK = threading.RLock()


def sec_client(cache_dir: str | Path, *, offline: bool = False) -> SourceClient:
    # Offline replay cannot emit a request, so it does not require contact
    # configuration. Online clients are shared per cache/contact identity so the
    # five-request/second throttle applies across issuer, index, and filing calls.
    user_agent = (
        "agent-compaction-offline-cache-replay/1.0"
        if offline
        else validate_sec_user_agent(os.environ.get("SEC_USER_AGENT"))
    )
    key = (str(Path(cache_dir).resolve()), user_agent)
    with _CLIENTS_LOCK:
        if key not in _CLIENTS:
            _CLIENTS[key] = SourceClient(
                cache_dir,
                user_agent=user_agent,
                minimum_interval_s=0.2,
                timeout_s=60,
            )
        return _CLIENTS[key]


def fetch_issuer_sources(
    cik: str,
    cache_dir: str | Path,
    *,
    offline: bool = False,
) -> dict[str, FetchRecord]:
    if not cik.isdigit() or len(cik) > 10:
        raise ValueError("CIK must contain at most ten digits")
    padded = cik.zfill(10)
    client = sec_client(cache_dir, offline=offline)
    records = {
        "submissions": client.fetch(
            f"https://data.sec.gov/submissions/CIK{padded}.json",
            namespace="sec/submissions",
            offline=offline,
        ),
        "companyfacts": client.fetch(
            f"https://data.sec.gov/api/xbrl/companyfacts/CIK{padded}.json",
            namespace="sec/companyfacts",
            offline=offline,
        ),
    }
    for name, record in records.items():
        try:
            payload: Any = json.loads(Path(record.path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SourceFetchError(f"SEC {name} response is not valid JSON") from exc
        if not isinstance(payload, dict) or str(payload.get("cik", "")).zfill(10) != padded:
            raise SourceFetchError(f"SEC {name} response CIK does not match request")
    return records


def fetch_filing_index(
    cik: str, accession: str, cache_dir: str | Path, *, offline: bool = False
) -> FetchRecord:
    """Fetch and identity-check one EDGAR filing directory index."""

    if not cik.isdigit() or not accession.replace("-", "").isdigit():
        raise ValueError("filing index requires numeric CIK/accession")
    padded = cik.zfill(10)
    compact = accession.replace("-", "")
    record = sec_client(cache_dir, offline=offline).fetch(
        f"https://www.sec.gov/Archives/edgar/data/{int(padded)}/{compact}/index.json",
        namespace="sec/filing-index",
        offline=offline,
    )
    payload = json.loads(Path(record.path).read_text(encoding="utf-8"))
    directory = payload.get("directory", {})
    if str(directory.get("name", "")) != compact:
        raise SourceFetchError("SEC filing index directory does not match accession")
    return record


def fetch_filing_file(
    cik: str,
    accession: str,
    filename: str,
    cache_dir: str | Path,
    *,
    offline: bool = False,
) -> FetchRecord:
    """Fetch one filename already discovered in a validated filing index."""

    if not filename or "/" in filename or "\\" in filename or filename.startswith("."):
        raise ValueError("SEC filing filename must be one safe basename")
    padded = cik.zfill(10)
    compact = accession.replace("-", "")
    return sec_client(cache_dir, offline=offline).fetch(
        f"https://www.sec.gov/Archives/edgar/data/{int(padded)}/{compact}/{filename}",
        namespace="sec/filing-documents",
        offline=offline,
    )
