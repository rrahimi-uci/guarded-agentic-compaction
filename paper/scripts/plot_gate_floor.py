#!/usr/bin/env python3
"""Draw the 92-group floor of the exact admission gate (``paper/iclr/figures/gate_floor.pdf``).

The figure explains one arithmetic fact the paper leans on: with the registered budget
``alpha = 0.05``, ``delta = 0.10`` and an ``|Lambda| = 11`` threshold grid, the
zero-violation Clopper--Pearson upper bound

    U(n) = 1 - (delta / |Lambda|) ** (1 / n)

first falls to ``alpha`` at ``n = 91.64`` admitted groups, so ``n >= 92`` is the smallest
pool that can certify anything (``U(92) = 0.0498``, ``U(91) = 0.0503``).  Certifying a
selective coverage ``c`` on a pool of ``|K|`` groups needs ``c * |K| >= 92``, i.e.
``|K| >= ceil(92 / c)``; every calibration pool in the paper is exactly 92 groups, so the
only certifiable coverages there are 0 and 1.  The corrected budget for ``m = 2``
candidates (``gamma = delta / (m |Lambda|)``) is drawn for comparison: at ``n = 92`` it
gives 0.0569 and needs 106 groups.

Every constant is the closed form of ``grc/calibrate.py::clopper_pearson_upper`` with
``k = 0``; the same numbers are retained in
``paper/results/iclr_revision/multiplicity_accounting.json`` (``u_at_92``, ``n_min``).
The script is provider-free and deterministic: it reuses the house palette and the fixed
PDF metadata of ``build_artifacts.py`` and adds no timestamp, so the PDF bytes are stable
across rebuilds.

Usage:
    python paper/scripts/plot_gate_floor.py            # writes paper/iclr/figures/gate_floor.pdf
    python paper/scripts/plot_gate_floor.py --png out.png   # also writes a raster preview
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_artifacts import COLORS, FIG_W, PDF_METADATA, configure_plots  # noqa: E402

OUT = ROOT / "paper" / "iclr" / "figures" / "gate_floor.pdf"

#: Registered admission budget (Table 3 of the paper; ``compiler.config`` of every study).
ALPHA = 0.05
DELTA = 0.10
GRID = 11
#: Coverages annotated on the right panel with their minimum pools (Appendix G).
COVERAGES = (1.0, 0.8, 0.7, 0.5, 0.25)
#: Every calibration pool in the paper.
POOL = 92


def upper(n: float, m: int = 1) -> float:
    """Zero-violation one-sided Clopper--Pearson bound under a budget split over m candidates."""
    return 1.0 - (DELTA / (m * GRID)) ** (1.0 / n)


def crossing(m: int = 1) -> float:
    """Real n at which ``upper(n, m)`` equals ``ALPHA``."""
    return math.log(DELTA / (m * GRID)) / math.log(1.0 - ALPHA)


def min_pool(coverage: float) -> int:
    return math.ceil(POOL / coverage)


def configure_fonts() -> None:
    """House palette and rc from build_artifacts, with a Times-compatible face.

    STIXGeneral ships inside matplotlib, so the figure renders identically on any
    machine; ``newtxtext`` in the manuscript is itself a Times clone, so the labels match
    the body face.  Type-42 embedding (set by ``configure_plots``) keeps the text
    selectable and the file free of Type-3 bitmaps.
    """
    configure_plots()
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["STIXGeneral", "STIX Two Text", "Times New Roman", "Times"],
            "mathtext.fontset": "stix",
            "font.size": 8.5,
            "axes.labelsize": 8.5,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
        }
    )


def floor_panel(ax) -> None:
    n = np.linspace(60, 200, 561)
    n_star = crossing(1)
    n_star_2 = crossing(2)

    # Region no zero-violation pool can certify: left of the crossing.
    ax.axvspan(60, n_star, color=COLORS["track"], alpha=0.55, lw=0, zorder=0)
    ax.axhline(ALPHA, color=COLORS["series2"], lw=1.0, ls="--", zorder=2)
    ax.plot(n, [upper(v, 1) for v in n], color=COLORS["series1"], lw=1.4, zorder=3)
    ax.plot(n, [upper(v, 2) for v in n], color=COLORS["ink2"], lw=1.0, ls=(0, (4, 2)),
            zorder=3)
    for x in (n_star, n_star_2):
        ax.plot([x, x], [0.02, ALPHA], color=COLORS["muted"], lw=0.6, ls=":", zorder=1)

    # Curves are labelled in place (the budget gamma = delta/(m|Lambda|) is in the
    # caption); a legend box collided with the annotations.
    ax.text(150, upper(150) - 0.004, r"$m=1$", fontsize=7,
            color=COLORS["series1"], ha="left", va="top")
    ax.text(140, upper(140, 2) + 0.002, r"$m=2$", fontsize=7,
            color=COLORS["ink2"], ha="left", va="bottom")

    # The two integers either side of the crossing, and the corrected bound at 92.
    u91, u92, u92_2 = upper(91), upper(92), upper(92, 2)
    ax.scatter([91], [u91], s=22, facecolor="white", edgecolor=COLORS["series2"],
               linewidth=1.0, zorder=5)
    ax.scatter([92], [u92], s=22, color=COLORS["series1"], zorder=5)
    ax.scatter([92], [u92_2], s=18, marker="s", color=COLORS["ink2"], zorder=5)
    arrow = dict(arrowstyle="-", color=COLORS["muted"], lw=0.5, shrinkA=0, shrinkB=2)
    ax.annotate(f"$m=2$ at $n=92$: $U={u92_2:.4f}$, needs $n\\geq{math.ceil(n_star_2)}$",
                xy=(92, u92_2), xytext=(104, 0.0762), fontsize=7, color=COLORS["ink2"],
                ha="left", va="center", arrowprops=arrow)
    ax.annotate(f"$n=91$: $U={u91:.4f}>\\alpha$", xy=(91, u91), xytext=(104, 0.0693),
                fontsize=7, color=COLORS["series2"], ha="left", va="center", arrowprops=arrow)
    ax.annotate(f"$n=92$: $U={u92:.4f}\\leq\\alpha$", xy=(92, u92), xytext=(104, 0.0628),
                fontsize=7, color=COLORS["series1"], ha="left", va="center", arrowprops=arrow)
    ax.text(62, 0.0475, "no zero-violation\npool certifies", fontsize=7,
            color=COLORS["ink2"], ha="left", va="top")
    ax.text(199, ALPHA + 0.0008, r"$\alpha=0.05$", fontsize=7, color=COLORS["series2"],
            ha="right", va="bottom")
    ax.text(n_star + 1.5, 0.0207, f"$n^*={n_star:.2f}$", fontsize=7, color=COLORS["ink2"],
            ha="left", va="bottom")

    ax.set_xlim(60, 200)
    ax.set_ylim(0.02, 0.08)
    ax.set_xticks([60, 92, 106, 140, 170, 200])
    ax.set_yticks([0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08])
    ax.set_xlabel(r"Admitted zero-violation groups $n_\eta$")
    ax.set_ylabel(r"$U=1-\gamma^{1/n_\eta}$")
    ax.yaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)


def pool_panel(ax) -> None:
    c = np.linspace(0.22, 1.0, 781)
    ax.plot(c, [min_pool(v) for v in c], color=COLORS["series1"], lw=1.4, zorder=3,
            drawstyle="steps-post")
    ax.axhline(POOL, color=COLORS["series2"], lw=1.0, ls="--", zorder=2)
    ax.axhspan(0, POOL, color=COLORS["track"], alpha=0.55, lw=0, zorder=0)

    xs = list(COVERAGES)
    ys = [min_pool(v) for v in xs]
    ax.scatter(xs, ys, s=22, color=COLORS["series1"], zorder=5)
    # Label positions are staggered by hand so no two labels share a band.
    offsets = {1.0: (-0.005, 8, "right"), 0.8: (0.02, 13, "left"),
               0.7: (0.02, 18, "left"), 0.5: (0.03, 26, "left"), 0.25: (0.03, 4, "left")}
    for x, y in zip(xs, ys):
        dx, dy, ha = offsets[x]
        ax.annotate(f"$c={x:g}$: {y}", xy=(x, y), xytext=(x + dx, y + dy), fontsize=7,
                    color=COLORS["ink"], ha=ha, va="bottom")
    # The paper's pools: |K| = 92 in every study, i.e. the point (1.0, 92).
    ax.scatter([1.0], [POOL], s=60, facecolor="none", edgecolor=COLORS["series2"],
               linewidth=1.0, zorder=6)
    ax.text(0.215, POOL + 7, r"every pool in this paper: $|\mathcal{K}|=92$",
            fontsize=7, color=COLORS["series2"], ha="left", va="bottom")
    ax.text(0.215, 12, r"at $|\mathcal{K}|=92$ the certifiable" "\n" r"coverage set is $\{0,1\}$",
            fontsize=7, color=COLORS["ink2"], ha="left", va="bottom")

    ax.set_xlim(0.2, 1.02)
    ax.set_ylim(0, 420)
    ax.set_xticks([0.25, 0.5, 0.7, 0.8, 1.0])
    ax.set_yticks([0, 92, 200, 300, 400])
    ax.set_xlabel(r"Selective coverage $c=n_\eta/|\mathcal{K}|$ to certify")
    ax.set_ylabel(r"Minimum pool $\lceil 92/c\rceil$")
    ax.yaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)


def build(out: Path, png: Path | None = None) -> None:
    configure_fonts()
    fig, (left, right) = plt.subplots(1, 2, figsize=(FIG_W, 2.3))
    floor_panel(left)
    pool_panel(right)
    for ax, tag in ((left, "(a)"), (right, "(b)")):
        ax.text(-0.19, 1.02, tag, transform=ax.transAxes, fontsize=8.5, fontweight="bold",
                color=COLORS["ink"], ha="left", va="bottom")
    fig.tight_layout(pad=0.3, w_pad=1.8)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", pad_inches=0.02, metadata=PDF_METADATA)
    if png is not None:
        fig.savefig(png, dpi=300, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--png", type=Path, default=None, help="optional raster preview")
    args = parser.parse_args(argv)
    build(args.out, args.png)
    print(f"n* = {crossing(1):.2f} (m=1), {crossing(2):.2f} (m=2); U(91) = {upper(91):.4f}, "
          f"U(92) = {upper(92):.4f}, U_2(92) = {upper(92, 2):.4f}; pools "
          + ", ".join(f"c={c:g}: {min_pool(c)}" for c in COVERAGES))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
