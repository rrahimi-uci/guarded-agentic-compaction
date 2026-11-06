"""Pinned upstream Agent JIT generation in its own dependency environment.

Input/output JSON files contain public benchmark text/programs, never credentials.
Generated programs are not executed in this process.
"""
import argparse
import ast
import asyncio
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys

from adaptive_campaign_budget import BudgetClient, Ledger, MODEL
from probe_agent_jit_sql import PIN


async def generate(request, checkout):
    if subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip() != PIN:
        raise ValueError("wrong upstream commit")
    if subprocess.check_output(["git", "-C", str(checkout), "diff", "--name-only", "HEAD"], text=True).strip():
        raise ValueError("upstream code modified")
    sys.path.insert(0, str(checkout))
    os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"]
    from blastai.agents.codegen import CodeGenerator
    from blastai.agents.models import Agent
    from agent_jit.sampling import collect_candidates
    from agent_jit.adapters.planner import select_candidate
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    client = BudgetClient(Ledger(Path(request["ledger"])), stage=request["stage"], task=request["task_id"], arm="agent_jit")

    class Model:
        model = MODEL
        provider = "openai"
        temperature = None
        max_completion_tokens = 4096
        def get_client(self):
            return client
        async def ainvoke(self, *args, **kwargs):
            raise RuntimeError("stream failed; unbudgeted fallback forbidden")

    agent = Agent.from_dict({"description": request["instructions"], "tools": request["registry"]["tools"]})
    generator = CodeGenerator(agent, llm=Model(), state_aware=True, max_iterations=1,
                              num_candidates=1, timezone="UTC")
    semaphore = asyncio.Semaphore(4)
    async def one():
        async with semaphore:
            return await generator.generate_candidate(request["task"], history=[], initial_state=request["state"])
    try:
        candidates, valid, met = await collect_candidates(one, request["candidates"], target="sampled")
        selected = select_candidate(valid, "best") if valid else None
        runtime_tree = ast.parse((checkout / "blastai/agents/coderun.py").read_text())
        runtime_func = next(n for n in ast.walk(runtime_tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == "ai_eval")
        system_call = next(n for n in ast.walk(runtime_func) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "SystemMessage")
        runtime_prompt = ast.literal_eval(next(k.value for k in system_call.keywords if k.arg == "content"))
        return {"upstream_commit": PIN, "target_met": met, "candidates": [
            {"exception": type(c).__name__} if isinstance(c, BaseException) else asdict(c) if c else None
            for c in candidates], "selected_index": next((i for i, c in enumerate(candidates) if c is selected), None) if selected is not None else None,
            "selection": "minimum upstream estimated cost; first candidate breaks ties",
            "candidate_target": "sampled", "model": MODEL, "runtime_system_prompt": runtime_prompt}
    finally:
        await client.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("request", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("checkout", type=Path)
    args = p.parse_args()
    result = asyncio.run(generate(json.loads(args.request.read_text()), args.checkout.resolve()))
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
