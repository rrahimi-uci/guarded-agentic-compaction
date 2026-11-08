"""Design arithmetic for the expansion-plan evidence synthesis (provider-free, deterministic).

Three tables, all from closed-form binomial arithmetic using the repository's own
Clopper-Pearson helper so the numbers agree with the compiler's gate:

1. **Admission floors**: the smallest number of accepted calibration groups that admits ``k``
   observed violations at alpha = 0.05 under (a) the registered grid (delta = 0.10 split over the
   11 grid thresholds, as the compiler calibrates) and (b) the single pre-registered rule of the
   end-to-end certificates (one-sided 90 percent, m = 1).
2. **Paired-pilot sensitivity**: for ``n`` paired issues, the smallest miss rate of a comparator
   arm that an exact McNemar test detects with 80 percent power when GAC's arm misses nothing
   (every discordant pair then points one way, and significance at 0.05 needs at least six
   discordant pairs).
3. **Forced-run sample for H3**: the number of forced episodes of a retired candidate needed to
   observe at least one violation with 95 percent probability at a true violation rate ``r``.

Outputs ``paper/results/expansion_synthesis/power.json`` and
``paper/iclr/tables/expansion_power.tex`` (not input by the paper).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

from scipy.stats import binom

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "src",):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from guarded_agentic_compaction.grc.calibrate import GRID, clopper_pearson_upper  # noqa: E402

OUT_DIR = ROOT / "paper/results/expansion_synthesis"
TABLE_PATH = ROOT / "paper/iclr/tables/expansion_power.tex"
ALPHA = 0.05
DELTA = 0.10
PAIR_SIZES = (30, 65, 100, 150, 200, 300, 500)
H3_RATES = (0.01, 0.02, 0.05, 0.10)
MIN_DISCORDANT = 6  # exact McNemar: 2 * 0.5**c <= 0.05 iff c >= 6


def admission_floor(k: int, conf: float, limit: int = 20000) -> int | None:
    """Smallest n with clopper_pearson_upper(k, n, conf) <= ALPHA."""
    for n in range(k + 1, limit):
        if clopper_pearson_upper(k, n, conf) <= ALPHA:
            return n
    return None


def floors() -> dict[str, dict[str, int | None]]:
    grid_conf = 1.0 - DELTA / len(GRID)
    return {
        "registered_grid": {str(k): admission_floor(k, grid_conf) for k in range(5)},
        "single_rule_90": {str(k): admission_floor(k, 1.0 - DELTA) for k in range(5)},
        "single_rule_95": {str(k): admission_floor(k, 0.95) for k in range(5)},
    }


def detectable_miss_rate(n: int, power: float = 0.8) -> float:
    """Smallest comparator miss rate pi with P(Binomial(n, pi) >= MIN_DISCORDANT) >= power,
    GAC's arm missing nothing. Bisection on a monotone function; four decimals."""
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if binom.sf(MIN_DISCORDANT - 1, n, mid) >= power:
            hi = mid
        else:
            lo = mid
    return round(hi, 4)


def pilot_sensitivity() -> list[dict[str, Any]]:
    rows = []
    for n in PAIR_SIZES:
        pi = detectable_miss_rate(n)
        rows.append({"pairs": n, "detectable_miss_rate_80pct_power": pi,
                     "expected_misses_at_that_rate": round(n * pi, 1),
                     "power_at_observed_pilot_rate_2_of_65": round(float(binom.sf(MIN_DISCORDANT - 1, n, 2 / 65)), 3)})
    return rows


def h3_forced_runs(prob: float = 0.95) -> dict[str, int]:
    return {str(r): math.ceil(math.log(1 - prob) / math.log(1 - r)) for r in H3_RATES}


def build() -> dict[str, Any]:
    return {
        "schema": "gac-expansion-power-table/v1",
        "alpha": ALPHA, "delta": DELTA, "grid_points": len(GRID),
        "min_discordant_for_significance": MIN_DISCORDANT,
        "admission_floors": floors(),
        "paired_pilot_sensitivity": pilot_sensitivity(),
        "h3_forced_runs_for_one_violation_95pct": h3_forced_runs(),
        "notes": [
            "Floors are accepted-group counts at the gate's threshold; realized coverage below 1.0 needs proportionally more sampled groups.",
            "Pilot sensitivity assumes every miss is in the comparator arm; two-sided misses lower power further.",
            "Forced-run counts are for one candidate at a stated true rate; they do not certify a rate, they detect one.",
        ],
    }


def table(data: dict[str, Any]) -> str:
    fl = data["admission_floors"]
    lines = [r"\begin{tabular}{@{}lrrrrr@{}}", r"\toprule",
             r"Admission rule & $k=0$ & $k=1$ & $k=2$ & $k=3$ & $k=4$ \\", r"\midrule"]
    labels = {"registered_grid": r"Registered grid ($\delta=0.10$ over 11 thresholds)",
              "single_rule_90": r"Single rule, one-sided 90\%",
              "single_rule_95": r"Single rule, one-sided 95\%"}
    for key, label in labels.items():
        lines.append(label + " & " + " & ".join(f"{fl[key][str(k)]:,}" for k in range(5)) + r" \\")
    lines += [r"\midrule", r"Paired pilot (pairs) & " + " & ".join(f"{r['pairs']}" for r in data["paired_pilot_sensitivity"][:5]) + r" \\",
              r"\quad detectable comparator miss rate (80\% power) & "
              + " & ".join(f"{100 * r['detectable_miss_rate_80pct_power']:.1f}\\%" for r in data["paired_pilot_sensitivity"][:5]) + r" \\",
              r"\midrule", r"Forced runs of a retired candidate (one violation, 95\%) & "
              + " & ".join(f"{100 * float(r):g}\\%: {n}" for r, n in data["h3_forced_runs_for_one_violation_95pct"].items()) + r" & -- \\",
              r"\bottomrule", r"\end{tabular}"]
    return "% generated by paper/scripts/expansion_power_table.py; do not edit\n" + "\n".join(lines) + "\n"


def main() -> None:
    data = build()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "power.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    text = table(data)
    TABLE_PATH.write_text(text, encoding="utf-8")
    print(json.dumps({k: data[k] for k in ("admission_floors", "paired_pilot_sensitivity", "h3_forced_runs_for_one_violation_95pct")}, indent=1))
    print(text)


if __name__ == "__main__":
    main()
