import ledger_to_exports as lte
import verify_references as vr


def test_exports_from_v1_0_ledger(workspace):
    assert lte.write_exports(workspace / "ledger_v1_0.yaml", "T", workspace) == 0
    assert "@article{pmid29596116," in (workspace / "T_References.bib").read_text()
    assert (workspace / "T_PMIDs.txt").read_text().split() == ["29596116"]


def test_excluded_references_not_exported(workspace):
    vr.verify(workspace / "ledger_a.yaml", workspace / "refs_b.yaml", True, None)
    assert lte.write_exports(workspace / "ledger_a.yaml", "C", workspace) == 0
    pmids = (workspace / "C_PMIDs.txt").read_text().split()
    assert "30000004" not in pmids and "30000005" not in pmids and "30000006" not in pmids
    assert "29596116" in pmids
