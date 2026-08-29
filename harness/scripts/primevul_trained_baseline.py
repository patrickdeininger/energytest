"""LineVul-class detector fine-tuned on the PrimeVul TRAIN split (paper Section 4.4).

  # 1. verify the mirror and check for leakage (CPU, no GPU needed)
  python -m harness.scripts.primevul_trained_baseline --check-only
  # 2. fine-tune and evaluate (GPU)
  python -m harness.scripts.primevul_trained_baseline --epochs 3 --batch-size 16

Reviewers 2 and 3 both objected that CodeBERT-Devign is a cross-dataset transfer
model, predictably damaged by distribution shift, and therefore not a fair
learned baseline. They are right. This trains the same architecture on
PrimeVul's own training split -- a RoBERTa/CodeBERT encoder with a binary
classification head, which is the LineVul recipe -- and evaluates it on the
identical 1549 functions the LLMs saw.

The expected result is not a strong detector. PrimeVul's own authors report that
models fine-tuned on its training split remain close to random on its test split,
and reproducing that is the point: it establishes that the benchmark is hard for
trained detectors too, rather than that our particular off-the-shelf baseline was
weak.

Leakage is checked explicitly rather than assumed. PrimeVul splits chronologically,
so no evaluated function should appear in training, but a duplicate function body
across splits would silently inflate the baseline and we would rather find that
ourselves than have a reviewer find it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

MIRROR = "starsofchance/PrimeVul"
COMBINED = "harness/runs/primevul_combined/results.jsonl"
LOCAL_TEST = "harness/data/primevul/primevul_test.jsonl"
OUTDIR = Path("harness/runs/primevul_trained_baseline")
PREVALENCE = 549 / 24788
# The evaluated sample is fully specified by these two numbers plus the test split.
SAMPLE_N = 2000
SAMPLE_SEED = 12345


def _norm(code: str) -> str:
    """Whitespace-insensitive body hash: a duplicate that differs only in
    indentation is still a duplicate for leakage purposes."""
    return hashlib.sha256(" ".join(code.split()).encode()).hexdigest()


def fetch(name: str) -> Path:
    from huggingface_hub import hf_hub_download

    return Path(hf_hub_download(MIRROR, name, repo_type="dataset"))


def read_jsonl(path: Path | str):
    for line in open(path, encoding="utf-8"):
        if line.strip():
            yield json.loads(line)


def verify_mirror() -> None:
    """The mirror's test split must match the split we evaluated on, or its train
    split may belong to a different dataset version."""
    mine = {str(r["idx"]): (r["target"], _norm(r["func"])) for r in read_jsonl(LOCAL_TEST)}
    theirs = {str(r["idx"]): (r["target"], _norm(r["func"])) for r in read_jsonl(fetch("primevul_test.jsonl"))}
    assert len(mine) == len(theirs), f"row count differs: {len(mine)} vs {len(theirs)}"
    bad = [k for k in mine if mine[k] != theirs.get(k)]
    assert not bad, f"{len(bad)} rows differ between local and mirror test splits"
    print(f"mirror verified: {len(mine)} test rows identical to the evaluated split")


def evaluated_ids() -> dict:
    """The 1549 evaluated task ids -> label.

    Derived from the sampling specification (n=2000 stratified by label at seed
    12345 over the test split), NOT read out of a previous run's results.jsonl.
    The sample is deterministic, so regenerating it is exact, and it removes a
    dependency on a gitignored run artifact that a fresh machine does not have.
    When a results file IS present we cross-check against it, since a silent
    divergence here would evaluate the baseline on a different set than the LLMs.
    """
    from harness.data.loader import load_jsonl

    tasks = load_jsonl(
        LOCAL_TEST, code_field="func", label_field="target", id_field="idx",
        cwe_field="cwe", source="jsonl", n=SAMPLE_N, stratify_by="label", seed=SAMPLE_SEED,
    )
    derived = {str(t.id): t.label for t in tasks}

    combined = Path(COMBINED)
    if combined.exists():
        from_run = {str(r["task_id"]): r["label"] for r in read_jsonl(combined)}
        if set(from_run) != set(derived):
            raise AssertionError(
                f"derived sample ({len(derived)}) does not match the evaluated run "
                f"({len(from_run)}); the baseline would be scored on a different set"
            )
        print(f"  sample cross-checked against {COMBINED}")
    return derived


def resolve_checkpoint(spec: str) -> str:
    """Resolve --from-checkpoint. 'auto' finds the checkpoint training actually
    selected.

    Training runs with load_best_model_at_end on eval_loss, so the model that
    produced a given set of scores is whichever epoch had the lowest validation
    loss -- not necessarily the last one on disk. Scoring a different checkpoint
    would silently produce numbers that do not correspond to the run we are
    building on, so this reads the choice out of the trainer state rather than
    guessing.
    """
    if spec != "auto":
        return spec

    import glob

    states = sorted(
        glob.glob(str(OUTDIR / "ckpt" / "checkpoint-*" / "trainer_state.json")),
        key=lambda p: int(p.split("checkpoint-")[1].split(os.sep)[0].split("/")[0]),
    )
    if not states:
        raise SystemExit(f"no checkpoints under {OUTDIR / 'ckpt'}; train first")
    st = json.loads(Path(states[-1]).read_text(encoding="utf-8"))

    best = st.get("best_model_checkpoint")
    if best and Path(best).is_dir():
        print(f"checkpoint: {best} (recorded by the trainer as best)")
        return best

    evals = [(h["eval_loss"], h["step"]) for h in st.get("log_history", [])
             if "eval_loss" in h]
    if evals:
        step = min(evals)[1]
        cand = OUTDIR / "ckpt" / f"checkpoint-{step}"
        if cand.is_dir():
            print(f"checkpoint: {cand} (lowest eval_loss {min(evals)[0]:.4f} "
                  f"in the log history)")
            return str(cand)

    last = str(Path(states[-1]).parent)
    print(f"checkpoint: {last} (no best recorded; falling back to the last)")
    return last


def check_leakage(train_rows, eval_ids: set, eval_bodies: dict) -> dict:
    by_id = sum(1 for r in train_rows if str(r["idx"]) in eval_ids)
    train_bodies = {_norm(r["func"]) for r in train_rows}
    by_body = sum(1 for tid, h in eval_bodies.items() if h in train_bodies)
    print(f"leakage check: {by_id} evaluated ids in train, "
          f"{by_body}/{len(eval_bodies)} evaluated function bodies duplicated in train")
    return {"overlap_by_id": by_id, "overlap_by_body": by_body, "n_eval": len(eval_bodies)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-only", action="store_true",
                    help="verify mirror + leakage only; no training (runs on CPU)")
    ap.add_argument("--model", default="microsoft/codebert-base")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--max-length", type=int, default=512)
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--no-class-weight", action="store_true",
                    help="disable inverse-frequency class weighting (reproduces the "
                         "collapse-to-majority failure; kept only for the record)")
    ap.add_argument("--from-checkpoint", default=None, nargs="?", const="auto",
                    help="skip training and score an existing checkpoint. Pass 'auto' "
                         "(or give the flag with no value) to use the one the trainer "
                         "recorded as best, which is what produced the saved scores.")
    ap.add_argument("--valid-subsample", type=int, default=6000,
                    help="validation rows used for threshold selection (the full "
                         "split is 23,948; a subsample keeps the pass short and the "
                         "threshold estimate is already stable at a few thousand)")
    args = ap.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    verify_mirror()

    train_rows = list(read_jsonl(fetch("primevul_train.jsonl")))
    valid_rows = list(read_jsonl(fetch("primevul_valid.jsonl")))
    labels = evaluated_ids()
    eval_bodies = {str(r["idx"]): _norm(r["func"])
                   for r in read_jsonl(LOCAL_TEST) if str(r["idx"]) in labels}
    print(f"train {len(train_rows)} ({sum(r['target'] for r in train_rows)} vulnerable), "
          f"valid {len(valid_rows)}, eval {len(labels)}")

    leak = check_leakage(train_rows, set(labels), eval_bodies)
    (OUTDIR / "leakage_check.json").write_text(json.dumps(leak, indent=2), encoding="utf-8")

    if args.check_only:
        print("check-only: stopping before training")
        return 0

    # --- training (GPU) ----------------------------------------------------
    import numpy as np
    import torch
    from torch.utils.data import Dataset
    from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                              Trainer, TrainingArguments, set_seed)

    from harness.analysis.stats import (balanced_accuracy, mcc,
                                        precision_at_prevalence, wilson_interval)

    set_seed(args.seed)
    tok = AutoTokenizer.from_pretrained(args.model)

    class DS(Dataset):
        def __init__(self, rows):
            self.rows = rows

        def __len__(self):
            return len(self.rows)

        def __getitem__(self, i):
            r = self.rows[i]
            enc = tok(r["func"], truncation=True, max_length=args.max_length,
                      padding="max_length", return_tensors="pt")
            return {"input_ids": enc["input_ids"][0],
                    "attention_mask": enc["attention_mask"][0],
                    "labels": torch.tensor(int(r["target"]))}

    eval_rows = [r for r in read_jsonl(LOCAL_TEST) if str(r["idx"]) in labels]
    model = AutoModelForSequenceClassification.from_pretrained(args.model, num_labels=2)

    # PrimeVul's training split is 2.77% positive (4,862 of 175,797). Under plain
    # cross-entropy the optimum is to predict "safe" everywhere, which scores 97.2%
    # training accuracy and yields a detector with recall 0 -- we produced exactly
    # that on the first attempt. Inverse-frequency weighting removes that optimum.
    n_pos = sum(int(r["target"]) for r in train_rows)
    n_neg = len(train_rows) - n_pos
    w = torch.tensor([1.0, n_neg / max(n_pos, 1)], dtype=torch.float)
    print(f"class balance: {n_pos} positive / {n_neg} negative "
          f"({n_pos/len(train_rows)*100:.2f}%); positive class weight "
          f"{w[1]:.1f}" + (" [DISABLED]" if args.no_class_weight else ""))

    class WeightedTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False, **kw):
            lab = inputs.pop("labels")
            out = model(**inputs)
            loss = torch.nn.functional.cross_entropy(
                out.logits, lab, weight=w.to(out.logits.device))
            return (loss, out) if return_outputs else loss

    TrainerCls = Trainer if args.no_class_weight else WeightedTrainer

    targs = TrainingArguments(
        output_dir=str(OUTDIR / "ckpt"), num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size * 2,
        learning_rate=args.lr, warmup_ratio=0.06, weight_decay=0.01,
        eval_strategy="epoch", save_strategy="epoch",
        load_best_model_at_end=True, metric_for_best_model="eval_loss",
        logging_steps=200, seed=args.seed, fp16=torch.cuda.is_available(),
        report_to=[],
    )
    trainer = TrainerCls(model=model, args=targs,
                         train_dataset=DS(train_rows), eval_dataset=DS(valid_rows))
    if args.from_checkpoint:
        ckpt = resolve_checkpoint(args.from_checkpoint)
        print(f"loading {ckpt} (skipping training)")
        model = AutoModelForSequenceClassification.from_pretrained(ckpt, num_labels=2)
        trainer.model = model.to(trainer.args.device)
    else:
        trainer.train()

    def score(rows):
        lg = trainer.predict(DS(rows)).predictions
        return torch.softmax(torch.tensor(lg), dim=-1)[:, 1].numpy()

    # Select the decision threshold on VALIDATION, never on the evaluation set.
    # Sweeping the threshold on test and reporting the best value is an oracle
    # result: it reports the best a threshold could have done, not what this
    # detector achieves. On our first run that difference is the whole finding,
    # since the model's scores never exceed 0.372 and argmax collapses.
    import random as _random

    vrows = valid_rows
    if args.valid_subsample and len(vrows) > args.valid_subsample:
        vrows = _random.Random(args.seed).sample(vrows, args.valid_subsample)
    print(f"selecting threshold on {len(vrows)} validation rows ...")
    vprobs = score(vrows)
    vys = np.array([int(r["target"]) for r in vrows])
    tuned, tuned_ba = 0.5, -1.0
    for thr in np.unique(np.round(vprobs, 4)):
        p = (vprobs >= thr).astype(int)
        v_tp = int(((p == 1) & (vys == 1)).sum()); v_fp = int(((p == 1) & (vys == 0)).sum())
        v_fn = int(((p == 0) & (vys == 1)).sum()); v_tn = int(((p == 0) & (vys == 0)).sum())
        ba = balanced_accuracy(v_tp, v_fp, v_fn, v_tn)
        if ba > tuned_ba:
            tuned, tuned_ba = float(thr), ba
    print(f"  validation-selected threshold {tuned:.4f} (validation bal.acc {tuned_ba:.4f})")

    probs = score(eval_rows)
    preds = (probs >= tuned).astype(int)
    ys = np.array([int(r["target"]) for r in eval_rows])

    tp = int(((preds == 1) & (ys == 1)).sum()); fp = int(((preds == 1) & (ys == 0)).sum())
    fn = int(((preds == 0) & (ys == 1)).sum()); tn = int(((preds == 0) & (ys == 0)).sum())
    rec = tp / (tp + fn) if tp + fn else 0.0
    spec = tn / (tn + fp) if tn + fp else 0.0
    prec = tp / (tp + fp) if tp + fp else 0.0
    tl, th = wilson_interval(tp, tp + fn); fl, fh = wilson_interval(fp, fp + tn)
    out = {
        "model": args.model, "trained_on": "primevul_train", "n": len(eval_rows),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "bal_acc": balanced_accuracy(tp, fp, fn, tn), "mcc": mcc(tp, fp, fn, tn),
        "f1": (2 * prec * rec / (prec + rec)) if prec + rec else 0.0,
        "accuracy": (tp + tn) / len(eval_rows), "recall": rec, "specificity": spec,
        "precision_at_1to44": precision_at_prevalence(rec, spec, PREVALENCE),
        "precision_at_1to44_ci": [precision_at_prevalence(tl, 1 - fh, PREVALENCE),
                                  precision_at_prevalence(th, 1 - fl, PREVALENCE)],
        "epochs": args.epochs, "seed": args.seed,
        # When scoring a checkpoint we did not train in this process, the flag
        # describes nothing: the loss used is a property of that training run.
        # Recording the flag here would mislabel the artifact.
        "class_weighted": (None if args.from_checkpoint else not args.no_class_weight),
        "scored_from_checkpoint": args.from_checkpoint or None,
        "threshold": tuned, "threshold_source": "validation split",
        "validation_bal_acc": tuned_ba, "n_validation_used": len(vrows),
        "leakage": leak,
    }

    # A collapsed argmax (predicting one class everywhere) can still hide a usable
    # ranking, so always report the threshold-free view. Without this we would have
    # concluded "trained detectors are near-random on PrimeVul" from what was
    # actually a class-imbalance training failure.
    from harness.analysis.stats import average_precision, roc_auc

    out["roc_auc"] = float(roc_auc(list(ys), list(probs)))
    out["pr_auc"] = float(average_precision(list(ys), list(probs)))
    out["score_min"], out["score_max"] = float(probs.min()), float(probs.max())

    # Reported for reference ONLY, and labelled as an oracle: this is the best a
    # threshold could have done had we been allowed to peek at the evaluation set.
    best = None
    for thr in np.unique(np.round(probs, 4)):
        p = (probs >= thr).astype(int)
        t_tp = int(((p == 1) & (ys == 1)).sum()); t_fp = int(((p == 1) & (ys == 0)).sum())
        t_fn = int(((p == 0) & (ys == 1)).sum()); t_tn = int(((p == 0) & (ys == 0)).sum())
        ba = balanced_accuracy(t_tp, t_fp, t_fn, t_tn)
        if best is None or ba > best["bal_acc"]:
            best = {"threshold": float(thr), "bal_acc": ba,
                    "recall": t_tp / max(t_tp + t_fn, 1),
                    "specificity": t_tn / max(t_tn + t_fp, 1),
                    "tp": t_tp, "fp": t_fp}
    out["oracle_best_threshold_TEST_SET_DO_NOT_REPORT_AS_RESULT"] = best

    if tp + fp == 0 or tn + fn == 0:
        out["WARNING"] = (
            "argmax collapsed to a single class. With PrimeVul's 2.77% positive rate "
            "this is the expected optimum of unweighted cross-entropy and is a "
            "training artifact, NOT evidence about the benchmark. Check roc_auc and "
            "best_threshold before drawing any conclusion."
        )
        print("\n*** " + out["WARNING"] + "\n")
    print(f"ROC-AUC {out['roc_auc']:.4f}  PR-AUC {out['pr_auc']:.4f}  "
          f"scores in [{out['score_min']:.4f}, {out['score_max']:.4f}]")
    print(f"\nREPORTABLE (threshold {tuned:.4f} chosen on validation):")
    print(f"   bal.acc {out['bal_acc']:.4f}  recall {rec:.3f}  spec {spec:.3f}  "
          f"prec@1:44 {out['precision_at_1to44']*100:.2f}%")
    print(f"oracle (threshold swept on the EVALUATION set -- not a result): "
          f"bal.acc {best['bal_acc']:.4f} at {best['threshold']:.4f}")
    (OUTDIR / "scores.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    # Per-item scores give this baseline the threshold sweep the LLMs lack.
    with (OUTDIR / "per_item.jsonl").open("w", encoding="utf-8") as fh:
        for r, p, pr in zip(eval_rows, probs, preds):
            fh.write(json.dumps({"task_id": str(r["idx"]), "label": int(r["target"]),
                                 "score": float(p), "prediction": int(pr)}) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "leakage"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
