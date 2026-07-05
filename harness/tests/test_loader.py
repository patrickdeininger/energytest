"""Tests for the fixture dataset loader."""

import json

from harness.data.loader import load_fixture, load_jsonl


def write_jsonl(path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")


def test_loads_all_valid_tasks(tmp_path):
    f = tmp_path / "d.jsonl"
    write_jsonl(f, [
        {"id": "a", "code": "x", "label": 1},
        {"id": "b", "code": "y", "label": 0},
    ])
    tasks = load_fixture(str(f))
    assert len(tasks) == 2
    assert {t.id for t in tasks} == {"a", "b"}


def test_skips_malformed_rows(tmp_path):
    f = tmp_path / "d.jsonl"
    lines = [
        json.dumps({"id": "a", "code": "x", "label": 1}),
        '{"id": "b", "code": "y"}',  # missing label
        "not json at all",
    ]
    f.write_text("\n".join(lines), encoding="utf-8")
    tasks = load_fixture(str(f))
    assert len(tasks) == 1
    assert tasks[0].id == "a"


def _balanced_fixture(path):
    rows = (
        [{"id": f"v{i}", "code": "c", "label": 1} for i in range(10)]
        + [{"id": f"s{i}", "code": "c", "label": 0} for i in range(10)]
    )
    write_jsonl(path, rows)


def test_stratified_sample_balances_labels(tmp_path):
    f = tmp_path / "d.jsonl"
    _balanced_fixture(f)
    tasks = load_fixture(str(f), n=6, stratify_by="label", seed=42)
    assert len(tasks) == 6
    labels = [t.label for t in tasks]
    assert labels.count(1) == 3
    assert labels.count(0) == 3


def test_sample_is_deterministic_with_seed(tmp_path):
    f = tmp_path / "d.jsonl"
    _balanced_fixture(f)
    a = load_fixture(str(f), n=6, stratify_by="label", seed=42)
    b = load_fixture(str(f), n=6, stratify_by="label", seed=42)
    assert [t.id for t in a] == [t.id for t in b]


def test_load_jsonl_maps_configurable_fields_like_primevul(tmp_path):
    f = tmp_path / "pv.jsonl"
    write_jsonl(f, [
        {"idx": 7, "func": "void f(){char b[8];gets(b);}", "target": 1, "cwe": "CWE-242"},
        {"idx": 8, "func": "int add(int a,int b){return a+b;}", "target": 0, "cwe": None},
    ])
    tasks = load_jsonl(
        str(f), code_field="func", label_field="target",
        id_field="idx", cwe_field="cwe", source="primevul",
    )
    by_id = {t.id: t for t in tasks}
    assert set(by_id) == {"7", "8"}
    assert by_id["7"].label == 1 and "gets" in by_id["7"].code
    assert by_id["7"].cwe == "CWE-242"
    assert by_id["8"].label == 0 and by_id["8"].source == "primevul"


def test_load_jsonl_coerces_list_valued_cwe(tmp_path):
    # PrimeVul stores cwe as a list (e.g. [] or ["CWE-120", "CWE-787"]).
    f = tmp_path / "pv.jsonl"
    write_jsonl(f, [
        {"idx": 1, "func": "c", "target": 1, "cwe": ["CWE-120", "CWE-787"]},
        {"idx": 2, "func": "c", "target": 0, "cwe": []},
    ])
    tasks = load_jsonl(str(f), code_field="func", label_field="target", id_field="idx", cwe_field="cwe")
    by_id = {t.id: t for t in tasks}
    assert len(tasks) == 2  # not skipped due to list cwe
    assert by_id["1"].cwe == "CWE-120;CWE-787"
    assert by_id["2"].cwe is None


def test_load_jsonl_skips_rows_missing_mapped_fields(tmp_path):
    f = tmp_path / "pv.jsonl"
    write_jsonl(f, [
        {"idx": 1, "func": "code", "target": 1},
        {"idx": 2, "func": "code"},  # missing target
    ])
    tasks = load_jsonl(str(f), code_field="func", label_field="target", id_field="idx")
    assert [t.id for t in tasks] == ["1"]


def test_load_jsonl_stratified_sample_is_balanced_and_deterministic(tmp_path):
    f = tmp_path / "pv.jsonl"
    rows = (
        [{"idx": f"v{i}", "func": "c", "target": 1} for i in range(10)]
        + [{"idx": f"s{i}", "func": "c", "target": 0} for i in range(10)]
    )
    write_jsonl(f, rows)
    kw = dict(code_field="func", label_field="target", id_field="idx", n=6, stratify_by="label", seed=1)
    a = load_jsonl(str(f), **kw)
    b = load_jsonl(str(f), **kw)
    assert len(a) == 6
    assert [t.label for t in a].count(1) == 3
    assert [t.id for t in a] == [t.id for t in b]
