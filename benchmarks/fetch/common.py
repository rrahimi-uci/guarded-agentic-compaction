"""Policy-aware, checksum-verifying HTTP cache for public benchmark data."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping


class SourceFetchError(RuntimeError):
    """A public source failed without creating a valid cached artifact."""


class SourcePolicyError(SourceFetchError):
    """Acquisition stopped because configuration or access policy was violated."""


@dataclass(frozen=True, slots=True)
class FetchRecord:
    url: str
    path: str
    sha256: str
    bytes: int
    retrieved_at: str
    status: int
    response_headers: Mapping[str, str]
    cache_hit: bool

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["response_headers"] = dict(self.response_headers)
        return result


class SourceClient:
    """Bounded HTTP GET client with atomic content-addressed caching.

    Request headers are never serialized. Only non-sensitive response metadata is
    retained. HTTP 403 and 429 are hard policy stops rather than retry targets.
    """

    _SAFE_RESPONSE_HEADERS = (
        "Content-Type",
        "Content-Length",
        "ETag",
        "Last-Modified",
        "Cache-Control",
    )

    def __init__(
        self,
        cache_dir: str | Path,
        *,
        user_agent: str,
        minimum_interval_s: float = 0.0,
        timeout_s: float = 60.0,
        max_bytes: int = 2_000_000_000,
        max_cache_bytes: int = 40 * 1024**3,
        accept: str = "application/json,*/*",
    ) -> None:
        if not user_agent.strip():
            raise SourcePolicyError("a non-empty public-source user agent is required")
        if not accept.strip():
            raise SourcePolicyError("a non-empty public-source accept header is required")
        if (
            minimum_interval_s < 0
            or timeout_s <= 0
            or max_bytes < 1
            or max_cache_bytes < 1
        ):
            raise ValueError("invalid source client bounds")
        self.cache_dir = Path(cache_dir)
        self.user_agent = user_agent
        self.minimum_interval_s = float(minimum_interval_s)
        self.timeout_s = float(timeout_s)
        self.max_bytes = int(max_bytes)
        self.max_cache_bytes = int(max_cache_bytes)
        self.accept = accept
        self._lock = threading.RLock()
        self._last_request = 0.0

    def _cache_bytes(self) -> int:
        """Return current cache usage without following symlinks."""

        if not self.cache_dir.exists():
            return 0
        total = 0
        for root, directories, files in os.walk(self.cache_dir, followlinks=False):
            directories[:] = [
                name for name in directories if not (Path(root) / name).is_symlink()
            ]
            for name in files:
                path = Path(root) / name
                if not path.is_symlink():
                    total += path.stat().st_size
        return total

    def _paths(self, url: str, namespace: str) -> tuple[Path, Path]:
        if not namespace.strip() or Path(namespace).is_absolute():
            raise SourcePolicyError("cache namespace must be a non-empty relative path")
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        cache_root = self.cache_dir.resolve()
        root = (self.cache_dir / namespace).resolve()
        try:
            root.relative_to(cache_root)
        except ValueError as exc:
            raise SourcePolicyError("cache namespace escapes the configured cache") from exc
        return root / f"{key}.bin", root / f"{key}.metadata.json"

    @staticmethod
    def _digest(path: Path) -> tuple[str, int]:
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                size += len(chunk)
                digest.update(chunk)
        return digest.hexdigest(), size

    def _cached(
        self, data_path: Path, metadata_path: Path, *, expected_url: str
    ) -> FetchRecord | None:
        if not data_path.is_file() or not metadata_path.is_file():
            return None
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            observed_digest, observed_bytes = self._digest(data_path)
            if (
                metadata.get("schema") != "agent-compaction-source-fetch/v1"
                or metadata.get("url") != expected_url
                or observed_digest != metadata["sha256"]
                or observed_bytes != metadata["bytes"]
            ):
                raise SourceFetchError(f"cached source checksum mismatch: {data_path}")
            return FetchRecord(
                url=metadata["url"],
                path=str(data_path),
                sha256=observed_digest,
                bytes=observed_bytes,
                retrieved_at=metadata["retrieved_at"],
                status=int(metadata["status"]),
                response_headers=dict(metadata.get("response_headers", {})),
                cache_hit=True,
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise SourceFetchError(f"invalid cached source metadata: {metadata_path}") from exc

    def fetch(
        self,
        url: str,
        *,
        namespace: str,
        offline: bool = False,
    ) -> FetchRecord:
        if not url.startswith("https://"):
            raise SourcePolicyError("benchmark sources must use HTTPS")
        data_path, metadata_path = self._paths(url, namespace)
        cached = self._cached(data_path, metadata_path, expected_url=url)
        if cached is not None:
            return cached
        if offline:
            raise SourceFetchError(f"source is not cached for offline replay: {url}")

        existing_cache_bytes = self._cache_bytes()
        if existing_cache_bytes >= self.max_cache_bytes:
            raise SourcePolicyError("benchmark cache has reached its configured byte cap")

        data_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            delay = self.minimum_interval_s - (time.monotonic() - self._last_request)
            if delay > 0:
                time.sleep(delay)
            request = urllib.request.Request(
                url,
                headers={"User-Agent": self.user_agent, "Accept": self.accept},
                method="GET",
            )
            try:
                response = urllib.request.urlopen(request, timeout=self.timeout_s)
            except urllib.error.HTTPError as exc:
                if exc.code in (403, 429):
                    raise SourcePolicyError(
                        f"source returned policy status {exc.code}; acquisition stopped"
                    ) from exc
                raise SourceFetchError(f"source returned HTTP {exc.code}: {url}") from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                raise SourceFetchError(f"source request failed: {url}") from exc
            finally:
                self._last_request = time.monotonic()

            status = int(getattr(response, "status", 200))
            if status < 200 or status >= 300:
                response.close()
                raise SourceFetchError(f"source returned HTTP {status}: {url}")
            raw_length = response.headers.get("Content-Length")
            try:
                content_length = None if raw_length is None else int(raw_length)
            except (TypeError, ValueError) as exc:
                response.close()
                raise SourceFetchError("source returned an invalid Content-Length") from exc
            if content_length is not None and content_length < 0:
                response.close()
                raise SourceFetchError("source returned an invalid Content-Length")
            if content_length is not None and content_length > self.max_bytes:
                response.close()
                raise SourceFetchError("source exceeds configured maximum byte size")
            if (
                content_length is not None
                and existing_cache_bytes + content_length > self.max_cache_bytes
            ):
                response.close()
                raise SourcePolicyError(
                    "source would exceed the configured aggregate benchmark cache cap"
                )
            digest = hashlib.sha256()
            size = 0
            temp_fd, temp_name = tempfile.mkstemp(
                prefix=".fetch-", dir=str(data_path.parent)
            )
            metadata_temp: str | None = None
            try:
                safe_headers = {
                    name: response.headers[name]
                    for name in self._SAFE_RESPONSE_HEADERS
                    if response.headers.get(name) is not None
                }
                with os.fdopen(temp_fd, "wb") as handle, response:
                    while True:
                        chunk = response.read(1 << 20)
                        if not chunk:
                            break
                        size += len(chunk)
                        if size > self.max_bytes:
                            raise SourceFetchError(
                                "source exceeded configured maximum while streaming"
                            )
                        if existing_cache_bytes + size > self.max_cache_bytes:
                            raise SourcePolicyError(
                                "source exceeded the configured aggregate benchmark cache cap"
                            )
                        digest.update(chunk)
                        handle.write(chunk)
                    handle.flush()
                    os.fsync(handle.fileno())
                if content_length is not None and size != content_length:
                    raise SourceFetchError(
                        "source body length differs from declared Content-Length"
                    )
                retrieved_at = datetime.now(timezone.utc).isoformat().replace(
                    "+00:00", "Z"
                )
                payload = {
                    "schema": "agent-compaction-source-fetch/v1",
                    "url": url,
                    "sha256": digest.hexdigest(),
                    "bytes": size,
                    "retrieved_at": retrieved_at,
                    "status": status,
                    "response_headers": safe_headers,
                }
                metadata_bytes = (
                    json.dumps(payload, indent=2, sort_keys=True) + "\n"
                ).encode("utf-8")
                if (
                    existing_cache_bytes + size + len(metadata_bytes)
                    > self.max_cache_bytes
                ):
                    raise SourcePolicyError(
                        "source and metadata exceed the aggregate benchmark cache cap"
                    )
                metadata_fd, metadata_temp = tempfile.mkstemp(
                    prefix=".fetch-metadata-", dir=str(data_path.parent)
                )
                with os.fdopen(metadata_fd, "wb") as handle:
                    handle.write(metadata_bytes)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, data_path)
                os.replace(metadata_temp, metadata_path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
                if metadata_temp is not None and os.path.exists(metadata_temp):
                    os.unlink(metadata_temp)
            return FetchRecord(
                url=url,
                path=str(data_path),
                sha256=digest.hexdigest(),
                bytes=size,
                retrieved_at=retrieved_at,
                status=status,
                response_headers=safe_headers,
                cache_hit=False,
            )


def validate_sec_user_agent(value: str | None) -> str:
    candidate = (value or "").strip()
    if "@" not in candidate or len(candidate.split()) < 2:
        raise SourcePolicyError(
            "SEC_USER_AGENT must contain a genuine project/entity name and contact address"
        )
    return candidate
