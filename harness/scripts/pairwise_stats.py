"""Complete pairwise statistics for the supplementary material (Appendix A).

  python -m harness.scripts.pairwise_stats [--run DIR] [--latex OUT.tex]

Reviewer 2 (#9) asked for the pairwise effects, confidence intervals, raw and
corrected p-values, the composition of the common parsed sets, and the exact
hypothesis family each correction is taken over. The main text reports only the
comparisons that carry an argument; this emits all of them, so the corrections
can be checked rather than trusted.

Three families are reported, and which one a p-value belongs to matters because
Holm's adjustment depends on the family size:

  PRIMARY   the 9 comparisons between the three top open models and the three
            frontier models -- the family the paper's central quality claim
            is made in;
  STRICT    all 15 open-vs-frontier comparisons, as a robustness check that the
            conclusion does not depend on how the family was drawn;
  ALL       every one of the 28 model pairs, reported without a corrected
            p-value, since no claim is made over that family.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from harness.analysis.stats import (holm_bonferroni,
                                    paired_bootstrap_bal_acc_diff)

SEED = 12345
N_BOOT = 20000
DEFAULT_RUN = Path("harness/runs/primevul_combined")

TIER = {
    "deepseek-v3.2": "open", "gemma-3-4b": "open", "glm-5": "open",
    "llama-3.3-70b": "open", "qwen3-coder-30b": "open",
    "claude-sonnet-5": "frontier", "gpt-5.1": "frontier", "gemini-3.1-pro": "frontier",
}
DISPLAY = {
    "deepseek-v3.2": "DeepSeek-V3.2", "gemma-3-4b": "Gemma-3-4B", "glm-5": "GLM-5",
    "gemini-3.1-pro": "Gemini-3.1-Pro", "gpt-5.1": "GPT-5.1",
    "claude-sonnet-5": "Claude-Sonnet-5", "llama-3.3-70b": "Llama-3.3-70B",
    "qwen3-coder-30b": "Qwen3-Coder-30B",
}
# The three highest-scoring open models; the primary family is these against the frontier.
TOP_OPEN = ["deepseek-v3.2", "gemma-3-4b", "glm-5"]
FRONTIER = ["gemini-3.1-pro", "gpt-5.1", "claude-sonnet-5"]


def load(run_dir: Path) -> dict:
    per = defaultdict(dict)
    for line in (run_dir / "results.jsonl").open(encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            per[r["model_id"]][str(r["task_id"])] = r
    return per


def common_set(per: dict, a: str, b: str):
    """Tasks BOTH models parsed. Parse failures are dropped rather than scored as
    'safe', which would otherwise credit a failing model with specificity."""
    ids = sorted(t for t in per[a]
                 if t in per[b] and per[a][t].get("parsed_ok") and per[b][t].get("parsed_ok"))
    labels = [per[a][t]["label"] for t in ids]
    pa = [per[a][t]["prediction"] for t in ids]
    pb = [per[b][t]["prediction"] for t in ids]
    return ids, labels, pa, pb


def compare(per: dict, a: str, b: str) -> dict:
    ids, labels, pa, pb = common_set(per, a, b)
    r = paired_bootstrap_bal_acc_diff(labels, pa, pb, n_boot=N_BOOT, seed=SEED)
    return {
        "a": DISPLAY.get(a, a), "b": DISPLAY.get(b, b),
        "a_id": a, "b_id": b,
        "tier_a": TIER.get(a), "tier_b": TIER.get(b),
        "n_common": len(ids),
        "n_pos": sum(labels), "n_neg": len(labels) - sum(labels),
        "n_dropped_a": len(per[a]) - len(ids), "n_dropped_b": len(per[b]) - len(ids),
        "delta": r["delta"], "ci_lo": r["ci_lo"], "ci_hi": r["ci_hi"],
        "p_raw": r["p_two_sided"],
    }


def add_holm(rows: list, key: str) -> list:
    for row, adj in zip(rows, holm_bonferroni([r["p_raw"] for r in rows])):
        row[key] = adj
    return rows


def fmt_p(p: float) -> str:
    if p < 1.0 / N_BOOT:
        return f"$<${1.0/N_BOOT:g}"
    return f"{p:.4f}" if p >= 1e-4 else f"{p:.1e}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=str(DEFAULT_RUN))
    ap.add_argument("--json", default="harness/runs/primevul_combined/pairwise_stats.json")
    ap.add_argument("--latex", default=None)
    args = ap.parse_args()

    per = load(Path(args.run))
    models = [m for m in per if m in TIER]
    print(f"{len(models)} models; bootstrap {N_BOOT} resamples, seed {SEED}\n")

    primary = add_holm([compare(per, o, f) for o in TOP_OPEN for f in FRONTIER], "p_holm")
    strict = add_holm([compare(per, o, f)
                       for o in [m for m in models if TIER[m] == "open"]
                       for f in FRONTIER], "p_holm")
    every = [compare(per, a, b) for a, b in combinations(sorted(models), 2)]

    def show(title, rows, holm=True):
        print(title)
        head = f"{'A':17s} {'B':17s} {'n':>5s} {'delta':>8s} {'95% CI':>18s} {'p_raw':>10s}"
        if holm:
            head += f" {'p_Holm':>10s}"
        print(head)
        print("-" * len(head))
        for r in sorted(rows, key=lambda x: x["p_raw"]):
            line = (f"{r['a']:17s} {r['b']:17s} {r['n_common']:5d} {r['delta']:+8.4f} "
                    f"[{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] {r['p_raw']:10.5f}")
            if holm:
                line += f" {r['p_holm']:10.5f}"
            print(line)
        print()

    show(f"PRIMARY family ({len(primary)} comparisons: 3 top open x 3 frontier)", primary)
    show(f"STRICT family ({len(strict)} comparisons: all open x all frontier)", strict)
    show(f"ALL pairs ({len(every)}), uncorrected", every, holm=False)

    out = {"seed": SEED, "n_boot": N_BOOT, "run": args.run,
           "families": {"primary": primary, "strict": strict, "all_pairs": every}}
    Path(args.json).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {args.json}")

    if args.latex:
        lines = [
            r"\begin{tabular}{llrrrr}", r"\toprule",
            r"\textbf{Model A} & \textbf{Model B} & \textbf{$n$} & "
            r"$\bm{\Delta}$ \textbf{bal.\ acc.} & \textbf{95\% CI} & "
            r"\textbf{Holm $p$}\\", r"\midrule",
        ]
        for r in sorted(primary, key=lambda x: x["p_holm"]):
            lines.append(f"{r['a']} & {r['b']} & {r['n_common']} & ${r['delta']:+.4f}$ & "
                         f"$[{r['ci_lo']:+.3f}, {r['ci_hi']:+.3f}]$ & {fmt_p(r['p_holm'])}\\\\")
        lines += [r"\bottomrule", r"\end{tabular}"]
        Path(args.latex).write_text("\n".join(lines), encoding="utf-8")
        print(f"wrote {args.latex}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
