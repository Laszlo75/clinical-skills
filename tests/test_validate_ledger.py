import yaml

import validate_ledger as vl


def write(ws, data, name="l.yaml"):
    path = ws / name
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return path


def test_schema_1_0_still_valid(workspace):
    assert vl.validate_ledger(workspace / "ledger_v1_0.yaml") == 0


def test_unverified_fixture_valid(workspace):
    assert vl.validate_ledger(workspace / "ledger_a.yaml") == 0


def test_case_insensitive_duplicate_doi(workspace):
    data = yaml.safe_load((workspace / "ledger_a.yaml").read_text())
    data["references"][1]["doi"] = data["references"][0]["doi"].upper()
    assert vl.validate_ledger(write(workspace, data)) == 1


def test_bad_integrity_status(workspace):
    data = yaml.safe_load((workspace / "ledger_a.yaml").read_text())
    data["references"][0]["integrity"] = {"status": "fail"}
    assert vl.validate_ledger(write(workspace, data)) == 1


def test_1_1_without_integrity_warns(workspace, capsys):
    data = yaml.safe_load((workspace / "ledger_a.yaml").read_text())
    data["metadata"]["ledger_schema_version"] = "1.1"
    assert vl.validate_ledger(write(workspace, data)) == 0
    assert "not independently verified" in capsys.readouterr().out


def test_excluded_needs_reason_and_unique_id(workspace):
    data = yaml.safe_load((workspace / "ledger_a.yaml").read_text())
    data["excluded_references"] = [{"ref_id": 2, "reason": ""}]
    out = vl.validate_ledger(write(workspace, data))
    assert out == 1


def test_future_major_rejected(workspace):
    data = yaml.safe_load((workspace / "ledger_a.yaml").read_text())
    data["metadata"]["ledger_schema_version"] = "2.0"
    assert vl.validate_ledger(write(workspace, data)) == 1


def test_schema_1_2_review_ledger_valid():
    from conftest import FIXTURES
    assert vl.validate_ledger(FIXTURES / "review_ledger.yaml") == 0


def test_bad_certainty_and_questions(workspace):
    from conftest import FIXTURES
    data = yaml.safe_load((FIXTURES / "review_ledger.yaml").read_text())
    data["references"][0]["certainty"] = "probably fine"
    data["references"][1]["questions"] = "Q1"
    data["guidelines"][0]["key_recommendations"][0]["accessed"] = "last week"
    assert vl.validate_ledger(write(workspace, data)) == 1
