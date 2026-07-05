"""Learned (fine-tuned) detector baseline: a CodeBERT vulnerability classifier on the
same 1549 functions.

  python -m harness.scripts.learned_baseline

The review panel asked for a fine-tuned learned detector (e.g. LineVul) to contextualize
the LLM scores. We run mahdin70/codebert-devign-code-vulnerability-detector -- a CodeBERT
model fine-tuned on the Devign C-function vulnerability dataset (the same architecture
family as LineVul) -- off the shelf on PrimeVul (a cross-dataset evaluation). Label 1 =
vulnerable. CPU inference, ~10 min. Scored with the same metrics as the LLMs and Flawfinder.
"""

from __future__ import annotations

import json
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from harness.analysis.stats import balanced_accuracy, mcc, precision_at_prevalence

MODEL = "mahdin70/codebert-devign-code-vulnerability-detector"
TOKENIZER = "microsoft/codebert-base"  # the model repo ships no tokenizer; use the backbone's
COMBINED = "harness/runs/primevul_combined/results.jsonl"
PRIMEVUL = "harness/data/primevul/primevul_test.jsonl"
PREVALENCE = 549 / 24788
OUT = Path("harness/runs/learned_baseline")
BATCH = 16
MAXLEN = 512


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
        if not line.strip():
            continue
        r = json.loads(line)
        tid = str(r["idx"])
        if tid in task_ids:
            src[tid] = r["func"]
    return src


def main() -> int:
    labels = task_labels()
    src = func_source(set(labels))
    ids = [t for t in labels if t in src]
    print(f"Scoring {len(ids)} functions ({sum(labels[t] for t in ids)} vulnerable) with {MODEL}")

    tok = AutoTokenizer.from_pretrained(TOKENIZER)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL)
    model.eval()
    torch.set_grad_enabled(False)

    preds: dict = {}
    for i in range(0, len(ids), BATCH):
        batch_ids = ids[i:i + BATCH]
        enc = tok([src[t] for t in batch_ids], truncation=True, max_length=MAXLEN,
                  padding=True, return_tensors="pt")
        logits = model(**enc).logits
        for t, lab in zip(batch_ids, logits.argmax(-1).tolist()):
            preds[t] = int(lab)   # label 1 = vulnerable
        if (i // BATCH) % 10 == 0:
            print(f"  {min(i + BATCH, len(ids))}/{len(ids)}")

    tp = sum(1 for t in ids if labels[t] == 1 and preds[t] == 1)
    fp = sum(1 for t in ids if labels[t] == 0 and preds[t] == 1)
    fn = sum(1 for t in ids if labels[t] == 1 and preds[t] == 0)
    tn = sum(1 for t in ids if labels[t] == 0 and preds[t] == 0)
    tpr = tp / (tp + fn) if (tp + fn) else 0.0
    tnr = tn / (tn + fp) if (tn + fp) else 0.0
    n = tp + fp + fn + tn
    rec = {
        "model": MODEL, "n": n, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "bal_acc": balanced_accuracy(tp, fp, fn, tn), "mcc": mcc(tp, fp, fn, tn),
        "f1": 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0,
        "accuracy": (tp + tn) / n, "recall": tpr, "specificity": tnr,
        "precision_at_1to44": precision_at_prevalence(tpr, tnr, PREVALENCE),
    }
    print("\n" + "  ".join(f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}"
                           for k, v in rec.items() if k != "model"))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "learned_scores.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
    print(f"Wrote {OUT / 'learned_scores.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
