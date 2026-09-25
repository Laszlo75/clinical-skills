from datetime import date

import yaml

import guideline_cache as gc
from conftest import FIXTURES

TODAY = date(2026, 9, 24)


def ledger(**overrides):
    data = yaml.safe_load((FIXTURES / "review_ledger.yaml").read_text())
    data["guidelines"][0].update(overrides)
    return data


def put(tmp_path, data, today=TODAY):
    path = tmp_path / "ledger.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True))
    return gc.main(["put", str(tmp_path / "cache"), str(path)], today=today)


def get(tmp_path, today=TODAY, max_age=90):
    out = tmp_path / "hits.yaml"
    assert gc.main(["get", str(tmp_path / "cache"), "--out", str(out),
                    "--max-age-days", str(max_age)], today=today) == 0
    return yaml.safe_load(out.read_text())["guidelines"]


def test_round_trip_strips_run_fields_and_stamps_date(tmp_path):
    assert put(tmp_path, ledger()) == 0
    [g] = get(tmp_path)
    assert g["organisation"] == "BTS" and g["cached_on"] == "2026-09-24"
    assert "ref_id" not in g and "questions" not in g
    assert g["key_recommendations"][0]["source_quote"].startswith("We recommend")


def test_max_age_filters_stale_entries(tmp_path):
    put(tmp_path, ledger(), today=date(2026, 5, 1))
    assert get(tmp_path, max_age=90) == []                    # 146 days old
    assert len(get(tmp_path, max_age=200)) == 1


def test_recommendations_accumulate_across_topics(tmp_path):
    put(tmp_path, ledger())
    extra = {"text": "Rituximab 375 mg/m2", "grade": {"system": "BTS", "code": "2C", "display": "BTS Grade 2C"}}
    data = ledger()
    data["guidelines"][0]["key_recommendations"] = [extra]
    put(tmp_path, data)
    [g] = get(tmp_path)
    assert {r["text"] for r in g["key_recommendations"]} == {
        "Target IgG titre of 1:8 or less at transplantation", "Rituximab 375 mg/m2"}


def test_reuse_does_not_refresh_the_date(tmp_path):
    put(tmp_path, ledger(), today=date(2026, 8, 1))
    [cached] = get(tmp_path)
    data = ledger()
    data["guidelines"][0] = {**cached, "ref_id": 1}           # reused unread this run
    put(tmp_path, data)
    assert get(tmp_path)[0]["cached_on"] == "2026-08-01"
    put(tmp_path, ledger())                                    # re-read: no cached_on
    assert get(tmp_path)[0]["cached_on"] == "2026-09-24"


def test_new_edition_is_a_separate_entry(tmp_path):
    put(tmp_path, ledger())
    put(tmp_path, ledger(year=2027))
    assert sorted(g["year"] for g in get(tmp_path)) == [2016, 2027]


def test_clear_and_missing_cache(tmp_path, capsys):
    assert get(tmp_path) == []                                 # no cache yet: a plain miss
    put(tmp_path, ledger(), today=date(2026, 1, 1))
    put(tmp_path, ledger(year=2027))
    gc.main(["clear", str(tmp_path / "cache"), "--older-than-days", "90"], today=TODAY)
    assert [g["year"] for g in get(tmp_path, max_age=999)] == [2027]
    gc.main(["list", str(tmp_path / "cache")], today=TODAY)
    assert "checked 0 days ago" in capsys.readouterr().out
    gc.main(["clear", str(tmp_path / "cache")], today=TODAY)
    assert get(tmp_path, max_age=999) == []


def test_unread_guideline_is_never_cached_or_reused(tmp_path, capsys):
    """An empty entry (a guideline that couldn't be read) must stay a cache miss, so the
    agents try it again and ask the researcher to supply it."""
    data = ledger()
    data["guidelines"].append({**data["guidelines"][0], "ref_id": 99, "organisation": "BSH",
                               "title": "FFP and cryoprecipitate", "key_recommendations": []})
    put(tmp_path, data)
    assert "1 with no recommendations not cached" in capsys.readouterr().out
    assert [g["organisation"] for g in get(tmp_path)] == ["BTS"]
    (tmp_path / "cache" / "legacy.yaml").write_text(yaml.safe_dump(   # an older cache's empty entry
        {"organisation": "EASL", "title": "HBV", "year": 2025, "cached_on": "2026-09-24",
         "key_recommendations": []}))
    assert [g["organisation"] for g in get(tmp_path)] == ["BTS"]


def test_damaged_entry_is_a_miss(tmp_path):
    put(tmp_path, ledger())
    (tmp_path / "cache" / "broken.yaml").write_text("{not: [valid")
    assert len(get(tmp_path)) == 1
