import pytest
import yaml

import format_references as fr
import verify_references as vr


def ledger(ws):
    return yaml.safe_load((ws / "ledger_a.yaml").read_text())


def test_order_and_numbering(workspace):
    entries = fr.format_entries(ledger(workspace), [3, 1, 2])
    assert [(e["number"], e["ref_id"], e["kind"]) for e in entries] == [
        (1, 3, "article"), (2, 1, "guideline"), (3, 2, "article")]


def test_article_vancouver(workspace):
    e = fr.format_entries(ledger(workspace), [2])[0]
    assert e["plain"].startswith(
        "Kotton CN, Kumar D, Caliendo AM, Huprikar S, Chou S, Danziger-Isakov L, et al. "
        "The Third International Consensus Guidelines")
    assert "Transplantation. 2018;102:900-931. PMID: 29596116. doi:10.1097/TP.0000000000002191" in e["plain"]
    assert "*Transplantation*" in e["markdown"]
    assert "[doi:10.1097/TP.0000000000002191](https://doi.org/10.1097/TP.0000000000002191)" in e["markdown"]


def test_short_author_list_has_no_et_al(workspace):
    e = fr.format_entries(ledger(workspace), [3])[0]
    assert e["plain"].startswith("Müller T, Schmidt A. Letermovir")


def test_guideline(workspace):
    e = fr.format_entries(ledger(workspace), [1])[0]
    assert e["plain"].startswith("KDIGO. KDIGO Clinical Practice Guideline")
    assert e["url"] == "https://kdigo.org/guidelines/transplant-candidate/"


def test_unknown_id_rejected(workspace):
    with pytest.raises(ValueError, match="not in the ledger"):
        fr.format_entries(ledger(workspace), [99])


def test_excluded_id_rejected(workspace):
    vr.verify(workspace / "ledger_a.yaml", workspace / "refs_b.yaml", True, None)
    with pytest.raises(ValueError, match="excluded"):
        fr.format_entries(ledger(workspace), [2, 4])


def test_url_form_doi_rendered_bare(workspace):
    data = ledger(workspace)
    data["references"][0]["doi"] = "https://doi.org/10.1097/TP.0000000000002191"
    e = fr.format_entries(data, [2])[0]
    assert e["url"] == "https://doi.org/10.1097/TP.0000000000002191"
    assert "doi:https" not in e["plain"]
