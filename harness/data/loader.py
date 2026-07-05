"""Dataset loading.

`load_fixture` reads the pilot fixture format (`code`/`label`). `load_jsonl` is
the general loader with configurable field names, used for real datasets such as
PrimeVul (`func`/`target`/`idx`) and SecVulEval. Both skip malformed rows and
share a deterministic stratified sampler.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict

from pydantic import ValidationError

from harness.schema import Task


def _sample(tasks: list[Task], n: int | None, stratify_by: str | None, seed: int) -> list[Task]:
    if n is None:
        return tasks
    rng = random.Random(seed)
    if stratify_by:
        groups: dict = defaultdict(list)
        for t in tasks:
            groups[getattr(t, stratify_by)].append(t)
        per = n // len(groups) if groups else 0
        selected: list[Task] = []
        for key in sorted(groups):
            group = sorted(groups[key], key=lambda t: t.id)
            selected.extend(rng.sample(group, min(per, len(group))))
        return selected[:n]
    ordered = sorted(tasks, key=lambda t: t.id)
    return rng.sample(ordered, min(n, len(ordered)))


def load_jsonl(
    path: str,
    *,
    code_field: str = "code",
    label_field: str = "label",
    id_field: str = "id",
    cwe_field: str | None = None,
    source: str = "jsonl",
    n: int | None = None,
    stratify_by: str | None = None,
    seed: int = 0,
) -> list[Task]:
    """Load Tasks from a JSONL file with configurable field names.

    Rows missing a mapped field, with an unparseable label, or that are not valid
    JSON are skipped. Sampling is deterministic in `seed`.
    """
    tasks: list[Task] = []
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                cwe_val = obj.get(cwe_field) if cwe_field else None
                if isinstance(cwe_val, list):  # PrimeVul stores cwe as a list
                    cwe_val = ";".join(str(x) for x in cwe_val) if cwe_val else None
                tasks.append(
                    Task(
                        id=str(obj[id_field]) if id_field in obj else str(i),
                        code=obj[code_field],
                        label=int(obj[label_field]),
                        cwe=cwe_val,
                        source=source,
                    )
                )
            except (json.JSONDecodeError, KeyError, ValidationError, TypeError, ValueError):
                continue
    return _sample(tasks, n, stratify_by, seed)


def load_fixture(
    path: str,
    n: int | None = None,
    stratify_by: str | None = None,
    seed: int = 0,
) -> list[Task]:
    """Load Tasks from a pilot fixture (`code`/`label`), skipping malformed rows."""
    tasks: list[Task] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                tasks.append(Task(**json.loads(line)))
            except (json.JSONDecodeError, ValidationError, TypeError):
                continue
    return _sample(tasks, n, stratify_by, seed)
