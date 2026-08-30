"""Assemble everything MDPI needs for the round-1 resubmission.

  python -m harness.scripts.build_resubmission

Writes into MDPI_Review_Round1/submission_MDPI/:

  manuscript.pdf              the revised manuscript
  manuscript_marked.pdf       latexdiff against the SUBMITTED version, so the
                              editor can see every change without diffing sources
  manuscript_latex.zip        sources to rebuild manuscript.pdf from scratch
  figures.zip                 figures at submission resolution
  reproduction.zip            harness, configs, per-run results, analysis scripts,
                              and a README mapping each script to the table it produces
  cover_letter.{md,docx}      to the editors
  response_reviewer_{1,2,3}.{md,docx}

The marked-changes baseline is the git commit that was submitted, not the working
tree, so the diff shows what the reviewers would see changed rather than what
happened to be edited most recently.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(".")
OUT = Path("MDPI_Review_Round1/submission_MDPI")
SUBMITTED_REV = "22fc67f"          # the commit reviewed in round 1

LETTERS = ["cover_letter", "response_reviewer_1", "response_reviewer_2",
           "response_reviewer_3"]

# Mirrors build_submission_package._skip: never ship credentials, caches,
# checkpoints, serving logs, the redistributed corpus, or scratch runs.
def _skip(p: Path) -> bool:
    parts = set(p.parts)
    return (
        p.name == ".env"
        or "__pycache__" in parts
        or ".pytest_cache" in parts
        or ".git" in parts
        or "ckpt" in parts
        or p.suffix in {".pyc", ".pyo"}
        or any(x.startswith("checkpoint-") for x in p.parts)
        or p.name.startswith("vllm_")
        or p.match("harness/data/primevul/*")
        or any(x.endswith(("_preflight", "_preflight2", "_diag")) for x in p.parts)
    )


def add_tree(zf: zipfile.ZipFile, src: Path, prefix: str = "") -> int:
    n = 0
    for p in sorted(src.rglob("*")):
        if p.is_dir() or _skip(p):
            continue
        arc = (Path(prefix) / p.relative_to(src)) if prefix else p
        zf.write(p, arc.as_posix())
        n += 1
    return n


def run(cmd, **kw) -> subprocess.CompletedProcess:
    # text=True alone decodes with the Windows ANSI codepage, which cannot read
    # the manuscript's UTF-8 (em dashes, non-breaking spaces). Force it.
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", **kw)


def build_marked_pdf() -> bool:
    """latexdiff the submitted revision against the working tree.

    Tables are treated as picture environments: latexdiff cannot mark up inside a
    tabular without emitting \\noalign in illegal positions, and half the tables
    here are new. A whole table marked as changed is the correct granularity for a
    reviewer anyway.
    """
    base = Path("_base_submitted.tex")
    got = run(["git", "show", f"{SUBMITTED_REV}:main.tex"])
    if got.returncode != 0:
        print(f"  cannot read {SUBMITTED_REV}:main.tex -- skipping marked copy")
        return False
    base.write_text(got.stdout, encoding="utf-8")

    diff = run([
        "latexdiff", "--encoding=utf8",
        "--append-safecmd=cmidrule,multicolumn,adjustwidth,includegraphics",
        "--config", r"PICTUREENV=(?:picture|DIFnomarkup|tabular|tabularx|table)[\w\d*@]*",
        "--exclude-textcmd=section,subsection,subsubsection",
        str(base), "main.tex",
    ])
    if diff.returncode != 0 or not diff.stdout.strip():
        print("  latexdiff failed -- skipping marked copy")
        base.unlink(missing_ok=True)
        return False
    Path("diff_main.tex").write_text(diff.stdout, encoding="utf-8")

    build = run(["latexmk", "-pdf", "-interaction=nonstopmode", "diff_main.tex"])
    ok = Path("diff_main.pdf").exists()
    if ok:
        shutil.copy("diff_main.pdf", OUT / "manuscript_marked.pdf")
        # Count change HUNKS, not macro occurrences: latexdiff emits several
        # \DIFadd{} macros per contiguous insertion but exactly one
        # \DIFaddbegin, so the begin markers are the number of distinct changes.
        adds = diff.stdout.count(r"\DIFaddbegin")
        dels = diff.stdout.count(r"\DIFdelbegin")
        print(f"  manuscript_marked.pdf  ({adds} insertions / {dels} deletions)")
    else:
        print("  marked PDF did not compile:", build.stdout[-300:])
    base.unlink(missing_ok=True)
    return ok


def convert_letters() -> None:
    if not shutil.which("pandoc"):
        print("  pandoc not found -- .docx not generated")
        return
    for name in LETTERS:
        md = OUT / f"{name}.md"
        if not md.exists():
            print(f"  {md} missing -- skipped")
            continue
        r = run(["pandoc", str(md), "-o", str(OUT / f"{name}.docx"),
                 "--from", "markdown", "--standalone"])
        print(f"  {name}.docx" if r.returncode == 0 else
              f"  {name}.docx FAILED: {r.stderr[:200]}")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    if not Path("main.pdf").exists():
        print("main.pdf missing -- build the manuscript first")
        return 1
    shutil.copy("main.pdf", OUT / "manuscript.pdf")
    print(f"  manuscript.pdf")

    build_marked_pdf()

    with zipfile.ZipFile(OUT / "manuscript_latex.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for f in ("main.tex", "bibliography.bib", "main.bbl", "main.pdf"):
            if Path(f).exists():
                zf.write(f, f)
        n = add_tree(zf, Path("Definitions"), "Definitions")
        n += add_tree(zf, Path("figures"), "figures")
        zf.writestr("BUILD.txt",
                    "Rebuild:\n  latexmk -pdf main.tex\n\n"
                    "Requires the MDPI class in Definitions/ (included) and a TeX\n"
                    "distribution with latexmk. main.bbl is included so the build\n"
                    "succeeds without re-running BibTeX.\n")
    print(f"  manuscript_latex.zip")

    with zipfile.ZipFile(OUT / "figures.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        n = sum(1 for p in sorted(Path("figures").iterdir())
                if p.is_file() and not _skip(p) and (zf.write(p, p.name) or True))
    print(f"  figures.zip  ({n} files)")

    from harness.scripts.reproduction_readme import README

    with zipfile.ZipFile(OUT / "reproduction.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        n = add_tree(zf, Path("harness"), "harness")
        n += add_tree(zf, Path("figures"), "figures")
        for f in ("pyproject.toml", ".env.example", "main.pdf", "LICENSE"):
            if Path(f).exists():
                zf.write(f, f)
                n += 1
        zf.writestr("README.md", README)
        n += 1
    size = (OUT / "reproduction.zip").stat().st_size / 1e6
    print(f"  reproduction.zip  ({n} files, {size:.1f} MB)")

    convert_letters()

    print(f"\ncontents of {OUT}:")
    for p in sorted(OUT.iterdir()):
        print(f"  {p.name:34s} {p.stat().st_size/1e6:8.2f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
