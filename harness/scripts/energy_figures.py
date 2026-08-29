"""Energy figures with explicit provenance and uncertainty (Figures 2 and 3).

  python -m harness.scripts.energy_figures

Reviewers 1, 2 (#3, #7) and 3 (#2) all asked for the same thing: that measured and
estimated energy be distinguishable at a glance, and that estimated values carry
an uncertainty range rather than being drawn as points. The original Figure 2
encoded provenance only in a caption, which invited exactly the misreading they
warned about.

Two changes here:

  Figure 2  measured points are filled circles with a solid edge; estimated points
            are open squares, and each carries a horizontal bar spanning the range
            the value takes as the assumed active-parameter count is swept. Only
            two of eight points are measured, and the figure now says so visually.

  Figure 3  the same data as a sensitivity sweep: balanced accuracy against energy
            with the frontier active-parameter assumption varied from 25B to 400B,
            showing the open/frontier separation survives the whole range.

The estimator is E ~ 2 * N_active * T * epsilon, linear in the assumed active
parameter count, so sweeping that assumption scales the frontier estimates
proportionally. Open-weight active parameter counts are published, so their
estimates move only with the far smaller uncertainty in epsilon, which we hold
fixed and note in the caption.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

METRICS = "harness/runs/primevul_combined/enriched_metrics.csv"
FIGDIR = Path("figures")

# Assumed active parameters for the frontier models in the headline estimate, and
# the range we sweep. 100B is the paper's bounded assumption; the sweep brackets
# plausible sparse and dense frontier configurations.
FRONTIER_ASSUMED_B = 100.0
FRONTIER_LOW_B, FRONTIER_HIGH_B = 25.0, 400.0

OPEN_C = "#1f5fa8"
FRONT_C = "#c1362f"


def load():
    import pandas as pd

    df = pd.read_csv(METRICS)
    df["measured"] = df["energy_source"].str.startswith("measured")
    return df


def energy_range(row):
    """(lo, hi) energy for a model. Measured values get the point itself; frontier
    estimates get the active-parameter sweep; open estimates keep their published
    active-parameter count and so are not swept."""
    e = row["energy_j"]
    if row["measured"]:
        return e, e
    if row["tier"] == "frontier":
        return (e * FRONTIER_LOW_B / FRONTIER_ASSUMED_B,
                e * FRONTIER_HIGH_B / FRONTIER_ASSUMED_B)
    return e, e


def fig2(df):
    import math

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    for _, r in df.iterrows():
        c = OPEN_C if r["tier"] == "open" else FRONT_C
        lo, hi = energy_range(r)
        if not r["measured"]:
            ax.plot([lo, hi], [r["bal_acc"]] * 2, color=c, lw=1.1, alpha=0.55,
                    solid_capstyle="butt", zorder=1)
            ax.plot([lo, hi], [r["bal_acc"]] * 2, "|", color=c, ms=5, alpha=0.7, zorder=1)
        ax.scatter(r["energy_j"], r["bal_acc"],
                   marker="o" if r["measured"] else "s",
                   s=68 if r["measured"] else 52,
                   facecolor=c if r["measured"] else "white",
                   edgecolor=c, linewidth=1.6, zorder=3)

    ax.set_xscale("log")
    ax.set_xlabel("Energy per task (J, log scale)")
    ax.set_ylabel("Balanced accuracy")
    ax.set_ylim(0.47, 0.72)
    # Pad the log x-range so edge labels stay inside the panel.
    xs = df["energy_j"]
    ax.set_xlim(10 ** (math.log10(xs.min()) - 0.45), 10 ** (math.log10(xs.max()) + 0.55))

    # The three frontier models sit within 0.01 balanced accuracy of each other and
    # their labels collide; step through vertical slots until one is free of every
    # label already placed nearby on the same side.
    placed: list[tuple[float, float, float]] = []

    def free_slot(x, y):
        # Two labels only collide if they are close in BOTH axes; points far apart
        # vertically never collide however near they are in x.
        for dy in (9, -14, 20, -25, 31, -36):
            if all(abs(math.log10(x) - math.log10(px)) > 0.16
                   or abs(y - py) > 0.020
                   or abs(dy - pdy) > 9
                   for px, py, pdy in placed):
                placed.append((x, y, dy))
                return dy
        placed.append((x, y, 9))
        return 9

    for _, r in df.sort_values("energy_j").iterrows():
        c = OPEN_C if r["tier"] == "open" else FRONT_C
        dy = free_slot(r["energy_j"], r["bal_acc"])
        ax.annotate(r["model"], (r["energy_j"], r["bal_acc"]),
                    textcoords="offset points", xytext=(0, dy),
                    ha="center", fontsize=7.6, color="#222")

    ax.axhline(0.5, ls="--", lw=0.9, color="#888", zorder=0)
    # Left-aligned: the legend occupies the lower right.
    ax.annotate("trivial baseline (0.5)", (ax.get_xlim()[0], 0.5),
                textcoords="offset points", xytext=(6, 4), ha="left",
                fontsize=7.2, color="#666")

    handles = [
        plt.Line2D([], [], marker="o", ls="", mfc="#444", mec="#444", ms=7,
                   label="measured on-GPU (NVML)"),
        plt.Line2D([], [], marker="s", ls="", mfc="white", mec="#444", mew=1.6, ms=7,
                   label="FLOP-estimated"),
        plt.Line2D([], [], color="#444", lw=1.1, alpha=0.6,
                   label="range over 25B--400B active params"),
        plt.Line2D([], [], marker="s", ls="", mfc="white", mec=OPEN_C, mew=1.6, ms=7,
                   label="open-weight"),
        plt.Line2D([], [], marker="s", ls="", mfc="white", mec=FRONT_C, mew=1.6, ms=7,
                   label="frontier"),
    ]
    ax.legend(handles=handles, fontsize=7.2, loc="lower right", framealpha=0.95)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(FIGDIR / f"pareto_balacc_energy.{ext}", dpi=200)
    plt.close(fig)
    print("wrote figures/pareto_balacc_energy.{pdf,png}")


def fig3(df):
    """Sensitivity band: how the frontier estimates move as the assumption sweeps."""
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    # Ascending energy, drawn bottom-up, so the cheapest model reads at the top.
    ordered = df.sort_values("energy_j", ascending=False).reset_index(drop=True)
    ypos = {r["model"]: i for i, r in ordered.iterrows()}
    open_max = df[df["tier"] == "open"]["energy_j"].max()

    for _, r in ordered.iterrows():
        y = ypos[r["model"]]
        if r["tier"] == "frontier":
            lo, hi = energy_range(r)
            ax.barh(y, hi - lo, left=lo, height=0.5,
                    color=FRONT_C, alpha=0.28, edgecolor=FRONT_C, linewidth=1.0, zorder=2)
            ax.plot([r["energy_j"]], [y], marker="D", color=FRONT_C, ms=6, zorder=4)
        else:
            ax.plot([r["energy_j"]], [y], marker="o" if r["measured"] else "s",
                    ms=7, zorder=4, ls="",
                    mfc=OPEN_C if r["measured"] else "white", mec=OPEN_C, mew=1.6)

    ax.set_yticks(range(len(ordered)))
    ax.set_yticklabels(ordered["model"])
    ax.set_ylim(-0.8, len(ordered) - 0.2)
    ax.axvline(open_max, ls=":", lw=1.1, color="#555", zorder=1)
    # Bottom of the panel: the legend occupies the top right.
    ax.annotate("highest open-weight energy", (open_max, -0.55),
                textcoords="offset points", xytext=(5, 0), fontsize=7.2,
                color="#555", va="center")
    ax.set_xscale("log")
    ax.set_xlabel("Energy per task (J, log scale)")
    handles = [
        plt.Line2D([], [], marker="D", ls="", color=FRONT_C, ms=6,
                   label="frontier estimate at 100B assumed active params"),
        plt.Line2D([], [], color=FRONT_C, lw=7, alpha=0.28,
                   label="frontier range, 25B--400B"),
        plt.Line2D([], [], marker="o", ls="", mfc=OPEN_C, mec=OPEN_C, ms=7,
                   label="open, measured on-GPU"),
        plt.Line2D([], [], marker="s", ls="", mfc="white", mec=OPEN_C, mew=1.6, ms=7,
                   label="open, FLOP-estimated"),
    ]
    ax.legend(handles=handles, fontsize=7.2, loc="upper right", framealpha=0.95)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(FIGDIR / f"energy_sensitivity.{ext}", dpi=200)
    plt.close(fig)
    print("wrote figures/energy_sensitivity.{pdf,png}")


def main() -> int:
    FIGDIR.mkdir(exist_ok=True)
    df = load().sort_values("bal_acc", ascending=False)
    print(df[["model", "tier", "bal_acc", "energy_j", "energy_source"]].to_string(index=False))
    ranges = {r["model"]: energy_range(r) for _, r in df.iterrows()}
    print("\nfrontier sensitivity ranges (J):")
    for _, r in df[df["tier"] == "frontier"].iterrows():
        lo, hi = ranges[r["model"]]
        print(f"  {r['model']:18s} {lo:8.0f} - {hi:8.0f}   (point {r['energy_j']:.0f})")
    gemma = df[df["model"] == "Gemma-3-4B"]["energy_j"].iloc[0]
    print("\nratio of frontier energy to Gemma-3-4B:")
    for _, r in df[df["tier"] == "frontier"].iterrows():
        lo, hi = ranges[r["model"]]
        print(f"  {r['model']:18s} {lo/gemma:6.1f}x - {hi/gemma:6.1f}x "
              f"(point {r['energy_j']/gemma:.1f}x)")
    fig2(df)
    fig3(df)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
