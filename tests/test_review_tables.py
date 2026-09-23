import csv
import shutil

import pytest
import yaml

import review_tables as rt
from conftest import FIXTURES


@pytest.fixture
def review(tmp_path):
    for name in ("review_ledger.yaml", "protocol_map.yaml", "judgements.yaml"):
        shutil.copy(FIXTURES / name, tmp_path / name)
    return tmp_path


def load(ws):
    return (yaml.safe_load((ws / n).read_text()) for n in
            ("review_ledger.yaml", "protocol_map.yaml", "judgements.yaml"))


def run(ws, monkeypatch, *extra):
    argv = ["review_tables.py", "--ledger", str(ws / "review_ledger.yaml"),
            "--map", str(ws / "protocol_map.yaml"), "--judgements", str(ws / "judgements.yaml"),
            "--prefix", "ABOi", "--outdir", str(ws), *extra]
    monkeypatch.setattr("sys.argv", argv)
    return rt.main()


def rows(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def test_happy_path_outputs(review, monkeypatch):
    assert run(review, monkeypatch) == 0
    trace = rows(review / "ABOi_Traceability.csv")
    assert [r["judgement"] for r in trace] == ["J1", "J2"]
    assert trace[1]["verdict"] == "Major update" and trace[1]["safety"] == "yes"
    assert trace[1]["evidence_citations"] == "BTS 2016; Müller T 2022"
    evidence = rows(review / "ABOi_Evidence_Table.csv")
    assert [int(r["ref_id"]) for r in evidence] == [1, 2, 3]
    assert evidence[1]["study_design"] == "Systematic review and meta-analysis"
    assert evidence[1]["cited_in"] == "J1" and evidence[1]["verification"] == "pass"
    assert "BTS Grade 1C" in evidence[0]["key_finding"]
    md = (review / ".clinical-evidence" / "traceability.md").read_text()
    assert md.startswith("| # | Section") and "J2" in md


def test_xlsx_written_when_openpyxl_available(review, monkeypatch):
    openpyxl = pytest.importorskip("openpyxl")
    run(review, monkeypatch)
    wb = openpyxl.load_workbook(review / "ABOi_Evidence_Table.xlsx")
    assert wb.sheetnames == ["Evidence", "Traceability"]


def test_register_row_and_header_migration(review, monkeypatch):
    reg = review / "clinical-evidence-register.csv"
    old_header = rt.REGISTER_COLUMNS[:13] + ["mdt_outcome", "appraiser", "notes"]
    with reg.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=old_header)
        w.writeheader()
        w.writerow({"protocol_name": "Old review", "mdt_outcome": "accepted"})
    assert run(review, monkeypatch, "--register", str(reg), "--model-id", "m", "--skill-version", "2.2.0") == 0
    data = rows(reg)
    assert data[0]["protocol_name"] == "Old review" and data[0]["mdt_outcome"] == "accepted"
    new = data[1]
    assert new["recommendations_major_update"] == "1" and new["recommendations_minor_update"] == "1"
    assert new["references_excluded"] == "1" and new["second_review_disagreements"] == "1"
    assert new["total_references"] == "3" and new["guidelines_consulted"] == "BTS 2016"


@pytest.mark.parametrize("mutate,message", [
    (lambda l, m, j: j.pop(0), "statement S1 has no judgement"),
    (lambda l, m, j: j[0].update(evidence=[4]), "excluded by verification"),
    (lambda l, m, j: j[0].update(evidence=[99]), "not in the ledger"),
    (lambda l, m, j: j[0].update(verdict="partly"), "verdict must be one of"),
    (lambda l, m, j: j[1]["second_review"].update(resolution=""), "a resolution is required"),
    (lambda l, m, j: j[0].update(statement=None), "only new_addition"),
    (lambda l, m, j: m["statements"][0].update(questions=["Q9"]), "unknown question Q9"),
])
def test_consistency_errors(review, monkeypatch, capsys, mutate, message):
    ledger, pmap, judgements = load(review)
    mutate(ledger, pmap, judgements)
    for name, data in (("review_ledger.yaml", ledger), ("protocol_map.yaml", pmap),
                       ("judgements.yaml", judgements)):
        (review / name).write_text(yaml.safe_dump(data, allow_unicode=True))
    assert run(review, monkeypatch) == 1
    assert message in capsys.readouterr().out
    assert not (review / "ABOi_Traceability.csv").exists()


def test_new_addition_without_statement_allowed(review, monkeypatch):
    ledger, pmap, judgements = load(review)
    judgements.append({"id": "J3", "statement": None, "question": "Q2", "verdict": "new_addition",
                       "recommendation": "Add post-transplant titre monitoring.", "evidence": [3],
                       "confidence": "low", "second_review": {"status": "agree"}})
    (review / "judgements.yaml").write_text(yaml.safe_dump(judgements, allow_unicode=True))
    assert run(review, monkeypatch) == 0


def test_second_review_warning_only_for_practice_changing(review, monkeypatch, capsys):
    ledger, pmap, judgements = load(review)
    judgements[0].pop("second_review")                      # minor_update: no warning
    judgements[1].pop("second_review")                      # major_update + safety: warning
    (review / "judgements.yaml").write_text(yaml.safe_dump(judgements, allow_unicode=True))
    assert run(review, monkeypatch) == 0
    out = capsys.readouterr().out
    assert "J2: practice-changing but not second-reviewed" in out and "J1:" not in out
