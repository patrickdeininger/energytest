"""The benchmark runner: config -> per-task metered inference -> results.jsonl.

Timestamps/run ids are injected by the caller (CLI), never read inside the loop,
so runs are reproducible and tests are deterministic. Jobs (model x task x rep)
run through a thread pool of size `concurrency` (API calls are I/O-bound); rows
are sorted before writing so output order is deterministic regardless of
completion order. Use concurrency=1 for latency-fidelity runs.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from harness import __version__
from harness.config import RunConfig, make_backend, make_meter
from harness.data.loader import load_fixture, load_jsonl
from harness.meters import compose
from harness.schema import GenParams
from harness.tasks.vuln_detect import build_prompt, parse


def _load_tasks(cfg: RunConfig):
    d = cfg.dataset
    if d.source == "fixture":
        return load_fixture(d.path, n=d.n, stratify_by=d.stratify_by, seed=cfg.seed)
    if d.source == "jsonl":
        return load_jsonl(
            d.path,
            code_field=d.code_field,
            label_field=d.label_field,
            id_field=d.id_field,
            cwe_field=d.cwe_field,
            source="jsonl",
            n=d.n,
            stratify_by=d.stratify_by,
            seed=cfg.seed,
        )
    raise ValueError(f"unknown dataset source: {d.source!r}")


def _make_call(backend, prompt, params):
    # bind loop vars at call-site so the closure is not affected by later iterations
    return lambda: backend.generate(prompt, params)


def run(cfg: RunConfig, *, run_id: str, timestamp: str, git_sha: str = "unknown") -> Path:
    run_dir = Path(cfg.output_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    tasks = _load_tasks(cfg)

    manifest = {
        "run_id": run_id,
        "run_name": cfg.run_name,
        "timestamp": timestamp,
        "git_sha": git_sha,
        "harness_version": __version__,
        "seed": cfg.seed,
        "n_tasks": len(tasks),
        "config": cfg.model_dump(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Resume: rows already on disk (from an interrupted run of the same run_id)
    # are kept and their jobs skipped, so a crash never forces re-spending.
    results_path = run_dir / "results.jsonl"
    completed: set = set()
    if results_path.exists():
        for line in results_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
                completed.add((r["model_id"], r["task_id"], r["rep"]))
            except (json.JSONDecodeError, KeyError):
                continue

    # Build the job list (backend/stack shared per model; both stateless-per-call
    # and thread-safe). Skip anything already completed.
    jobs = []
    for spec in cfg.models:
        backend = make_backend(spec, cfg.seed)
        stack = compose([make_meter(name, spec) for name in cfg.meters])
        for task in tasks:
            prompt = build_prompt(
                task,
                max_code_chars=cfg.gen.max_code_chars,
                variant=cfg.gen.prompt_variant,
            )
            prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]
            for rep in range(cfg.reps):
                if (spec.id, task.id, rep) in completed:
                    continue
                jobs.append((spec, backend, stack, task, prompt, prompt_hash, rep))

    write_lock = threading.Lock()
    fh = results_path.open("a" if completed else "w", encoding="utf-8")

    def run_job(job) -> None:
        spec, backend, stack, task, prompt, prompt_hash, rep = job
        params = GenParams(
            temperature=cfg.gen.temperature,
            max_output_tokens=cfg.gen.max_output_tokens,
            seed=cfg.seed + rep,
        )
        row = {
            "run_id": run_id,
            "model_id": spec.id,
            "task_id": task.id,
            "rep": rep,
            "prompt_hash": prompt_hash,
            "label": task.label,
            "backend": spec.backend,
            "meter_set": cfg.meters,
            "prompt_variant": cfg.gen.prompt_variant,
            "max_output_tokens": cfg.gen.max_output_tokens,
        }
        try:
            resp, metrics = stack.measure(_make_call(backend, prompt, params))
            pred = parse(resp.text)
            row.update({
                "prediction": pred.label,
                "correct": bool(pred.label == task.label),
                "parsed_ok": pred.parsed_ok,
                "raw_output": resp.text[:2000],
                "input_tokens": resp.input_tokens,
                "output_tokens": resp.output_tokens,
                "confidence": pred.confidence,
                "provider": resp.provider,
                "attempts": resp.attempts,
                "error": None,
            })
            row.update(metrics)
        except Exception as exc:  # one failed call must not abort a long run
            row.update({
                "prediction": 0,
                "correct": False,
                "parsed_ok": False,
                "raw_output": "",
                "error": f"{type(exc).__name__}: {str(exc)[:200]}",
            })
        # Incremental, flushed write so a crash never loses completed rows.
        line = json.dumps(row)
        with write_lock:
            fh.write(line + "\n")
            fh.flush()

    try:
        if cfg.concurrency > 1:
            with ThreadPoolExecutor(max_workers=cfg.concurrency) as ex:
                list(ex.map(run_job, jobs))
        else:
            for job in jobs:
                run_job(job)
    finally:
        fh.close()

    return run_dir
