"""Re-derive predictions from saved raw_output with the current parser.

  python -m harness.scripts.reparse harness/runs/<run>/results.jsonl [...]

The verdict parser was fixed to honor the leading YES/NO token (reasoning-mode
outputs mention marker words throughout their analysis, which the old body-scan
misread). Because every row stores its full raw_output, we can re-derive
prediction/parsed_ok/correct offline without re-calling any API. Rewrites each
file in place (raw_output is untouched) and reports how many predictions changed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from harness.tasks.vuln_detect import parse


def reparse_file(path: str) -> tuple[int, int]:
    rows = [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    changed = 0
    for r in rows:
        new = parse(str(r.get("raw_output") or ""))
        old_pred, old_ok = r.get("prediction"), r.get("parsed_ok")
        r["prediction"] = new.label
        r["parsed_ok"] = new.parsed_ok
        r["correct"] = bool(new.parsed_ok and new.label == r["label"])
        if new.parsed_ok != old_ok or (new.parsed_ok and new.label != old_pred):
            changed += 1
    with Path(path).open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    return changed, len(rows)


def main(argv) -> int:
    if not argv:
        print(__doc__)
        return 1
    for path in argv:
        changed, n = reparse_file(path)
        print(f"{path}: reparsed {n} rows, {changed} predictions changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
