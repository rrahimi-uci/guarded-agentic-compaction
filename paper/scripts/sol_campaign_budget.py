"""Conservative GPT-5.6 Sol accounting in the existing $300 campaign ledger.

The historical ledger's root Luna rates stay unchanged. Sol requests record
their own prices per row, and every reservation still counts toward the same
campaign and stage caps through the original atomic Ledger.transaction().
"""
import hashlib
import json
import math
from types import SimpleNamespace
import time
import uuid

from adaptive_campaign_budget import Ledger, BudgetExceeded, TOTAL_CAP, STAGE_CAPS, MAX_PAYLOAD_BYTES, clean

MODEL = "gpt-5.6-sol"
# Official model page checked 2026-11-06: $4 input and $20 output per million.
# 1.25x input covers cache-write billing and deliberately ignores cache discounts.
INPUT_UPPER = 5.0
OUTPUT_RATE = 20.0
MAX_OUTPUT = 4096
PRICE_SOURCE = "https://developers.openai.com/api/docs/models/gpt-5.6-sol"


class SolLedger:
    def __init__(self, path):
        self.ledger = Ledger(path)

    def reserve(self, payload, *, stage, task, arm):
        if stage not in STAGE_CAPS or payload.get("model") != MODEL:
            raise ValueError("wrong stage or model")
        blob = json.dumps(clean(payload), ensure_ascii=False, sort_keys=True).encode()
        if len(blob) > MAX_PAYLOAD_BYTES:
            raise BudgetExceeded("provider payload exceeds pinned bound")
        output = payload.get("max_completion_tokens")
        if type(output) is not int or not 1 <= output <= MAX_OUTPUT:
            raise ValueError("unbounded completion")
        bound = len(blob) + 8192
        reserved = (bound * INPUT_UPPER + output * OUTPUT_RATE) / 1e6
        rid = uuid.uuid4().hex
        with self.ledger.transaction() as data:
            if any(r["status"].endswith("_STOP") for r in data["requests"]):
                raise BudgetExceeded("campaign stopped after usage-bound violation")
            charged = lambda r: r.get("accounted_upper_usd", r["reserved_usd"])
            used = math.fsum(charged(r) for r in data["requests"])
            stage_used = math.fsum(charged(r) for r in data["requests"] if r["stage"] == stage)
            task_calls = sum(r["stage"] == stage and r["task"] == task and r["arm"] == arm
                             for r in data["requests"])
            if (used + reserved > TOTAL_CAP or stage_used + reserved > STAGE_CAPS[stage]
                    or task_calls >= 96):
                raise BudgetExceeded("campaign, stage or per-task request cap")
            data["requests"].append({"id": rid, "stage": stage, "task": task, "arm": arm,
                "model": MODEL, "status": "reserved", "reserved_usd": reserved,
                "input_token_bound": bound, "max_output_tokens": output,
                "input_rate_upper_per_million": INPUT_UPPER,
                "output_rate_per_million": OUTPUT_RATE,
                "price_source": PRICE_SOURCE,
                "payload_sha256": hashlib.sha256(blob).hexdigest(),
                "started_unix": time.time()})
        return rid

    def finish(self, rid, usage=None, *, status="complete", response_model=None):
        stopped = False
        with self.ledger.transaction() as data:
            row = next(r for r in data["requests"] if r["id"] == rid)
            if row["status"] != "reserved" or row["model"] != MODEL:
                raise ValueError("request not reserved for this model")
            row["status"] = status
            row["response_model"] = response_model
            if usage is None:
                row["status"] = status + "_usage_unknown"
            else:
                inp, out = usage.get("prompt_tokens"), usage.get("completion_tokens")
                if type(inp) is not int or type(out) is not int or min(inp, out) < 0:
                    row["status"] = "invalid_usage_reservation_retained"
                else:
                    row["usage"] = usage
                    row["accounted_upper_usd"] = (inp * INPUT_UPPER + out * OUTPUT_RATE) / 1e6
                    if inp > row["input_token_bound"] or out > row["max_output_tokens"]:
                        row["status"] = "usage_exceeded_reservation_STOP"
                        stopped = True
        if stopped:
            raise BudgetExceeded("provider usage exceeded conservative reservation")


class SolBudgetClient:
    def __init__(self, path, *, stage, task, arm):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(max_retries=0, timeout=90, base_url="https://api.openai.com/v1")
        self.ledger = SolLedger(path)
        self.stage, self.task, self.arm = stage, task, arm
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, **kwargs):
        kwargs = clean(kwargs)
        kwargs.update(model=MODEL, max_completion_tokens=MAX_OUTPUT,
                      reasoning_effort="none", store=False, service_tier="default")
        for key in ("temperature", "top_p", "max_tokens"):
            kwargs.pop(key, None)
        rid = self.ledger.reserve(kwargs, stage=self.stage, task=self.task, arm=self.arm)
        try:
            response = await self.client.chat.completions.create(**kwargs)
        except BaseException:
            self.ledger.finish(rid, status="provider_request_failed")
            raise
        self.ledger.finish(rid, response.usage.model_dump() if response.usage else None,
                           response_model=response.model)
        return response

    async def close(self):
        await self.client.close()
