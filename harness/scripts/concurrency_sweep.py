"""Measured energy and throughput under batching (paper Sections 4.x and 5.x).

  python -m harness.scripts.concurrency_sweep --model <hf_id> --config <yaml> \
      --levels 1,8,32,64 --idle-w 75.6

RUN ON THE GPU HOST, against an already-serving vLLM instance.

Why this exists. Our published energy measurement was taken at concurrency 1,
which is the honest way to attribute energy to a single request but is also a
low-utilization, energy-pessimistic regime that no production API serves in.
Reviewers 1 and 2 both noted that this weakens the comparison against
FLOP-estimated frontier energy, whose calibration constant assumes batched
datacenter serving. Measuring a concurrency sweep replaces that caveat with a
number, and the same sweep yields the throughput term the self-hosting
break-even model needs.

Measurement note: per-request NVML windows overlap once concurrency exceeds one,
so per-call metering double-counts. This script therefore measures at the RUN
level -- the NVML cumulative energy counter is read once before and once after
each level, and divided by the number of completed tasks. That is the only
attribution that is correct under batching.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

OUT = Path("harness/runs/concurrency_sweep")


def nvml_energy_j(gpu_index: int = 0) -> float:
    """Cumulative energy in joules from the NVML counter (millijoules on Volta+)."""
    import pynvml

    pynvml.nvmlInit()
    h = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)
    return pynvml.nvmlDeviceGetTotalEnergyConsumption(h) / 1000.0


def idle_power_w(gpu_index: int = 0, seconds: float = 20.0) -> float:
    """Measure idle draw directly rather than trusting a configured placeholder."""
    e0, t0 = nvml_energy_j(gpu_index), time.time()
    time.sleep(seconds)
    e1, t1 = nvml_energy_j(gpu_index), time.time()
    return (e1 - e0) / (t1 - t0)


def run_level(config: str, level: int, run_id: str) -> tuple[Path, int]:
    """Run the harness once at a given concurrency, returning its run dir and task count."""
    cfg = json.loads(Path(config).with_suffix(".resolved.json").read_text(encoding="utf-8")) \
        if Path(config).with_suffix(".resolved.json").exists() else None
    cmd = [sys.executable, "-m", "harness.run", "--config", config, "--run-id", run_id]
    env_note = f"HARNESS_CONCURRENCY_OVERRIDE={level}"
    print(f">> {env_note}  {' '.join(cmd)}")
    import os

    env = dict(os.environ, HARNESS_CONCURRENCY_OVERRIDE=str(level))
    subprocess.run(cmd, check=True, env=env)
    run_dir = Path("harness/runs") / run_id
    n = sum(1 for line in (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip())
    _ = cfg
    return run_dir, n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="a local_energy_*.yaml served by vLLM")
    ap.add_argument("--levels", default="1,8,32,64")
    ap.add_argument("--gpu-index", type=int, default=0)
    ap.add_argument("--idle-w", type=float, default=None,
                    help="idle GPU power; measured directly when omitted")
    ap.add_argument("--tag", default="sweep")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    idle = args.idle_w if args.idle_w is not None else idle_power_w(args.gpu_index)
    print(f"idle power: {idle:.1f} W")

    rows = []
    for level in [int(x) for x in args.levels.split(",")]:
        run_id = f"{args.tag}_c{level}-{time.strftime('%Y%m%d-%H%M%S')}"
        e0, t0 = nvml_energy_j(args.gpu_index), time.time()
        run_dir, n = run_level(args.config, level, run_id)
        e1, t1 = nvml_energy_j(args.gpu_index), time.time()

        wall = t1 - t0
        gross = e1 - e0
        active = gross - idle * wall  # subtract what the card would have burned idling
        rows.append({
            "concurrency": level, "n_tasks": n, "wall_s": wall,
            "gross_j": gross, "active_j": active,
            "gross_j_per_task": gross / n if n else None,
            "active_j_per_task": active / n if n else None,
            "throughput_tasks_per_s": n / wall if wall else None,
            "idle_power_w": idle, "run_dir": str(run_dir),
        })
        r = rows[-1]
        print(f"  c={level:3d}  n={n:4d}  wall={wall:7.1f}s  "
              f"active={r['active_j_per_task']:8.1f} J/task  "
              f"thru={r['throughput_tasks_per_s']:6.3f} task/s")

    out = OUT / f"{args.tag}.json"
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")
    if len(rows) > 1 and rows[0]["active_j_per_task"] and rows[-1]["active_j_per_task"]:
        ratio = rows[0]["active_j_per_task"] / rows[-1]["active_j_per_task"]
        print(f"energy per task falls {ratio:.1f}x from concurrency "
              f"{rows[0]['concurrency']} to {rows[-1]['concurrency']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
