"""Fold the concurrency sweeps into the paper's energy and break-even claims.

  python -m harness.scripts.analyze_sweeps

Reads harness/runs/concurrency_sweep/{gemma,qwen,llama}.json and answers the three
questions the round-1 reviews raised about energy:

1. How far off is the FLOP estimator, and in which regime? The estimator's
   energy-per-FLOP constant is calibrated to batched datacenter serving, so if it
   matches the concurrency-1 measurement rather than the batched one, it is
   effectively a single-request estimate and every API-served figure in the paper
   is overstated by the batching factor.

2. Is the batching factor uniform across models? This is what decides whether the
   correction is cosmetic or structural. The estimator is linear in
   active-parameters x tokens, so a uniform factor rescales every model equally and
   leaves the between-model ratios -- which is what the paper's argument rests on --
   untouched. A non-uniform factor would mean the ranking itself is regime-dependent.

3. What throughput does each model actually reach? That is the axis of the
   self-hosting break-even table, which until now had to be presented as a
   sensitivity analysis over an assumed value.
"""

from __future__ import annotations

import json
from pathlib import Path

SWEEPS = Path("harness/runs/concurrency_sweep")
METRICS = Path("harness/runs/primevul_combined/enriched_metrics.csv")

# FLOP-estimated energy per task from the main run, and the label used in the paper.
ESTIMATE_J = {"gemma": 64.4, "qwen": 40.2, "llama": 944.3}
LABEL = {"gemma": "Gemma-3-4B", "qwen": "Qwen3-Coder-30B", "llama": "Llama-3.3-70B"}
# Published concurrency-1 measurements (active J) for the two models already reported.
PUBLISHED_C1_J = {"qwen": 88.0, "llama": 738.0}

# Break-even inputs, matching Section 5.1 of the paper.
API_USD_PER_TASK = {"llama": 0.0000815, "qwen": 0.0000603, "gemma": 0.0000435}
HOURLY = {"rented H200": 3.50, "owned (amortized)": 1.46}


def load(tag: str):
    p = SWEEPS / f"{tag}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    sweeps = {t: load(t) for t in ("gemma", "qwen", "llama")}
    have = {t: v for t, v in sweeps.items() if v}
    if not have:
        print(f"no sweep results found in {SWEEPS}")
        return 1

    print("=" * 78)
    print("1. MEASURED ENERGY PER TASK vs CONCURRENCY")
    print("=" * 78)
    print(f"{'model':18s} " + " ".join(f"{'c='+str(c):>10s}" for c in (1, 8, 32, 64))
          + f" {'c1/c64':>8s}")
    for tag, rows in have.items():
        by = {r["concurrency"]: r for r in rows}
        cells = []
        for c in (1, 8, 32, 64):
            cells.append(f"{by[c]['active_j_per_task']:10.1f}" if c in by else f"{'--':>10s}")
        ratio = (by[1]["active_j_per_task"] / by[64]["active_j_per_task"]
                 if 1 in by and 64 in by else float("nan"))
        print(f"{LABEL[tag]:18s} " + " ".join(cells) + f" {ratio:7.1f}x")

    print()
    print("=" * 78)
    print("2. FLOP ESTIMATE vs MEASUREMENT -- which regime does the estimator match?")
    print("=" * 78)
    print(f"{'model':18s} {'estimate':>10s} {'meas c=1':>10s} {'est/c1':>8s} "
          f"{'meas c=64':>10s} {'est/c64':>9s}")
    factors = {}
    for tag, rows in have.items():
        by = {r["concurrency"]: r for r in rows}
        est = ESTIMATE_J[tag]
        c1 = by.get(1, {}).get("active_j_per_task")
        c64 = by.get(64, {}).get("active_j_per_task")
        if not (c1 and c64):
            continue
        factors[tag] = est / c64
        print(f"{LABEL[tag]:18s} {est:10.1f} {c1:10.1f} {est/c1:7.2f}x "
              f"{c64:10.1f} {est/c64:8.1f}x")

    if len(factors) > 1:
        lo, hi = min(factors.values()), max(factors.values())
        print(f"\n   overstatement at c=64 spans {lo:.1f}x to {hi:.1f}x "
              f"across {len(factors)} models (spread {hi/lo:.2f}x)")
        if hi / lo < 2.0:
            print("   -> roughly UNIFORM: the correction rescales all models similarly, so")
            print("      between-model ratios, which carry the paper's argument, survive.")
        else:
            print("   -> NOT uniform: the energy ranking is regime-dependent and the")
            print("      comparison must state which serving regime it refers to.")

    for tag, pub in PUBLISHED_C1_J.items():
        if tag in have:
            by = {r["concurrency"]: r for r in have[tag]}
            if 1 in by:
                new = by[1]["active_j_per_task"]
                print(f"\n   {LABEL[tag]}: published c=1 was {pub:.0f} J, re-measured "
                      f"{new:.1f} J ({new/pub:.2f}x)")

    print()
    print("=" * 78)
    print("3. THROUGHPUT AND SELF-HOSTING BREAK-EVEN")
    print("=" * 78)
    for tag, rows in have.items():
        by = {r["concurrency"]: r for r in rows}
        if 64 not in by:
            continue
        thru = by[64]["throughput_tasks_per_s"]
        api = API_USD_PER_TASK.get(tag)
        print(f"\n{LABEL[tag]}: {thru:.1f} task/s at c=64  (API list ${api:.7f}/task)")
        for name, hourly in HOURLY.items():
            self_cost = hourly / (3600 * thru)
            be = hourly / (3600 * api)
            verdict = "CHEAPER than API" if self_cost < api else "dearer than API"
            print(f"   {name:20s} ${self_cost:.7f}/task  {verdict} "
                  f"({self_cost/api:.2f}x)   break-even at {be:.1f} task/s")

    print()
    print("=" * 78)
    print("4. SANITY: accuracy must not move with concurrency")
    print("=" * 78)
    import glob
    for tag in have:
        accs = []
        for d in sorted(glob.glob(f"harness/runs/{tag}_c*/results.jsonl")):
            rows = [json.loads(l) for l in open(d, encoding="utf-8") if l.strip()]
            if rows:
                accs.append((Path(d).parent.name.split("_c")[1].split("-")[0],
                             sum(r["correct"] for r in rows) / len(rows)))
        if accs:
            spread = max(a for _, a in accs) - min(a for _, a in accs)
            print(f"{LABEL[tag]:18s} " + "  ".join(f"c{c}={a:.4f}" for c, a in accs)
                  + f"   spread {spread:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
