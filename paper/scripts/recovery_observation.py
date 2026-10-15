"""Capture numeric SDK usage and safe failure locations without provider content."""
from __future__ import annotations
import traceback
from pathlib import Path
from agents.models.interface import Model


def safe_usage(response):
    u = response.usage
    return {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
            "cached_input_tokens": u.input_tokens_details.cached_tokens,
            "cache_write_tokens": getattr(u.input_tokens_details, "cache_write_tokens", 0),
            "total_tokens": u.total_tokens}


def safe_error(exc, stage):
    return {"stage": stage, "error_type": type(exc).__name__,
            "cause_type": type(exc.__cause__).__name__ if exc.__cause__ else None,
            "frames": [{"file": Path(f.filename).name, "function": f.name, "line": f.lineno}
                       for f in traceback.extract_tb(exc.__traceback__)]}


class ObservedModel(Model):
    def __init__(self, wrapped, record):
        self.wrapped, self.record = wrapped, record

    async def get_response(self, *args, **kwargs):
        self.record["stage"] = "model_request"
        self.record["requests_started"] += 1
        response = await self.wrapped.get_response(*args, **kwargs)
        self.record["usage_observations"].append(safe_usage(response))
        self.record["stage"] = "runner_processing"
        return response

    async def stream_response(self, *args, **kwargs):
        raise NotImplementedError("non-streaming study")
        yield
