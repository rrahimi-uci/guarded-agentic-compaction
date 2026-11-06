"""Cross-process, fail-closed accounting for the authorized $300 campaign.

Only public benchmark text goes to the provider. No credentials or prompts are
written to the ledger. Unknown usage retains its full reservation.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
from types import SimpleNamespace
import time
import uuid

MODEL = "gpt-5.6-luna"
TOTAL_CAP = 300.0
STAGE_CAPS = {"pilot": 30.0, "discovery": 30.0, "calibration": 60.0, "test": 180.0}
# Official model page checked 2026-11-06: .20 input / .02 cache read / 1.20 output.
# Budget at .50 input (covers long cache writes); never claim this is an invoice.
INPUT_UPPER = .50
INPUT_REFERENCE = .20
OUTPUT_RATE = 1.20
PRICE_SOURCE = "https://developers.openai.com/api/docs/models/gpt-5.6-luna"
MAX_OUTPUT = 4096
MAX_PAYLOAD_BYTES = 200_000


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items() if type(v).__name__ not in {"Omit", "NotGiven"}}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    return value


class BudgetExceeded(RuntimeError):
    pass


class Ledger:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def transaction(self):
        with self.path.with_suffix(".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            data = json.loads(self.path.read_text()) if self.path.exists() else {
                "schema": "gac-adaptive-campaign-ledger-v1", "cap_usd": TOTAL_CAP,
                "stage_caps": STAGE_CAPS, "requests": [], "price_source": PRICE_SOURCE,
                "input_upper_per_million": INPUT_UPPER, "output_per_million": OUTPUT_RATE}
            if (data["cap_usd"] != TOTAL_CAP or data["stage_caps"] != STAGE_CAPS
                    or data["input_upper_per_million"] != INPUT_UPPER or data["output_per_million"] != OUTPUT_RATE):
                raise ValueError("campaign limits changed; refusing to reset ledger")
            yield data
            data["accounted_upper_usd"] = math.fsum(r.get("accounted_upper_usd", r["reserved_usd"]) for r in data["requests"])
            tmp = self.path.with_suffix(".tmp")
            with tmp.open("w") as output:
                output.write(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n")
                output.flush()
                os.fsync(output.fileno())
            tmp.replace(self.path)

    def reserve(self, payload, *, stage, task, arm):
        if stage not in STAGE_CAPS or payload.get("model") != MODEL:
            raise ValueError("unsealed stage or model")
        blob = json.dumps(clean(payload), ensure_ascii=False, sort_keys=True).encode()
        if len(blob) > MAX_PAYLOAD_BYTES:
            raise BudgetExceeded("text payload exceeds the pinned short-context bound")
        output = payload.get("max_completion_tokens")
        if type(output) is not int or not 1 <= output <= MAX_OUTPUT:
            raise ValueError("unbounded completion")
        amount = ((len(blob) + 8192) * INPUT_UPPER + output * OUTPUT_RATE) / 1e6
        rid = uuid.uuid4().hex
        with self.transaction() as data:
            if any(r["status"].endswith("_STOP") for r in data["requests"]):
                raise BudgetExceeded("campaign stopped after a reservation-bound violation")
            charged = lambda r: r.get("accounted_upper_usd", r["reserved_usd"])
            used = math.fsum(charged(r) for r in data["requests"])
            stage_used = math.fsum(charged(r) for r in data["requests"] if r["stage"] == stage)
            task_calls = sum(r["stage"] == stage and r["task"] == task and r["arm"] == arm for r in data["requests"])
            if used + amount > TOTAL_CAP or stage_used + amount > STAGE_CAPS[stage] or task_calls >= 48:
                raise BudgetExceeded("campaign, stage, or 48-request arm/task limit reached")
            data["requests"].append({"id": rid, "stage": stage, "task": task, "arm": arm,
                "model": MODEL, "status": "reserved", "reserved_usd": amount,
                "input_token_bound": len(blob) + 8192, "max_output_tokens": output,
                "payload_sha256": hashlib.sha256(blob).hexdigest(), "started_unix": time.time()})
        return rid

    def finish(self, rid, usage=None, *, status="complete", response_model=None):
        with self.transaction() as data:
            row = next(r for r in data["requests"] if r["id"] == rid)
            if row["status"] != "reserved":
                raise ValueError("request already settled")
            row["status"] = status
            row["response_model"] = response_model
            if usage is not None:
                inp, out = usage.get("prompt_tokens"), usage.get("completion_tokens")
                if type(inp) is not int or type(out) is not int or min(inp, out) < 0:
                    row["status"] = "invalid_usage_reservation_retained"
                else:
                    row["usage"] = usage
                    upper = (inp * INPUT_UPPER + out * OUTPUT_RATE) / 1e6
                    row["accounted_upper_usd"] = upper
                    row["uncached_reference_usd"] = (inp * INPUT_REFERENCE + out * OUTPUT_RATE) / 1e6
                    if inp > row["input_token_bound"] or out > row["max_output_tokens"]:
                        row["status"] = "usage_exceeded_reservation_STOP"
            else:
                row["status"] = status + "_usage_unknown"
        if row["status"] == "usage_exceeded_reservation_STOP":
            raise BudgetExceeded("provider usage exceeded conservative reservation; stop campaign")


class BudgetClient:
    """Duck-typed AsyncOpenAI client shared by Agents SDK and upstream generator."""
    def __init__(self, ledger, *, stage, task, arm):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(max_retries=0, timeout=60, base_url="https://api.openai.com/v1")
        self.ledger, self.stage, self.task, self.arm = ledger, stage, task, arm
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))
        self.base_url = self.client.base_url

    def with_options(self, **kwargs):
        if set(kwargs) - {"max_retries"} or kwargs.get("max_retries", 0) != 0:
            raise ValueError("client options cannot bypass campaign limits")
        return self

    async def create(self, **kwargs):
        kwargs = clean(kwargs)
        kwargs.update(model=MODEL, max_completion_tokens=MAX_OUTPUT,
                      reasoning_effort="low", store=False, service_tier="default")
        for key in ("temperature", "top_p", "max_tokens"):
            kwargs.pop(key, None)
        if kwargs.get("stream"):
            kwargs["stream_options"] = {"include_usage": True}
        rid = self.ledger.reserve(kwargs, stage=self.stage, task=self.task, arm=self.arm)
        try:
            response = await self.client.chat.completions.create(**kwargs)
        except BaseException:
            self.ledger.finish(rid, status="provider_request_failed")
            raise
        if not kwargs.get("stream"):
            self.ledger.finish(rid, response.usage.model_dump() if response.usage else None,
                               response_model=response.model)
            return response

        async def stream():
            usage = None
            model = None
            status = "complete"
            try:
                async for chunk in response:
                    if chunk.usage:
                        usage = chunk.usage.model_dump()
                    model = getattr(chunk, "model", model)
                    yield chunk
            except BaseException:
                status = "stream_interrupted"
                raise
            finally:
                try:
                    await response.close()
                finally:
                    self.ledger.finish(rid, usage, status=status, response_model=model)
        return stream()

    async def close(self):
        await self.client.close()
