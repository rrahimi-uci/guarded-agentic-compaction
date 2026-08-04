"""HMDA public-record acquisition with no identity or enrichment joins."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode

from .common import FetchRecord, SourceClient


PUBLIC_USER_AGENT = "agent-compaction-research/0.5 (public HMDA benchmark)"


def client(cache_dir: str | Path) -> SourceClient:
    return SourceClient(
        cache_dir,
        user_agent=PUBLIC_USER_AGENT,
        minimum_interval_s=0.2,
        timeout_s=180,
        accept="text/csv,*/*",
    )


def fetch_public_lar_csv(
    *,
    year: int,
    states: tuple[str, ...],
    cache_dir: str | Path,
    actions_taken: tuple[int, ...] = (),
    offline: bool = False,
) -> FetchRecord:
    if year < 2018 or year > 2100:
        raise ValueError("HMDA public LAR year must be 2018 or later")
    if not states or any(len(state) != 2 or not state.isalpha() for state in states):
        raise ValueError("states must contain two-letter state abbreviations")
    params: list[tuple[str, str]] = [("years", str(year))]
    params.extend(("states", state.upper()) for state in sorted(set(states)))
    params.extend(("actions_taken", str(action)) for action in sorted(set(actions_taken)))
    # This is the official Data Browser CSV route used by the public application.
    url = "https://ffiec.cfpb.gov/v2/data-browser-api/view/csv?" + urlencode(params)
    return client(cache_dir).fetch(
        url, namespace=f"hmda/lar/{year}", offline=offline
    )
