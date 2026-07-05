"""Static-analysis baseline: Flawfinder on the exact 1549 evaluated functions.

  python -m harness.scripts.flawfinder_baseline

Gives the non-LLM reference point the review panel asked for ("is 0.67 balanced
accuracy good?"). Flawfinder is a lexical C/C++ scanner; we treat a function as
predicted-vulnerable if it raises at least one hit at or above a risk-level
threshold, and sweep the threshold. Scored with the same metrics as the LLMs.
"""

from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
from pathlib import Path

from harness.analysis.stats import balanced_accuracy, mcc, precision_at_prevalence

COMBINED = "harness/runs/primevul_combined/results.jsonl"
PRIMEVUL = "harness/data/primevul/primevul_test.jsonl"
PREVALENCE = 549 / 24788
WORKDIR = Path(__file__).resolve().parents[2] / "harness" / "runs" / "flawfinder_baseline"


def task_labels() -> dict:
    """The 1549 evaluated task_ids -> label (from any model's rows; all share the set)."""
    out = {}
    for line in open(COMBINED, encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        out[str(r["task_id"])] = r["label"]
    return out


def func_source(task_ids: set) -> dict:
    """idx -> func text for the needed task_ids (idx is the id_field)."""
    src = {}
    for line in open(PRIMEVUL, encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        tid = str(r["idx"])
        if tid in task_ids:
            src[tid] = r["func"]
    return src


def run_flawfinder(src_dir: Path) -> dict:
    """Return {task_id: max risk level found (0 if none)} over all .c files in src_dir."""
    proc = subprocess.run(
        [sys.executable, "-m", "flawfinder", "--csv", "--minlevel=0", str(src_dir)],
        capture_output=True, text=True,
    )
    hits: dict = {}
    reader = csv.DictReader(io.StringIO(proc.stdout))  # StringIO: handle quoted newlines in Context
    for row in reader:
        lvl_str = (row.get("Level") or "").strip()
        fname = row.get("File") or ""
        if not lvl_str.isdigit() or not fname:
            continue
        tid = Path(fname).stem.replace("func_", "")
        hits[tid] = max(hits.get(tid, 0), int(lvl_str))
    return hits


def score(labels: dict, hits: dict, threshold: int) -> dict:
    tp = fp = fn = tn = 0
    for tid, lab in labels.items():
        pred = 1 if hits.get(tid, 0) >= threshold else 0
        if lab == 1 and pred == 1: tp += 1
        elif lab == 0 and pred == 1: fp += 1
        elif lab == 1 and pred == 0: fn += 1
        else: tn += 1
    tpr = tp / (tp + fn) if (tp + fn) else 0.0
    tnr = tn / (tn + fp) if (tn + fp) else 0.0
    n = tp + fp + fn + tn
    f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0
    return {
        "threshold": threshold, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "bal_acc": balanced_accuracy(tp, fp, fn, tn), "mcc": mcc(tp, fp, fn, tn),
        "f1": f1, "accuracy": (tp + tn) / n if n else 0.0,
        "recall": tpr, "specificity": tnr,
        "precision_at_1to44": precision_at_prevalence(tpr, tnr, PREVALENCE),
    }


def main() -> int:
    labels = task_labels()
    print(f"Evaluated tasks: {len(labels)} ({sum(labels.values())} vulnerable)")
    src = func_source(set(labels))
    print(f"Recovered source for {len(src)} functions")

    src_dir = WORKDIR / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    for tid, code in src.items():
        (src_dir / f"func_{tid}.c").write_text(code, encoding="utf-8", errors="replace")

    print("Running flawfinder ...")
    hits = run_flawfinder(src_dir)
    n_flagged = sum(1 for t in labels if hits.get(t, 0) >= 1)
    print(f"Flawfinder raised >=1 hit on {n_flagged}/{len(labels)} functions\n")

    rows = [score(labels, hits, t) for t in (1, 2, 3, 4, 5)]
    print(f"{'thr':>3} {'bal_acc':>8} {'mcc':>7} {'recall':>7} {'spec':>7} {'prec@1:44':>10}")
    for r in rows:
        print(f"{r['threshold']:>3} {r['bal_acc']:>8.3f} {r['mcc']:>7.3f} "
              f"{r['recall']:>7.3f} {r['specificity']:>7.3f} {r['precision_at_1to44']*100:>9.1f}%")

    (WORKDIR / "flawfinder_scores.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"\nWrote {WORKDIR / 'flawfinder_scores.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
