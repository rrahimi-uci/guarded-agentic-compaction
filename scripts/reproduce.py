#!/usr/bin/env python3
"""One command that reproduces every table and figure from a clean checkout.

    python scripts/reproduce.py            # full: fixtures, tests, experiments, report
    python scripts/reproduce.py --quick    # smaller budgets for a smoke run
    python scripts/reproduce.py --skip-experiments   # fixtures, tests and report only

Definition of done (execution-plan §16.4): source, schemas, demo applications, frozen split
manifests, all four experimental conditions, artifact and evidence reports, raw aggregate
results, figure/table scripts, environment lock and the negative results all reproduce from
a clean checkout. This script is that claim, executable.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: Sequence[str], *, label: str) -> float:
    print(f"\n=== {label}\n$ {' '.join(cmd)}", flush=True)
    t = time.time()
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        raise SystemExit(f"{label} failed with exit code {proc.returncode}")
    return time.time() - t


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--skip-tests", action="store_true")
    ap.add_argument("--skip-experiments", action="store_true")
    ap.add_argument("--demos", nargs="*", default=None)
    ap.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="run independent demonstrations in parallel (default: 1)",
    )
    args = ap.parse_args(argv)
    if args.jobs < 1:
        ap.error("--jobs must be positive")

    py = sys.executable
    timings: dict[str, float] = {}

    timings["fixtures"] = run(
        [py, "scripts/generate_synthetic.py", "--episodes", "400", "--seed", "5"],
        label="regenerate the planted synthetic fixture",
    )

    if not args.skip_tests:
        timings["tests"] = run([py, "-m", "pytest", "-q"], label="test suite")

    if not args.skip_experiments:
        demos = args.demos or [
            "support",
            "permissioned_rag",
            "incident_triage",
            "mcp_ops",
            "fulfillment",
        ]
        if args.jobs == 1 or len(demos) == 1:
            cmd = [py, "experiments/run.py", "--out", "experiments/results"]
            if args.quick:
                cmd.append("--quick")
            cmd += ["--demos", *demos]
            timings["experiments"] = run(cmd, label="four scored conditions per demonstration")
        else:
            started = time.time()
            with tempfile.TemporaryDirectory(prefix="agent-compaction-reproduce-") as tmp:
                temp_root = Path(tmp)

                def one(demo: str) -> float:
                    cmd = [
                        py,
                        "experiments/run.py",
                        "--out",
                        str(temp_root / demo),
                        "--demos",
                        demo,
                    ]
                    if args.quick:
                        cmd.append("--quick")
                    return run(cmd, label=f"scored conditions: {demo}")

                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=min(args.jobs, len(demos))
                ) as pool:
                    futures = {pool.submit(one, demo): demo for demo in demos}
                    for future in concurrent.futures.as_completed(futures):
                        future.result()
                _merge_parallel_results(
                    [temp_root / demo for demo in demos],
                    ROOT / "experiments" / "results",
                    demos,
                )
            timings["experiments"] = time.time() - started

    timings["report"] = run(
        [py, "experiments/analysis/report.py"], label="tables and figures -> docs/results.md"
    )
    timings["verify"] = run([py, "scripts/verify_release.py"], label="reproducibility audit")

    print("\n=== timings (seconds)")
    for k, v in timings.items():
        print(f"  {k:14s} {v:8.1f}")
    print("\nresults:  docs/results.md")
    print("raw:      experiments/results/*.json")
    print("figures:  experiments/figures/*.png")
    return 0


def _merge_parallel_results(
    inputs: Sequence[Path], outdir: Path, demos: Sequence[str]
) -> None:
    """Merge isolated per-demo runs after validating their environment identity."""

    payloads = [json.loads((path / "all_results.json").read_text()) for path in inputs]
    manifests = [payload["manifest"] for payload in payloads]
    identity = ("substrate", "python", "platform", "numpy", "scipy", "sklearn", "seed", "quick")
    expected = {key: manifests[0].get(key) for key in identity}
    for manifest in manifests[1:]:
        got = {key: manifest.get(key) for key in identity}
        if got != expected:
            raise SystemExit(f"parallel experiment manifests disagree: {got} != {expected}")

    manifest = dict(manifests[0])
    manifest["demos"] = list(demos)
    manifest["created"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    outdir.mkdir(parents=True, exist_ok=True)
    aggregate: dict[str, Any] = {"manifest": manifest, "demos": {}}
    for path, demo, payload in zip(inputs, demos, payloads):
        if set(payload["demos"]) != {demo}:
            raise SystemExit(f"parallel result {path} did not contain exactly {demo}")
        aggregate["demos"][demo] = payload["demos"][demo]
        shutil.copyfile(path / f"{demo}.json", outdir / f"{demo}.json")
    (outdir / "run_manifest.json").write_text(json.dumps(manifest, indent=2))
    (outdir / "all_results.json").write_text(json.dumps(aggregate, indent=2, default=str))


if __name__ == "__main__":
    raise SystemExit(main())
