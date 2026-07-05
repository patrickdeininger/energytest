"""CLI entry point: `python -m harness.run --config configs/pilot_dryrun.yaml`.

Generates the run id / timestamp / git SHA here (the entry point), then delegates
to the pure, deterministic runner.
"""

from __future__ import annotations

import argparse
import datetime
import subprocess

from harness.config import load_config
from harness.report.report import build_report
from harness.runner import run


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except Exception:
        return "unknown"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run the vuln-detection benchmark harness.")
    ap.add_argument("--config", required=True, help="Path to a run config YAML.")
    ap.add_argument("--run-id", default=None,
                    help="Reuse an existing run id to RESUME an interrupted run.")
    args = ap.parse_args(argv)

    try:
        from dotenv import load_dotenv

        load_dotenv()  # pick up API keys from .env for api backends
    except ImportError:
        pass

    cfg = load_config(args.config)
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    run_id = args.run_id or f"{cfg.run_name}-{now.strftime('%Y%m%d-%H%M%S')}"

    run_dir = run(cfg, run_id=run_id, timestamp=timestamp, git_sha=_git_sha())
    report = build_report(run_dir)

    print(f"Run complete: {run_dir}")
    print(report["metrics"].to_string(index=False))
    print(f"\nPlots: {', '.join(p.name for p in report['plots'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
