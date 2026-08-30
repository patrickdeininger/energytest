"""Graphical abstract for the revised submission.

  python -m harness.scripts.graphical_abstract

MDPI requires at least 560 x 1100 px (height x width); this renders exactly
1100 x 560 and asserts the result.

The July version of this figure claimed "Top 3 on quality are all open-weight"
and that a 4B model "matches or beats frontier quality". Neither survives the
revision: under budget matching Claude-Sonnet-5 ties Gemma-3-4B, and under a
prompt paraphrase the ranking reorders entirely. What did survive every test is
the efficiency result, so that is what this figure leads with, and the quality
claim is stated as parity rather than superiority.

The energy panel reproduces Figure 2, including its measured-versus-estimated
distinction: only two of the eight points are measurements, and a summary figure
that hides that would misrepresent the paper.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

METRICS = Path("harness/runs/primevul_combined/enriched_metrics.csv")
OUT = Path("MDPI_Review_Round1/submission_MDPI/graphical_abstract.png")

# Budget-matched comparison (Section 4.7, Table 11): Gemma-3-4B and Claude-Sonnet-5
# reach the SAME balanced accuracy, which is what makes the cost ratio a
# like-for-like statement rather than a trade-off.
MATCHED_BA = 0.653
GEMMA_USD, CLAUDE_USD = 0.00004, 0.00265
DETECTOR_BA, BEST_LLM_BA = 0.765, 0.711

BLUE, RED, INK, MUTE = "#1f5fa8", "#c1362f", "#1a1a1a", "#5c5c5c"


def build(out: Path = OUT) -> Path:
    df = pd.read_csv(METRICS)
    df["measured"] = df["energy_source"].str.startswith("measured")

    px_w, px_h, dpi = 1100, 560, 100
    fig = plt.figure(figsize=(px_w / dpi, px_h / dpi), dpi=dpi)
    fig.patch.set_facecolor("white")

    fig.text(0.035, 0.945, "Open-weight LLMs own the efficiency frontier",
             fontsize=19, fontweight="bold", color=INK, va="top")
    fig.text(0.035, 0.878,
             "Eight LLMs on function-level vulnerability detection  ·  PrimeVul, N = 1549  "
             "·  cost and energy as first-class axes",
             fontsize=10, color=MUTE, va="top")

    # ---- left: energy Pareto, with provenance encoded ----------------------
    ax = fig.add_axes([0.075, 0.15, 0.38, 0.60])
    for tier, c in (("open", BLUE), ("frontier", RED)):
        s = df[df["tier"] == tier]
        for _, r in s.iterrows():
            ax.scatter(r["energy_j"], r["bal_acc"],
                       marker="o" if r["measured"] else "s",
                       s=64 if r["measured"] else 52,
                       facecolor=c if r["measured"] else "white",
                       edgecolor=c, linewidth=1.5, zorder=3)
    ax.set_xscale("log")
    lo, hi = df["energy_j"].min(), df["energy_j"].max()
    ax.set_xlim(lo / (hi / lo) ** 0.14, hi * (hi / lo) ** 0.55)
    ylo, yhi = ax.get_ylim()
    ax.set_ylim(ylo, yhi + 0.12 * (yhi - ylo))
    for name, dx, dy in (("Gemma-3-4B", 8, 4), ("DeepSeek-V3.2", 8, 4),
                         ("Claude-Sonnet-5", 8, 4)):
        r = df[df["model"] == name].iloc[0]
        ax.annotate(name, (r["energy_j"], r["bal_acc"]), textcoords="offset points",
                    xytext=(dx, dy), fontsize=8.5, ha="left", va="bottom", color=INK)
    ax.axhline(0.5, ls="--", c="grey", lw=1, zorder=1)
    ax.set_xlabel("Energy per task, J (log)", fontsize=9.5)
    ax.set_ylabel("Balanced accuracy", fontsize=9.5)
    ax.tick_params(labelsize=8.5)
    handles = [
        plt.Line2D([], [], marker="s", ls="", mfc="white", mec=BLUE, mew=1.5, ms=7,
                   label="open-weight"),
        plt.Line2D([], [], marker="s", ls="", mfc="white", mec=RED, mew=1.5, ms=7,
                   label="frontier"),
        plt.Line2D([], [], marker="o", ls="", mfc="#444", mec="#444", ms=6,
                   label="measured on-GPU"),
    ]
    ax.legend(handles=handles, frameon=False, fontsize=8, loc="lower right")

    # ---- right: three claims that survived the revision --------------------
    cost_x = CLAUDE_USD / GEMMA_USD
    rows = [
        (f"{cost_x:.0f}×", "cheaper at equal quality",
         f"Gemma-3-4B and Claude-Sonnet-5 both reach {MATCHED_BA:.3f}"),
        ("10–150×", "less energy per task",
         "range spans the frontier active-parameter assumption"),
        (f"{DETECTOR_BA:.3f}", "a 125M fine-tuned detector",
         f"beats all eight LLMs (best {BEST_LLM_BA:.3f}) at negligible cost"),
    ]
    # Right-align the numbers: "10-150x" is far wider than "66x", and left-aligning
    # a ragged column crowds the labels beside the widest entry.
    x_num, x_txt, y = 0.645, 0.665, 0.665
    for big, lead, sub in rows:
        fig.text(x_num, y, big, fontsize=22, fontweight="bold", color=BLUE,
                 va="center", ha="right")
        fig.text(x_txt, y + 0.046, lead, fontsize=11, color=INK, va="center", ha="left")
        fig.text(x_txt, y - 0.048, sub, fontsize=8.5, color=MUTE, va="center", ha="left")
        y -= 0.205

    fig.text(0.515, 0.055,
             "Efficiency holds across three prompts, three sample draws, two budgets,\n"
             "all reasoning modes and three serving providers. Quality does not:\n"
             "three reasonable phrasings give three different winners.",
             fontsize=9, color=INK, va="bottom", ha="left", linespacing=1.55)

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=dpi, facecolor="white")
    plt.close(fig)

    from PIL import Image
    w, h = Image.open(out).size
    assert (w, h) == (px_w, px_h), f"graphical abstract is {w}x{h}, expected {px_w}x{px_h}"
    return out


if __name__ == "__main__":
    p = build()
    print(f"wrote {p} ({p.stat().st_size/1000:.0f} kB)")
