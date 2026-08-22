"""Version-pinned Headroom bridge for the context-compression ablation.

The compiler never depends on Headroom.  This module is deliberately scoped to
the experiment: it runs Headroom's public ``compress(messages, model=...)`` API
at a model-visible evidence boundary and records what happened.  Any adapter
failure falls back to the byte-for-byte original payload so an unavailable or
incompatible optional dependency cannot turn into a silent benchmark variant.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from importlib import import_module
from typing import Any, Callable, Mapping, Sequence


HEADROOM_PACKAGE = "headroom-ai"
HEADROOM_VERSION = "0.5.18"


class HeadroomUnavailableError(RuntimeError):
    """Raised before an ablation run when its pinned optional dependency is absent."""


@dataclass(frozen=True)
class HeadroomAblationConfig:
    """The narrow, reproducible Headroom surface exercised by this repository."""

    package: str = HEADROOM_PACKAGE
    version: str = HEADROOM_VERSION
    model: str = "gpt-5.6-luna"
    api: str = "headroom.compress(messages, model=...)"
    scope: str = "single source-grounded JSON payload at a model-visible boundary"
    cross_session_memory: bool = False
    output_shaping: bool = False
    learning: bool = False
    retrieval_tool: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HeadroomCompression:
    """One attempted payload transformation, including every fail-closed fallback."""

    content: str
    tokens_before: int
    tokens_after: int
    tokens_saved: int
    compression_ratio: float
    transforms_applied: tuple[str, ...]
    applied: bool
    fallback_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "tokens_before": self.tokens_before,
            "tokens_after": self.tokens_after,
            "tokens_saved": self.tokens_saved,
            "compression_ratio": self.compression_ratio,
            "transforms_applied": list(self.transforms_applied),
            "applied": self.applied,
            "fallback_reason": self.fallback_reason,
        }


CompressCallable = Callable[..., Any]


class HeadroomCompressor:
    """Call Headroom without exposing its optional API to the main package.

    The adapter permits a test double so normal unit tests do not download models
    or depend on an installed third-party package.  Production experiment runs
    use :meth:`installed`, which verifies the exact package version first.
    """

    def __init__(
        self,
        compress: CompressCallable,
        *,
        config: HeadroomAblationConfig = HeadroomAblationConfig(),
        installed_version: str = HEADROOM_VERSION,
    ) -> None:
        if installed_version != config.version:
            raise HeadroomUnavailableError(
                f"{config.package}=={config.version} is required; found {installed_version}"
            )
        self._compress = compress
        self.config = config

    @classmethod
    def installed(
        cls, *, config: HeadroomAblationConfig = HeadroomAblationConfig()
    ) -> "HeadroomCompressor":
        try:
            module = import_module("headroom")
            compress = getattr(module, "compress")
            installed_version = str(getattr(module, "__version__"))
        except (ImportError, AttributeError) as exc:
            raise HeadroomUnavailableError(
                f"install {config.package}=={config.version} to run the Headroom ablation"
            ) from exc
        return cls(compress, config=config, installed_version=installed_version)

    def compress_json(
        self,
        content: str,
        *,
        required_fields: Sequence[str] = (),
    ) -> HeadroomCompression:
        """Compress one JSON payload, preserving required top-level source facts.

        Headroom is intentionally allowed to be lossy for the remaining payload;
        the live study's paired exact contract measures whether that changes an
        answer.  Invalid JSON, changed mandatory facts, or an incompatible result
        shape are never forwarded to the model.
        """

        try:
            original = json.loads(content)
        except json.JSONDecodeError as exc:
            return self._fallback(content, f"original_not_json:{type(exc).__name__}")
        if not isinstance(original, Mapping):
            return self._fallback(content, "original_not_json_object")
        try:
            # The public API deliberately protects user instructions.  Representing
            # the payload as an OpenAI-style tool result exercises the advertised
            # Headroom boundary while keeping the exact source data separate from
            # the task instruction that the agent receives.
            result = self._compress(
                [
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": "headroom-ablation",
                            "type": "function",
                            "function": {"name": "source_snapshot", "arguments": "{}"},
                        }],
                    },
                    {
                        "role": "tool",
                        "tool_call_id": "headroom-ablation",
                        "content": content,
                    },
                ],
                model=self.config.model,
            )
            messages = getattr(result, "messages", None)
            if not isinstance(messages, list) or len(messages) != 2:
                return self._fallback(content, "unexpected_message_shape")
            transformed = messages[1]
            if not isinstance(transformed, Mapping) or transformed.get("role") != "tool":
                return self._fallback(content, "unexpected_message_role")
            compressed = transformed.get("content")
            if not isinstance(compressed, str):
                return self._fallback(content, "non_string_content")
            candidate = json.loads(compressed)
            if not isinstance(candidate, Mapping):
                return self._fallback(content, "compressed_not_json_object")
            if any(candidate.get(field) != original.get(field) for field in required_fields):
                return self._fallback(content, "required_source_field_changed")
            before = int(getattr(result, "tokens_before", 0) or 0)
            after = int(getattr(result, "tokens_after", 0) or 0)
            saved = int(getattr(result, "tokens_saved", before - after) or 0)
            ratio = float(getattr(result, "compression_ratio", 0.0) or 0.0)
            transforms = tuple(str(value) for value in (getattr(result, "transforms_applied", ()) or ()))
            return HeadroomCompression(
                content=compressed,
                tokens_before=before,
                tokens_after=after,
                tokens_saved=max(0, saved),
                compression_ratio=ratio,
                transforms_applied=transforms,
                applied=compressed != content,
            )
        except Exception as exc:  # Third-party failures must retain the original evidence.
            return self._fallback(content, f"compression_error:{type(exc).__name__}")

    @staticmethod
    def _fallback(content: str, reason: str) -> HeadroomCompression:
        return HeadroomCompression(
            content=content,
            tokens_before=0,
            tokens_after=0,
            tokens_saved=0,
            compression_ratio=0.0,
            transforms_applied=(),
            applied=False,
            fallback_reason=reason,
        )


def aggregate_headroom(records: Sequence[HeadroomCompression]) -> dict[str, Any]:
    """Produce a compact, serializable audit of a condition's transformations."""

    fallbacks: dict[str, int] = {}
    for record in records:
        if record.fallback_reason:
            fallbacks[record.fallback_reason] = fallbacks.get(record.fallback_reason, 0) + 1
    return {
        "attempted_payloads": len(records),
        "applied_payloads": sum(record.applied for record in records),
        "fallback_payloads": sum(record.fallback_reason is not None for record in records),
        "tokens_before": sum(record.tokens_before for record in records),
        "tokens_after": sum(record.tokens_after for record in records),
        "tokens_saved": sum(record.tokens_saved for record in records),
        "fallback_reasons": dict(sorted(fallbacks.items())),
    }
