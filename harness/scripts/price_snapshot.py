"""Provider price dispersion for the evaluated models (paper Section 5.x).

  python -m harness.scripts.price_snapshot [--out FILE]

Reviewer 1 asked us to be more careful moving from API price to computational
efficiency, "because market price is not the same as real serving cost", and
Reviewer 2 asked us to separate open-weight availability from API-served
evaluation. This script supplies the evidence for both.

For every evaluated model it records, at one instant, every provider serving it
through the gateway, that provider's per-token price, and the quantization it
serves at. The result makes the argument concretely: for an open-weight model,
"the price" is not a property of the model at all -- it is a routing choice
across many competing hosts, and the spread between them is far larger than any
efficiency difference we could measure. For a proprietary frontier model there
is effectively one seller.

The snapshot is written to disk and shipped with the reproduction package, since
prices move and the paper's numbers must remain checkable against a fixed date.
"""

from __future__ import annotations

import argparse
import datetime
import json
import urllib.request
from pathlib import Path

MODELS = {
    "claude-sonnet-5": ("anthropic/claude-sonnet-5", "frontier"),
    "gpt-5.1": ("openai/gpt-5.1", "frontier"),
    "gemini-3.1-pro": ("google/gemini-3.1-pro-preview", "frontier"),
    "deepseek-v3.2": ("deepseek/deepseek-v3.2", "open"),
    "glm-5": ("z-ai/glm-5", "open"),
    "llama-3.3-70b": ("meta-llama/llama-3.3-70b-instruct", "open"),
    "qwen3-coder-30b": ("qwen/qwen3-coder-30b-a3b-instruct", "open"),
    "gemma-3-4b": ("google/gemma-3-4b-it", "open"),
}
DEFAULT_OUT = Path("harness/runs/price_snapshot.json")


def fetch(slug: str) -> list[dict]:
    url = f"https://openrouter.ai/api/v1/models/{slug}/endpoints"
    with urllib.request.urlopen(url, timeout=60) as fh:
        data = json.load(fh)["data"]
    out = []
    for e in data.get("endpoints", []):
        out.append({
            "provider": e.get("provider_name") or e.get("name"),
            "in_per_mtok": float(e["pricing"]["prompt"]) * 1e6,
            "out_per_mtok": float(e["pricing"]["completion"]) * 1e6,
            "quantization": e.get("quantization"),
            "context_length": e.get("context_length"),
        })
    return sorted(out, key=lambda r: (r["in_per_mtok"], r["out_per_mtok"]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    snap = {
        "captured_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "gateway": "openrouter",
        "models": {},
    }
    print(f"{'model':18s} {'tier':9s} {'n':>3s} {'min in':>8s} {'max in':>8s} "
          f"{'spread':>7s} {'quantizations':>28s}")
    print("-" * 88)
    for mid, (slug, tier) in MODELS.items():
        try:
            eps = fetch(slug)
        except Exception as exc:  # a dead slug must not lose the whole snapshot
            print(f"{mid:18s} ERROR {exc}")
            snap["models"][mid] = {"slug": slug, "tier": tier, "error": str(exc)}
            continue
        ins = [e["in_per_mtok"] for e in eps]
        quants = sorted({str(e["quantization"]) for e in eps})
        spread = (max(ins) / min(ins)) if ins and min(ins) > 0 else float("nan")
        snap["models"][mid] = {
            "slug": slug, "tier": tier, "n_providers": len(eps),
            "min_in": min(ins) if ins else None, "max_in": max(ins) if ins else None,
            "spread_in": spread, "quantizations": quants, "endpoints": eps,
        }
        print(f"{mid:18s} {tier:9s} {len(eps):3d} {min(ins):8.3f} {max(ins):8.3f} "
              f"{spread:6.1f}x {','.join(quants)[:28]:>28s}")

    Path(args.out).write_text(json.dumps(snap, indent=2), encoding="utf-8")
    print(f"\nwrote {args.out}")

    open_spreads = [m["spread_in"] for m in snap["models"].values()
                    if m.get("tier") == "open" and m.get("spread_in")]
    front_spreads = [m["spread_in"] for m in snap["models"].values()
                     if m.get("tier") == "frontier" and m.get("spread_in")]
    if open_spreads and front_spreads:
        print(f"\nopen-weight input-price spread:  {min(open_spreads):.1f}x - {max(open_spreads):.1f}x")
        print(f"frontier input-price spread:     {min(front_spreads):.1f}x - {max(front_spreads):.1f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
