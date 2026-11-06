"""Exact planning sensitivities for a focused comparison; not an execution seal."""
import hashlib
import json
import math
from pathlib import Path

from scipy.stats import binom

from matched_compiler_feasibility import ni_max_losses, superiority_power
from audit_bird_denominators import audit_cohort

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper/results/adaptive_comparison_preflight/design_sensitivity.json"


def build():
    rows = []
    # Alternative claim families, not two jointly licensed analyses. Choose
    # one error allocation prospectively; cost endpoints also need allocation.
    for contrasts in (3, 5):
        alpha = .05 / contrasts
        for n in (100, 145, 312, 600, 900, 1200, 1800):
            losses = ni_max_losses(n, margin=.02, error=alpha)
            rows.append({"contrasts": contrasts, "groups": n, "per_contrast_alpha": alpha,
                "six_arm_test_episodes": 6 * n,
                "superiority_power_gain_04_loss_01": superiority_power(n, .04, .01, alpha),
                "superiority_power_gain_03_loss_01": superiority_power(n, .03, .01, alpha),
                "two_point_conservative_ni_max_losses": losses,
                "two_point_conservative_ni_power_at_loss_01": float(binom.cdf(losses, n, .01)),
                "zero_loss_upper_bound": 1 - alpha ** (1 / n)})
    calibration = []
    for candidates in (1, 2):
        k = math.ceil(math.log(.1 / (11 * candidates)) / math.log(.95))
        calibration.append({"candidates": candidates, "thresholds": 11,
            "accepted_zero_error_floor": k, "pool_at_half_coverage_floor": 2*k})
    historical = {}
    for split, suffix in (("dev", ""), ("train", "train/")):
        base = ROOT / f"paper/results/bird/{suffix}"
        audit = audit_cohort(base)
        counts = {"n": audit["scheduled_questions"], "correct": audit["arms"]["compiled"]["correct"]}
        inputs = list(base.glob("schema_first/*/compile.json")) + [base / "preflight.json"]
        inputs += [base / p for p in audit["source_sha256"]]
        historical[split] = {**counts, "error_rate": 1 - counts["correct"] / counts["n"],
            "denominator": "All scheduled questions in historically admitted families; own-arm missing counts as incorrect.",
            "source_hashes": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}}
    return {"schema": "gac-adaptive-design-sensitivity-v1", "provider_calls": 0,
        "status": "PLANNING_ONLY_NO_FINAL_SAMPLE_SIZE_OR_ERROR_ALLOCATION_SELECTED",
        "rows": rows, "calibration": calibration, "historical_compiled_quality": historical,
        "assumptions": ["IID paired question groups and specified discordance rates; not established by source counts.",
            "Superiority is exact favorable two-sided McNemar rejection with Bonferroni planning alpha.",
            "Noninferiority bounds comparator-only-correct probability, conservatively upper-bounding net quality loss.",
            "Two percentage points is a sensitivity margin, not an accepted quality tolerance.",
            "Per-contrast power is not joint-study power. Cost/latency claims require their own allocation and variance pilot.",
            "A five-percent absolute final-error certificate differs from quality noninferiority or replay agreement.",
            "Historical quality is descriptive context, not fresh power data or proof of future achievable risk.",
            "Do not filter future questions by baseline correctness or enlarge calibration after seeing errors."],
        "source_hashes": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (Path(__file__).resolve(), Path(__file__).with_name("matched_compiler_feasibility.py"),
             Path(__file__).with_name("audit_bird_denominators.py"))}}


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(), indent=2, sort_keys=True) + "\n")
    print("Wrote focused design sensitivity; no execution or final design seal.")
