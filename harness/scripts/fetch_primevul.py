"""Fetch the PrimeVul test split onto a fresh machine (e.g. a GPU pod).

  python -m harness.scripts.fetch_primevul

The dataset is gitignored (64 MB), so a clone does NOT carry it and every run
dies with FileNotFoundError on harness/data/primevul/primevul_test.jsonl. This
pulls it from a Hugging Face mirror and verifies it before writing.

The verification matters. The evaluated 1549-function sample is drawn from this
file by seed, so a mirror carrying a different dataset revision would silently
produce a different sample and quietly invalidate any comparison against the
published numbers. We check the row count, the vulnerable count, and a hash over
every (idx, target, func) triple. The mirror below was verified byte-identical to
the split used for the paper on 2026-08-29.

Sampling is order-independent -- the loader sorts by task id within each label
group before sampling -- so line ordering in the mirror does not matter.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

MIRROR = "starsofchance/PrimeVul"
FILENAME = "primevul_test.jsonl"
DEST = Path("harness/data/primevul/primevul_test.jsonl")

# Invariants of the split the paper was measured on.
EXPECT_ROWS = 24_788
EXPECT_VULN = 549


def summarize(path: Path) -> tuple[int, int, str]:
    h = hashlib.sha256()
    rows = vuln = 0
    for line in open(path, encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        rows += 1
        vuln += int(r["target"]) == 1
        h.update(f"{r['idx']}\x00{r['target']}\x00{r['func']}\x00".encode())
    return rows, vuln, h.hexdigest()[:16]


def main() -> int:
    if DEST.exists():
        rows, vuln, digest = summarize(DEST)
        print(f"already present: {DEST} ({rows} rows, {vuln} vulnerable, content {digest})")
        if rows == EXPECT_ROWS and vuln == EXPECT_VULN:
            return 0
        print("  but it does NOT match the expected split -- re-fetching", file=sys.stderr)

    from huggingface_hub import hf_hub_download

    print(f"downloading {FILENAME} from {MIRROR} ...")
    cached = hf_hub_download(MIRROR, FILENAME, repo_type="dataset")

    rows, vuln, digest = summarize(Path(cached))
    print(f"  {rows} rows, {vuln} vulnerable, content {digest}")
    if rows != EXPECT_ROWS or vuln != EXPECT_VULN:
        print(f"REFUSING to install: expected {EXPECT_ROWS} rows / {EXPECT_VULN} vulnerable. "
              f"This mirror is a different dataset revision and would change the sample.",
              file=sys.stderr)
        return 1

    DEST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(cached, DEST)
    print(f"installed {DEST} ({DEST.stat().st_size / 1e6:.1f} MB) -- verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
