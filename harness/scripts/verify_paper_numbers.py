"""Cross-check numbers in main.tex against the artifacts they came from.

  python -m harness.scripts.verify_paper_numbers

Every table in the paper was transcribed by hand from script output, which is
where transcription errors live and where a reviewer will find them. This
re-derives the load-bearing figures from the saved artifacts and compares them
with what the manuscript actually says, so a stale number surfaces here rather
than in review.

It checks values, not prose. A failure means the paper and the data disagree;
which of the two is wrong is for a human to decide.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

TEX = Path("main.tex")
FAILURES: list[str] = []
CHECKED = 0


def claim(label: str, expected: float, pattern: str, tol: float = 0.0006) -> None:
    """Assert the manuscript contains `pattern` with a number matching `expected`."""
    global CHECKED
    CHECKED += 1
    text = TEX.read_text(encoding="utf-8")
    m = re.search(pattern, text)
    if not m:
        FAILURES.append(f"{label}: pattern not found in main.tex -> {pattern!r}")
        return
    got = float(m.group(1))
    if abs(got - expected) > tol:
        FAILURES.append(
            f"{label}: paper says {got}, artifacts say {expected:.4f} "
            f"(difference {abs(got-expected):.4f})")


def main() -> int:
    # --- concurrency sweep -------------------------------------------------
    sweeps = {}
    for tag in ("gemma", "qwen", "llama"):
        p = Path(f"harness/runs/concurrency_sweep/{tag}.json")
        if p.exists():
            sweeps[tag] = {r["concurrency"]: r for r in json.loads(p.read_text())}

    if "gemma" in sweeps:
        claim("Gemma c=64 energy", round(sweeps["gemma"][64]["active_j_per_task"], 1),
              r"Gemma-3-4B \(dense\) & 64 & 84\.4 & 12\.2 & 5\.1 & \\textbf\{([0-9.]+)\}", 0.05)
        claim("Gemma c=64 throughput", round(sweeps["gemma"][64]["throughput_tasks_per_s"], 1),
              r"Gemma-3-4B & -- & 3\.03 & 20\.4 & 48\.6 & \\textbf\{([0-9.]+)\}", 0.05)
    if "llama" in sweeps:
        claim("Llama c=1 energy", round(sweeps["llama"][1]["active_j_per_task"], 1),
              r"Llama-3\.3-70B \(dense, FP8\) & 944 & ([0-9.]+)", 0.05)
        claim("Llama c=64 energy", round(sweeps["llama"][64]["active_j_per_task"], 1),
              r"Llama-3\.3-70B \(dense, FP8\) & 944 & 739\.9 & 149\.8 & 88\.9 & ([0-9.]+)", 0.05)
        claim("Llama break-even throughput", round(sweeps["llama"][64]["throughput_tasks_per_s"], 1),
              r"Llama-3\.3-70B & ([0-9.]+) & 0\.0000815", 0.05)
    if "qwen" in sweeps:
        claim("Qwen c=64 energy", round(sweeps["qwen"][64]["active_j_per_task"], 1),
              r"Qwen3-Coder-30B \(MoE\) & 40 & 84\.0 & 24\.1 & 11\.0 & ([0-9.]+)", 0.05)

    # --- trained detector --------------------------------------------------
    p = Path("harness/runs/primevul_trained_baseline/scores.json")
    if p.exists():
        s = json.loads(p.read_text())
        claim("detector bal_acc", round(s["bal_acc"], 3),
              r"\\textbf\{CodeBERT-PrimeVul \(learned, in-distribution\)\} & "
              r"\\textbf\{validation-tuned\} & \\textbf\{([0-9.]+)\}")
        claim("detector MCC", round(s["mcc"], 3),
              r"\\textbf\{validation-tuned\} & \\textbf\{0\.765\} & \\textbf\{([0-9.]+)\}")
        claim("detector precision@1:44", round(s["precision_at_1to44"] * 100, 2),
              r"0\.709 & 0\.821 & \\textbf\{([0-9.]+)\}", 0.02)
        claim("detector ROC-AUC (confidence table)", round(s["roc_auc"], 3),
              r"CodeBERT-PrimeVul \(125M, fine-tuned\)\}.*?\\textbf\{([0-9.]+)\}\}")

    # --- confidence analysis ----------------------------------------------
    p = Path("harness/runs/confidence_analysis.json")
    if p.exists():
        c = json.loads(p.read_text())
        cl = c.get("claude-sonnet-5", {})
        if cl.get("usable"):
            claim("Claude confidence AUC", round(cl["auc_literal"], 3),
                  r"Claude-Sonnet-5 & 0\.997 & 34 & 0\.26 & 0\.63 & literal & "
                  r"\\textbf\{([0-9.]+)\}")
            claim("Claude confidence coverage", round(cl["coverage"], 3),
                  r"Claude-Sonnet-5 & ([0-9.]+) & 34 & 0\.26")

    # --- price dispersion --------------------------------------------------
    p = Path("harness/runs/price_snapshot.json")
    if p.exists():
        snap = json.loads(p.read_text())["models"]
        ds = snap.get("deepseek-v3.2", {})
        if ds.get("spread_in"):
            claim("DeepSeek provider spread", round(ds["spread_in"], 1),
                  r"DeepSeek-V3\.2 & open & 14 & 0\.209--3\.000 & ([0-9.]+)\$\\times\$", 0.05)
            claim("DeepSeek provider count", float(ds["n_providers"]),
                  r"DeepSeek-V3\.2 & open & ([0-9]+) & 0\.209", 0.5)

    # --- report ------------------------------------------------------------
    print(f"checked {CHECKED} numeric claims against saved artifacts")
    if FAILURES:
        print(f"\n{len(FAILURES)} MISMATCH(ES):\n")
        for f in FAILURES:
            print("  " + f)
        return 1
    print("all checked claims agree with the artifacts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
