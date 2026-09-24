import pytest

import refmatch as rm


@pytest.mark.parametrize("raw", [
    "10.1097/tp.0000000000002191", "https://doi.org/10.1097/TP.0000000000002191", "doi: 10.1097/TP.0000000000002191",
    "http://dx.doi.org/10.1097/TP.0000000000002191", " 10.1097/TP.0000000000002191. ",
])
def test_norm_doi_variants(raw):
    assert rm.norm_doi(raw) == "10.1097/tp.0000000000002191"


def test_norm_title_strips_markup_case_and_translation():
    a = "Letermovir Prophylaxis: A <i>Randomized</i> Trial. [Article in German]"
    assert rm.norm_title(a) == "letermovir prophylaxis a randomized trial"


def test_title_score_same_paper_different_formatting():
    assert rm.title_score("Outcomes after ABO-incompatible kidney transplantation.",
                          "Outcomes after ABO incompatible kidney transplantation") >= rm.TITLE_PASS


def test_title_score_different_paper():
    assert rm.title_score("Valganciclovir dosing in renal impairment",
                          "Hepatitis E infection in heart transplant recipients") < rm.TITLE_REVIEW


def test_title_score_subtitle_truncation():
    full = "Rituximab desensitisation before ABO-incompatible kidney transplantation: a systematic review and meta-analysis"
    short = "Rituximab desensitisation before ABO-incompatible kidney transplantation"
    assert rm.title_score(full, short) >= rm.TITLE_PASS


@pytest.mark.parametrize("a,b", [
    ("Müller T", "Muller T"), ("Müller T", "Mueller T"), ("García-López M", "Garcia Lopez M"),
    ("van der Berg A", "Berg A"), ("O'Neill JP", "ONeill J"), ("kotton cn", "Kotton CN"),
])
def test_surname_forms_match(a, b):
    assert rm.surname_forms(a) & rm.surname_forms(b)


def test_surname_forms_differ():
    assert not (rm.surname_forms("Smith J") & rm.surname_forms("Jones K"))


def base():
    return {"pmid": "1", "doi": "10.1/x", "title": "A trial of something important in transplant",
            "first_author": "Kotton CN", "year": 2020}


def test_compare_pass_with_harmless_differences():
    b = dict(base(), doi="10.1/X", title="A Trial of Something Important in Transplant.", year=2021,
             first_author="kotton c")
    assert rm.compare(base(), b)["status"] == rm.PASS


def test_compare_doi_mismatch_fails():
    assert rm.compare(base(), dict(base(), doi="10.1/y"))["status"] == rm.FAIL


def test_compare_pmid_mismatch_fails():
    assert rm.compare(base(), dict(base(), pmid="2"))["status"] == rm.FAIL


def test_compare_year_gap_is_review():
    result = rm.compare(base(), dict(base(), year=2023))
    assert result["status"] == rm.REVIEW and result["fields"]["year"] == rm.REVIEW


def test_compare_missing_doi_is_review():
    assert rm.compare(base(), dict(base(), doi=None))["status"] == rm.REVIEW


def test_compare_retraction_fails():
    b = dict(base(), publication_types=["Journal Article", "Retracted Publication"])
    assert rm.compare(base(), b)["fields"]["retraction"] == rm.FAIL


def test_identity_only_second_reading():
    a = base()
    ok = rm.compare(a, {"pmid": "1", "doi": "10.1/X"})
    assert ok["status"] == rm.PASS and "title" not in ok["fields"]
    wrong_paper = rm.compare(a, {"pmid": "1", "doi": "10.9/other"})
    assert wrong_paper["status"] == rm.FAIL
    no_doi = rm.compare(a, {"pmid": "1", "doi": None})
    assert no_doi["status"] == rm.REVIEW
    retracted = rm.compare(dict(a, title="[Retracted] A trial"), {"pmid": "1", "doi": "10.1/x"})
    assert retracted["status"] == rm.FAIL


@pytest.mark.parametrize("code,quote,gq,expected", [
    ("1C", "We recommend a target titre of ≤1:8 at transplantation (1C).", None, True),
    ("1C", "We recommend a target titre of ≤1:8 at transplantation.", None, False),   # grade from memory
    ("1C", "We recommend a target titre of ≤1:8.", "Grade 1C", True),                 # grade printed elsewhere
    ("1C", "Monitor HbA1c at 3 months.", None, False),                                # not a whole token
    ("Category I, Grade 1B", "ABOi kidney: Category  I, grade 1B", None, True),       # spacing and case
    ("ungraded", "Offer vaccination before transplant.", None, True),
])
def test_grade_in_source(code, quote, gq, expected):
    grade = {"system": "BTS", "code": code, "display": f"BTS {code}"}
    if gq:
        grade["quote"] = gq
    assert rm.grade_in_source({"source_quote": quote, "grade": grade}) is expected
