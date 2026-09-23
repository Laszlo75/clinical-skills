import csv

import yaml

import verify_references as vr


def run(ws, apply=True):
    return vr.verify(ws / "ledger_a.yaml", ws / "refs_b.yaml", apply, None)


def statuses(ws):
    with (ws / ".clinical-evidence" / "verification_report.csv").open() as f:
        return {int(r["ref_id"]): r for r in csv.DictReader(f)}


def test_report_statuses(workspace):
    assert run(workspace, apply=False) == 0
    rows = statuses(workspace)
    assert {k: v["status"] for k, v in rows.items()} == {
        2: "pass", 3: "pass", 4: "fail", 5: "fail", 6: "fail", 7: "review", 8: "review", 9: "review",
    }
    assert "different paper" in rows[4]["notes"]
    assert rows[5]["doi_check"] == "fail"
    assert rows[6]["retraction_check"] == "fail"


def test_dry_run_leaves_ledger_untouched(workspace):
    before = (workspace / "ledger_a.yaml").read_text()
    run(workspace, apply=False)
    assert (workspace / "ledger_a.yaml").read_text() == before


def test_apply_moves_failures_and_stamps_integrity(workspace):
    assert run(workspace) == 0
    ledger = yaml.safe_load((workspace / "ledger_a.yaml").read_text())
    assert ledger["metadata"]["ledger_schema_version"] == "1.1"
    kept = {r["ref_id"]: r for r in ledger["references"]}
    assert set(kept) == {2, 3, 7, 8, 9}
    assert kept[2]["integrity"]["status"] == "pass"
    assert kept[7]["integrity"]["status"] == "review"
    assert {e["ref_id"] for e in ledger["excluded_references"]} == {4, 5, 6}
    assert all(e["reason"] for e in ledger["excluded_references"])


def test_applied_ledger_validates(workspace, capsys):
    import validate_ledger

    run(workspace)
    assert validate_ledger.validate_ledger(workspace / "ledger_a.yaml") == 0


def test_missing_second_reading_is_bad_input(workspace):
    assert vr.verify(workspace / "ledger_a.yaml", workspace / "nope.yaml", True, None) == 1


def test_missing_ledger(workspace):
    assert vr.verify(workspace / "nope.yaml", workspace / "refs_b.yaml", True, None) == 2


def test_not_found_pmid_fails(workspace):
    b = yaml.safe_load((workspace / "refs_b.yaml").read_text())
    b.append({"pmid": "30000009", "not_found": True})
    (workspace / "refs_b.yaml").write_text(yaml.safe_dump(b))
    run(workspace, apply=False)
    assert statuses(workspace)[9]["status"] == "fail"


def test_agreed_url_form_doi_is_stored_bare(workspace):
    ledger = yaml.safe_load((workspace / "ledger_a.yaml").read_text())
    ledger["references"][0]["doi"] = "https://doi.org/10.1097/tp.0000000000002191"
    (workspace / "ledger_a.yaml").write_text(yaml.safe_dump(ledger, sort_keys=False))
    run(workspace)
    kept = yaml.safe_load((workspace / "ledger_a.yaml").read_text())["references"]
    assert kept[0]["doi"] == "10.1097/TP.0000000000002191"


def test_apply_never_downgrades_schema(workspace):
    ledger = yaml.safe_load((workspace / "ledger_a.yaml").read_text())
    ledger["metadata"]["ledger_schema_version"] = "1.2"
    (workspace / "ledger_a.yaml").write_text(yaml.safe_dump(ledger, sort_keys=False))
    run(workspace)
    assert yaml.safe_load((workspace / "ledger_a.yaml").read_text())["metadata"]["ledger_schema_version"] == "1.2"
