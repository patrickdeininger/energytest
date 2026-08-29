"""Additional non-LLM baselines: Semgrep and Cppcheck on the exact 1549 functions.

  python -m harness.scripts.static_baselines [--tool semgrep|cppcheck|all]

Reviewers 2 and 3 both asked for a stronger, semantic static-analysis baseline
than the lexical Flawfinder, naming CodeQL. CodeQL is not applicable here:
building a CodeQL database for C/C++ requires tracing a real compilation, and
PrimeVul functions are isolated snippets with no headers, no includes and no
build system, so no database can be created. We therefore use two analyzers that
are designed to work on unbuildable code:

  * Semgrep with the community C/C++ security rulesets -- pattern and intra-
    procedural taint analysis, no build required.
  * Cppcheck with all checks enabled -- flow-sensitive checking that tolerates
    missing headers via --force and by ignoring configuration errors.

Both are scored exactly like the LLMs: a function is predicted vulnerable if the
tool raises at least one finding at or above a severity threshold, and the
threshold is swept so the precision/recall trade-off is visible rather than
fixed by our choice.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from harness.analysis.stats import balanced_accuracy, mcc, precision_at_prevalence

COMBINED = "harness/runs/primevul_combined/results.jsonl"
PRIMEVUL = "harness/data/primevul/primevul_test.jsonl"
PREVALENCE = 549 / 24788
OUTDIR = Path("harness/runs/static_baselines")

# Semgrep severities, ordered least to most severe; sweeping these mirrors the
# Flawfinder risk-level sweep so the two are directly comparable.
SEMGREP_SEVERITIES = ["INFO", "WARNING", "ERROR"]
CPPCHECK_SEVERITIES = ["style", "performance", "portability", "warning", "error"]
# Severities that plausibly indicate a security defect, most permissive first.
CPPCHECK_THRESHOLDS = [
    ("any", set(CPPCHECK_SEVERITIES)),
    ("warning+", {"warning", "error", "portability"}),
    ("error", {"error"}),
]


def task_labels() -> dict:
    out = {}
    for line in open(COMBINED, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[str(r["task_id"])] = r["label"]
    return out


def func_source(task_ids: set) -> dict:
    src = {}
    for line in open(PRIMEVUL, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            tid = str(r["idx"])
            if tid in task_ids:
                src[tid] = r["func"]
    return src


def materialize(src: dict, dest: Path) -> None:
    """One .c file per function, named by task id, so findings map back cleanly."""
    dest.mkdir(parents=True, exist_ok=True)
    for tid, code in src.items():
        (dest / f"{tid}.c").write_text(code, encoding="utf-8", errors="replace")


def run_semgrep(src_dir: Path) -> dict:
    """{task_id: highest severity index found}, -1 when clean."""
    cmd = [
        "semgrep", "scan",
        "--config=p/c",
        "--config=p/security-audit",
        "--json", "--quiet", "--no-git-ignore",
        "--metrics=off", "--timeout=15", "--max-target-bytes=0",
        str(src_dir),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if not proc.stdout.strip():
        print("semgrep produced no output:", proc.stderr[:400], file=sys.stderr)
        return {}
    data = json.loads(proc.stdout)
    hits: dict = {}
    for f in data.get("results", []):
        tid = Path(f["path"]).stem
        sev = f.get("extra", {}).get("severity", "INFO").upper()
        idx = SEMGREP_SEVERITIES.index(sev) if sev in SEMGREP_SEVERITIES else 0
        hits[tid] = max(hits.get(tid, -1), idx)
    return hits


def run_cppcheck(src_dir: Path) -> dict:
    """{task_id: set of severities found}."""
    cmd = [
        "cppcheck", "--enable=all", "--force", "--inline-suppr", "--quiet",
        "--template={file}|{severity}|{id}",
        # Snippets have no headers; without these every file is an error, not a finding.
        "--suppress=missingInclude", "--suppress=missingIncludeSystem",
        "--suppress=unmatchedSuppression", "--suppress=checkersReport",
        "--std=c11", str(src_dir),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    hits: dict = {}
    for line in (proc.stderr or "").splitlines():
        parts = line.strip().split("|")
        if len(parts) != 3:
            continue
        path, sev, _rule = parts
        tid = Path(path).stem
        hits.setdefault(tid, set()).add(sev)
    return hits


def score(name: str, labels: dict, predicted: dict) -> dict:
    tp = sum(1 for t, y in labels.items() if y == 1 and predicted.get(t, 0) == 1)
    fn = sum(1 for t, y in labels.items() if y == 1 and predicted.get(t, 0) == 0)
    fp = sum(1 for t, y in labels.items() if y == 0 and predicted.get(t, 0) == 1)
    tn = sum(1 for t, y in labels.items() if y == 0 and predicted.get(t, 0) == 0)
    ba = balanced_accuracy(tp, fp, fn, tn)
    rec = tp / (tp + fn) if tp + fn else 0.0
    spec = tn / (tn + fp) if tn + fp else 0.0
    prec = tp / (tp + fp) if tp + fp else 0.0
    return {
        "setting": name, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "bal_acc": ba, "mcc": mcc(tp, fp, fn, tn),
        "f1": (2 * prec * rec / (prec + rec)) if prec + rec else 0.0,
        "accuracy": (tp + tn) / max(len(labels), 1),
        "recall": rec, "specificity": spec,
        # second argument is TNR (specificity), not FPR
        "precision_at_1to44": precision_at_prevalence(rec, spec, PREVALENCE),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool", default="all", choices=["semgrep", "cppcheck", "all"])
    ap.add_argument("--keep-src", action="store_true")
    args = ap.parse_args()

    labels = task_labels()
    src = func_source(set(labels))
    print(f"{len(labels)} evaluated functions, {len(src)} sources resolved")
    OUTDIR.mkdir(parents=True, exist_ok=True)

    tmp = Path(tempfile.mkdtemp(prefix="statbase_"))
    try:
        src_dir = tmp / "src"
        materialize(src, src_dir)
        results = {}

        if args.tool in ("semgrep", "all"):
            if shutil.which("semgrep"):
                print("running semgrep ...")
                hits = run_semgrep(src_dir)
                rows = []
                for i, sev in enumerate(SEMGREP_SEVERITIES):
                    pred = {t: int(hits.get(t, -1) >= i) for t in labels}
                    rows.append(score(f"severity>={sev}", labels, pred))
                results["semgrep"] = rows
            else:
                print("semgrep not installed, skipping", file=sys.stderr)

        if args.tool in ("cppcheck", "all"):
            if shutil.which("cppcheck"):
                print("running cppcheck ...")
                hits = run_cppcheck(src_dir)
                rows = []
                for name, keep in CPPCHECK_THRESHOLDS:
                    pred = {t: int(bool(hits.get(t, set()) & keep)) for t in labels}
                    rows.append(score(name, labels, pred))
                results["cppcheck"] = rows
            else:
                print("cppcheck not installed, skipping", file=sys.stderr)

        for tool, rows in results.items():
            print(f"\n{tool}")
            print(f"{'setting':16s} {'bal_acc':>8s} {'mcc':>7s} {'recall':>7s} "
                  f"{'spec':>7s} {'prec@1:44':>10s}")
            for r in rows:
                print(f"{r['setting']:16s} {r['bal_acc']:8.3f} {r['mcc']:7.3f} "
                      f"{r['recall']:7.3f} {r['specificity']:7.3f} "
                      f"{r['precision_at_1to44']*100:9.2f}%")
            (OUTDIR / f"{tool}_scores.json").write_text(
                json.dumps(rows, indent=2), encoding="utf-8")
        print(f"\nwrote {OUTDIR}")
    finally:
        if args.keep_src:
            print(f"sources kept at {tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
