import copy

import yaml

import merge_ledgers as ml
import validate_ledger as vl
from conftest import FIXTURES


def parts():
    base = yaml.safe_load((FIXTURES / "review_ledger.yaml").read_text())
    base.pop("excluded_references")
    for r in base["references"]:
        r.pop("integrity")
    a, b = copy.deepcopy(base), copy.deepcopy(base)
    a["references"] = [base["references"][0]]
    a["metadata"]["questions"] = [base["metadata"]["questions"][0]]
    b["references"] = [dict(base["references"][0], pmid=" 30000102 ", questions=["Q2"]),
                       base["references"][1]]
    b["metadata"]["questions"] = [base["metadata"]["questions"][1]]
    b["metadata"]["search_date"] = "2026-09-24"
    b["guidelines"][0]["key_recommendations"].append(
        {"text": "Rituximab 375 mg/m2", "grade": {"system": "BTS", "code": "2C", "display": "BTS Grade 2C"}})
    return a, b


def test_merge_deduplicates_and_unions():
    merged = ml.merge(list(parts()))
    assert len(merged["guidelines"]) == 1 and len(merged["references"]) == 2
    assert merged["references"][0]["questions"] == ["Q1", "Q2"]
    assert len(merged["guidelines"][0]["key_recommendations"]) == 2
    assert [q["id"] for q in merged["metadata"]["questions"]] == ["Q1", "Q2"]
    assert merged["metadata"]["search_date"] == "2026-09-24"
    ids = [e["ref_id"] for e in merged["guidelines"] + merged["references"]]
    assert ids == [1, 2, 3]


def test_merged_ledger_validates(tmp_path):
    out = tmp_path / "merged.yaml"
    out.write_text(yaml.safe_dump(ml.merge(list(parts())), allow_unicode=True))
    assert vl.validate_ledger(out) == 0


def test_guideline_part_merges_with_literature_parts(tmp_path):
    a, b = parts()
    g = copy.deepcopy(a)
    g["references"] = []
    g["metadata"].update(ledger_schema_version="1.3", model_id="opus (effort medium)")
    g["guidelines"][0]["currency"] = {"status": "current", "checked_on": "2026-09-24"}
    a["guidelines"] = b["guidelines"] = []
    merged = ml.merge([g, a, b])
    assert len(merged["guidelines"]) == 1 and merged["guidelines"][0]["ref_id"] == 1
    assert [r["ref_id"] for r in merged["references"]] == [2, 3]
    assert merged["metadata"]["ledger_schema_version"] == "1.3"
    assert merged["metadata"]["model_id"].count(";") == 1
    out = tmp_path / "merged.yaml"
    out.write_text(yaml.safe_dump(merged, allow_unicode=True))
    assert vl.validate_ledger(out) == 0


def test_unretrieved_guideline_dropped_once_supplied():
    a, b = parts()
    missing = {"organisation": "British Society for Haematology", "title": "FFP and cryoprecipitate",
               "year": 2018, "importance": "key", "questions": ["Q2"]}
    other = {"organisation": "ASFA", "title": "Apheresis guidelines", "importance": "supporting"}
    a["metadata"]["unretrieved_guidelines"] = [missing, other]
    merged = ml.merge([a, b])
    assert [u["organisation"] for u in merged["metadata"]["unretrieved_guidelines"]] == [
        "British Society for Haematology", "ASFA"]
    uploaded = copy.deepcopy(b)
    uploaded["references"] = []
    uploaded["guidelines"] = [dict(b["guidelines"][0], organisation="British Society for Haematology",
                                   title="FFP and Cryoprecipitate", year=2018, source_file="bsh_ffp.pdf")]
    merged = ml.merge([a, b, uploaded])
    assert [u["organisation"] for u in merged["metadata"]["unretrieved_guidelines"]] == ["ASFA"]
    assert any(g.get("source_file") == "bsh_ffp.pdf" for g in merged["guidelines"])
