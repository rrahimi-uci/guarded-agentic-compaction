"""Fail-closed GPT-5.4 accounting in the existing $300 adaptive campaign ledger."""

from __future__ import annotations

import hashlib
import json
import math
import time
import uuid

from adaptive_campaign_budget import BudgetExceeded, Ledger, STAGE_CAPS, TOTAL_CAP, clean


MODEL = "gpt-5.4-2026-03-05"
INPUT_UPPER = 3.125  # 1.25 times the published $2.50/M uncached input rate.
OUTPUT_UPPER = 15.0  # Published $15/M output rate; cached-input discount ignored.
PRICE_SOURCE = "https://developers.openai.com/api/docs/models/gpt-5.4"
MAX_OUTPUT = 16384  # Match the official harness per-turn default.
MAX_PAYLOAD_BYTES = 200_000
TASK_PREFIX = "agenthop-st2-v1:"


class AgentHopBudget:
    def __init__(self, path):
        self.ledger = Ledger(path)

    def reserve(self, payload, *, task):
        if payload.get("model") != MODEL or not task.startswith(TASK_PREFIX):
            raise ValueError("wrong model or task namespace")
        blob = json.dumps(clean(payload), ensure_ascii=False, sort_keys=True).encode()
        if len(blob) > MAX_PAYLOAD_BYTES or payload.get("max_output_tokens") != MAX_OUTPUT:
            raise BudgetExceeded("request exceeds sealed payload/output limits")
        # Responses API previous_response_id hides accumulated context in the
        # request body. The official per-sample cumulative cap is 200k tokens.
        input_bound = 200_000
        reserved = (input_bound * INPUT_UPPER + MAX_OUTPUT * OUTPUT_UPPER) / 1e6
        rid = uuid.uuid4().hex
        with self.ledger.transaction() as data:
            if any(r["status"].endswith("_STOP") for r in data["requests"]):
                raise BudgetExceeded("campaign stopped after usage-bound violation")
            charged = lambda r: r.get("accounted_upper_usd", r["reserved_usd"])
            used = math.fsum(charged(r) for r in data["requests"])
            stage_used = math.fsum(charged(r) for r in data["requests"] if r["stage"] == "pilot")
            task_calls = sum(r["stage"] == "pilot" and r["task"] == task and r["arm"] == "baseline"
                             for r in data["requests"])
            if (used + reserved > TOTAL_CAP or stage_used + reserved > STAGE_CAPS["pilot"]
                    or task_calls >= 30):
                raise BudgetExceeded("campaign, pilot stage, or per-task request cap")
            data["requests"].append({
                "id": rid, "stage": "pilot", "task": task, "arm": "baseline",
                "model": MODEL, "status": "reserved", "reserved_usd": reserved,
                "input_token_bound": input_bound, "max_output_tokens": MAX_OUTPUT,
                "input_rate_upper_per_million": INPUT_UPPER,
                "output_rate_per_million": OUTPUT_UPPER,
                "price_source": PRICE_SOURCE,
                "payload_sha256": hashlib.sha256(blob).hexdigest(),
                "started_unix": time.time(),
            })
        return rid

    def finish(self, rid, usage=None, *, status="complete", response_model=None):
        stopped = False
        with self.ledger.transaction() as data:
            row = next(r for r in data["requests"] if r["id"] == rid)
            if row["status"] != "reserved" or row["model"] != MODEL:
                raise ValueError("request not reserved for AgentHop pilot")
            row["status"] = status
            row["response_model"] = response_model
            if usage is None:
                row["status"] = status + "_usage_unknown"
            else:
                inp, out = usage.get("input_tokens"), usage.get("output_tokens")
                if type(inp) is not int or type(out) is not int or min(inp, out) < 0:
                    row["status"] = "invalid_usage_reservation_retained"
                else:
                    row["usage"] = usage
                    row["accounted_upper_usd"] = (inp * INPUT_UPPER + out * OUTPUT_UPPER) / 1e6
                    if inp > row["input_token_bound"] or out > row["max_output_tokens"]:
                        row["status"] = "usage_exceeded_reservation_STOP"
                        stopped = True
        if stopped:
            raise BudgetExceeded("provider usage exceeded conservative reservation")


class AgentHopBudgetClient:
    def __init__(self, path, *, task):
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(max_retries=0, timeout=90, base_url="https://api.openai.com/v1")
        self.budget = AgentHopBudget(path)
        self.task = task

    async def create(self, **kwargs):
        kwargs = clean(kwargs)
        kwargs.update(model=MODEL, max_output_tokens=MAX_OUTPUT,
                      reasoning={"effort": "medium"}, store=True, service_tier="default")
        for key in ("temperature", "top_p", "max_tokens", "max_completion_tokens"):
            kwargs.pop(key, None)
        rid = self.budget.reserve(kwargs, task=self.task)
        try:
            response = await self.client.responses.create(**kwargs)
        except BaseException:
            self.budget.finish(rid, status="provider_request_failed")
            raise
        self.budget.finish(rid, response.usage.model_dump() if response.usage else None,
                           response_model=response.model)
        return response

    async def close(self):
        await self.client.close()
