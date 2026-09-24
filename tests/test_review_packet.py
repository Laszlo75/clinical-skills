import yaml

import review_packet as rp
from conftest import FIXTURES


def load():
    return (yaml.safe_load((FIXTURES / n).read_text()) for n in
            ("review_ledger.yaml", "protocol_map.yaml", "judgements.yaml"))


def test_packet_holds_only_what_the_reviewer_needs():
    ledger, pmap, judgements = load()
    packet, errors = rp.build(ledger, pmap, judgements, ["J2"])
    assert errors == []
    [j] = packet["judgements"]
    assert j["id"] == "J2" and "second_review" not in j
    assert j["protocol_statement"]["text"]
    assert [e["ref_id"] for e in packet["evidence"]] == [1, 3]          # J2 cites 1 and 3 only
    g = packet["evidence"][0]
    assert g["type"] == "guideline" and g["key_recommendations"][0]["source_quote"]
    assert "authors_full" not in packet["evidence"][1]                 # trimmed paper record
    assert [q["id"] for q in packet["questions"]] == ["Q2"]


def test_mdt_option_evidence_included():
    ledger, pmap, judgements = load()
    judgements[1]["options"] = [{"position": "a", "evidence": [1]}, {"position": "b", "evidence": [2]}]
    packet, _ = rp.build(ledger, pmap, judgements, ["J2"])
    assert [e["ref_id"] for e in packet["evidence"]] == [1, 2, 3]


def test_errors_and_cli(tmp_path, capsys):
    ledger, pmap, judgements = load()
    assert rp.build(ledger, pmap, judgements, ["J9"])[1] == ["unknown judgement J9"]
    judgements[0]["evidence"] = [99]
    assert "cited ref_id 99 is not in the ledger" in rp.build(ledger, pmap, judgements, ["J1"])[1]
    out = tmp_path / "packet.yaml"
    args = ["--ledger", str(FIXTURES / "review_ledger.yaml"), "--map", str(FIXTURES / "protocol_map.yaml"),
            "--judgements", str(FIXTURES / "judgements.yaml"), "--ids", "J1,J2", "--out", str(out)]
    assert rp.main(args) == 0
    assert len(yaml.safe_load(out.read_text())["judgements"]) == 2
    assert "Packet: 2 judgements" in capsys.readouterr().out
