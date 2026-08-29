"""Can LLM self-reported confidence supply a threshold-sweepable score? (R2#8)

  python -m harness.scripts.confidence_analysis [--run DIR]

Reviewer 2 asked for precision-recall curves, calibration, workload-at-fixed-recall
and VD-Score. All of those need a continuous score, which a binary verdict cannot
give. We therefore re-ran every model asking it to emit, alongside its verdict,
an integer 0-100 defined explicitly in the prompt as "the probability, in percent,
that the code contains a vulnerability: 0 means certainly safe, 100 means certainly
vulnerable".

That instruction is unambiguous, and most models did not follow it. This script
quantifies how they failed, because the failure is the answer to the reviewer's
request: it establishes that elicited confidence is not a sound substitute for a
model score on this task, rather than leaving the question open.

Two readings of a returned number are possible and they are incompatible:

  literal      score = c            the model reports P(vulnerable), as asked
  conditional  score = c if YES     the model reports confidence in its own
                       else 1 - c   verdict, the common default behaviour

Which one a model used is diagnosable from its own output: under the literal
reading a NO verdict should carry a LOW number. We report the diagnostic, and the
AUC under both readings, rather than silently picking whichever is higher --
choosing the reading by its result would be fitting the metric to the data.
"""

from __future__ import annotations

import argparse
import glob
import json
from collections import defaultdict

from harness.analysis.stats import average_precision, roc_auc

DEFAULT_GLOB = "harness/runs/r2_conf-*/results.jsonl"


def load(pattern: str):
    files = sorted(glob.glob(pattern))
    if not files:
        raise SystemExit(f"no run matching {pattern}")
    per = defaultdict(list)
    for line in open(files[0], encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            per[r["model_id"]].append(r)
    return files[0], per


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=DEFAULT_GLOB)
    ap.add_argument("--json", default="harness/runs/confidence_analysis.json")
    args = ap.parse_args()

    path, per = load(args.run)
    print(f"source: {path}\n")

    hdr = (f"{'model':20s} {'n_conf':>7s} {'cover':>6s} {'lvls':>5s} "
           f"{'c|NO':>6s} {'c|YES':>6s} {'reading':>12s} "
           f"{'AUC_lit':>8s} {'AUC_cond':>9s} {'verdict BA':>11s}")
    print(hdr)
    print("-" * len(hdr))

    out = {}
    for mid, rows in sorted(per.items()):
        ok = [r for r in rows if r.get("parsed_ok") and r.get("confidence") is not None]
        cover = len(ok) / len(rows)
        ys = [r["label"] for r in ok]
        cs = [r["confidence"] for r in ok]
        vs = [r["prediction"] for r in ok]

        if len(ok) < 50 or len(set(ys)) < 2:
            print(f"{mid:20s} {len(ok):7d} {cover:6.3f} "
                  f"{'--':>5s} {'--':>6s} {'--':>6s} {'UNUSABLE':>12s} "
                  f"{'--':>8s} {'--':>9s} {'--':>11s}")
            out[mid] = {"n_conf": len(ok), "coverage": cover, "usable": False}
            continue

        c_no = [c for c, v in zip(cs, vs) if v == 0]
        c_yes = [c for c, v in zip(cs, vs) if v == 1]
        m_no = sum(c_no) / len(c_no) if c_no else float("nan")
        m_yes = sum(c_yes) / len(c_yes) if c_yes else float("nan")

        # Under the literal reading a NO verdict carries a LOW number; under the
        # conditional one it carries a high number. A model that does BOTH within
        # the same verdict class has not settled on a convention at all, and its
        # mean is then meaningless -- check that before trusting the mean.
        # The two readings make different, checkable predictions about how the
        # number relates to the verdict, so the convention can be identified from
        # the outputs alone without consulting any AUC:
        #   literal      c means P(vulnerable), so YES verdicts carry much
        #                higher numbers than NO verdicts
        #   conditional  c means "how sure am I", which is independent of the
        #                verdict's direction, so both classes sit high together
        #   degenerate   both classes sit at the floor: no information either way
        #   inconsistent a single verdict class is split across both conventions,
        #                which makes its mean meaningless
        hi = sum(1 for c in c_no if c > 0.5) / len(c_no) if c_no else 0.0
        if c_no and 0.25 < hi < 0.75:
            reading = "INCONSISTENT"
        elif m_yes - m_no > 0.20:
            reading = "literal"
        elif m_no > 0.5 and m_yes > 0.5:
            reading = "conditional"
        else:
            reading = "DEGENERATE"

        lit = roc_auc(ys, cs)
        cond = roc_auc(ys, [c if v == 1 else 1.0 - c for c, v in zip(cs, vs)])
        # The binary verdict's own balanced accuracy, as the point of comparison:
        tp = sum(1 for y, v in zip(ys, vs) if y == 1 and v == 1)
        fn = sum(1 for y, v in zip(ys, vs) if y == 1 and v == 0)
        fp = sum(1 for y, v in zip(ys, vs) if y == 0 and v == 1)
        tn = sum(1 for y, v in zip(ys, vs) if y == 0 and v == 0)
        ba = 0.5 * (tp / max(tp + fn, 1) + tn / max(tn + fp, 1))

        print(f"{mid:20s} {len(ok):7d} {cover:6.3f} {len(set(cs)):5d} "
              f"{m_no:6.2f} {m_yes:6.2f} {reading:>12s} "
              f"{lit:8.4f} {cond:9.4f} {ba:11.4f}")
        out[mid] = {
            "n_conf": len(ok), "coverage": cover, "distinct_levels": len(set(cs)),
            "mean_conf_given_no": m_no, "mean_conf_given_yes": m_yes,
            "apparent_reading": reading, "frac_no_verdicts_above_half": hi,
            "auc_literal": lit,
            "auc_conditional": cond, "pr_auc_conditional": average_precision(
                ys, [c if v == 1 else 1.0 - c for c, v in zip(cs, vs)]),
            "verdict_bal_acc": ba, "usable": reading in ("literal", "conditional"),
        }

    print("\nHow to read this:")
    print("  cover    fraction of tasks that returned a parseable verdict AND a number")
    print("  lvls     distinct confidence values used -- a handful means the score")
    print("           cannot support a fine-grained threshold sweep whatever its AUC")
    print("  reading  inferred from the model's own outputs, not chosen by result")
    print("  AUC_*    ranking quality under each reading; 0.5 is no signal")
    print("\nA model is only a usable score source if coverage is high, levels are")
    print("many, and the AUC under its apparent reading materially exceeds the")
    print("balanced accuracy its plain verdict already achieves. Otherwise the")
    print("elicited number adds nothing a binary verdict did not already provide.")

    json.dump(out, open(args.json, "w", encoding="utf-8"), indent=2)
    print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
