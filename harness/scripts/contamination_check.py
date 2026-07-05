"""Contamination proxy: does detection recall rise for older (more-documented) CVEs?

  python -m harness.scripts.contamination_check

PrimeVul functions come from public CVE-fixing commits (2008-2022 here), all
predating the 2026 models' training cutoffs, so a clean post-cutoff hold-out is
not available. As a memorization proxy we bin the vulnerable functions by CVE year
and report per-model recall: a systematic advantage on older, well-documented CVEs
is consistent with (though not proof of) memorization-driven inflation.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict

COMBINED = "harness/runs/primevul_combined/results.jsonl"
PRIMEVUL = "harness/data/primevul/primevul_test.jsonl"
ERAS = ["<=2020", "2021", "2022"]
MODELS = ["deepseek-v3.2", "gemma-3-4b", "glm-5", "gemini-3.1-pro", "gpt-5.1", "claude-sonnet-5"]


def _era(y: int) -> str:
    return "<=2020" if y <= 2020 else str(y)


def cve_year_by_task(task_ids: set) -> dict:
    out = {}
    for line in open(PRIMEVUL, encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        tid = str(r["idx"])
        if tid in task_ids:
            m = re.match(r"CVE-(\d{4})-", str(r.get("cve") or ""))
            if m:
                out[tid] = int(m.group(1))
    return out


def main() -> int:
    rows = [json.loads(l) for l in open(COMBINED, encoding="utf-8") if l.strip()]
    ids = {str(r["task_id"]) for r in rows}
    year = cve_year_by_task(ids)

    rec = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # model -> era -> [hits, total]
    for r in rows:
        tid = str(r["task_id"])
        if r["label"] == 1 and r["parsed_ok"] and tid in year:
            e = _era(year[tid])
            rec[r["model_id"]][e][1] += 1
            rec[r["model_id"]][e][0] += int(r["prediction"] == 1)

    counts = {e: rec["deepseek-v3.2"][e][1] for e in ERAS}
    print(f"Vulnerable functions with CVE year, per era: {counts}\n")
    print(f"{'model':<18}" + "".join(f"{e:>9}" for e in ERAS) + "   gap(old-new)")
    for m in MODELS:
        vals = [rec[m][e][0] / rec[m][e][1] if rec[m][e][1] else 0.0 for e in ERAS]
        gap = vals[0] - (vals[1] + vals[2]) / 2
        print(f"{m:<18}" + "".join(f"{v:>9.3f}" for v in vals) + f"   {gap:+.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
