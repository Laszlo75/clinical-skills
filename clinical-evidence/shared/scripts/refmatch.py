"""Tolerant comparison of bibliographic records.

Two independent readings of the same paper (e.g. two PubMed MCP transcriptions, or
PubMed vs Crossref) legitimately differ in capitalisation, diacritics, HTML markup,
bracketed translations, and epub-vs-print year. These must not fail verification.
What *must* fail is a different identifier or a different paper.

Rules (see compare()):
    PMID          equal → pass            differ → fail
    DOI           normalised equal → pass one side missing → review   differ → fail
    title         score ≥ 0.90 → pass     0.75–0.90 → review          < 0.75 → fail
    first author  surname forms overlap → pass                        else → review
    year          |Δ| ≤ 1 → pass          else → review
    retracted     either side flags retraction → fail

Overall status is the worst field status. Standard library only.
"""

from __future__ import annotations

import html
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any

PASS, REVIEW, FAIL = "pass", "review", "fail"
_RANK = {PASS: 0, REVIEW: 1, FAIL: 2}

TITLE_PASS = 0.90
TITLE_REVIEW = 0.75

RETRACTION_MARKERS = ("[retracted]", "[retraction of:", "retracted:")
RETRACTION_PUBTYPES = {"retracted publication", "retraction of publication"}

_PARTICLES = {
    "van", "von", "de", "der", "den", "del", "della", "la", "le", "da", "dos",
    "das", "di", "du", "ter", "ten", "el", "al",
}
_GERMAN_FOLD = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def worst(*statuses: str) -> str:
    return max(statuses, key=lambda s: _RANK[s]) if statuses else PASS


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _ascii_fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def bare_doi(doi: Any) -> str:
    """DOI without URL/"doi:" prefix or trailing punctuation, original casing kept."""
    if _blank(doi):
        return ""
    s = str(doi).strip()
    s = re.sub(r"^(?:https?://)?(?:dx\.)?doi\.org/", "", s, flags=re.I)
    s = re.sub(r"^doi:\s*", "", s, flags=re.I)
    return s.strip().rstrip(".,;")


def norm_doi(doi: Any) -> str:
    """Canonical DOI for comparison: bare, trimmed, lower-case (DOIs are case-insensitive)."""
    return bare_doi(doi).lower()


def norm_pmid(pmid: Any) -> str:
    return "" if _blank(pmid) else str(pmid).strip()


def norm_title(title: Any) -> str:
    if _blank(title):
        return ""
    s = html.unescape(str(title))
    s = re.sub(r"<[^>]+>", " ", s)  # <i>, <sup>, MathML …
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\[[^\]]*\]", " ", s)  # bracketed translations / [Retracted]
    s = _ascii_fold(s).casefold()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def title_score(a: Any, b: Any) -> float:
    """Similarity in [0, 1]; tolerant of subtitles or truncation on one side."""
    na, nb = norm_title(a), norm_title(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    ratio = SequenceMatcher(None, na, nb).ratio()
    ta, tb = set(na.split()), set(nb.split())
    if min(len(ta), len(tb)) >= 5:
        containment = len(ta & tb) / min(len(ta), len(tb))
        # Containment alone would let a short title match inside a long unrelated one;
        # require the shorter title to be a substantial part of the longer.
        if min(len(ta), len(tb)) / max(len(ta), len(tb)) >= 0.5:
            ratio = max(ratio, containment)
    return ratio


def surname_forms(author: Any) -> set[str]:
    """Comparable forms of the surname in 'Kotton CN' / 'García-López M' / 'van der Berg A'."""
    if _blank(author):
        return set()
    raw = html.unescape(str(author)).strip()
    tokens = raw.replace(",", " ").split()
    # Drop trailing initials (all-caps tokens of ≤3 letters, optionally dotted).
    while len(tokens) > 1 and re.fullmatch(r"(?:[A-Z]\.?){1,3}", tokens[-1]):
        tokens.pop()
    words = [t for t in tokens if t.casefold() not in _PARTICLES] or tokens
    forms = set()
    # Whole name (handles multi-word surnames) and the first word alone (handles
    # initials that were not recognised, e.g. lower-case "kotton cn").
    for candidate in {"".join(words), words[0]}:
        for variant in (candidate, candidate.casefold().translate(_GERMAN_FOLD)):
            compact = re.sub(r"[^a-z]", "", _ascii_fold(variant).casefold())
            if compact:
                forms.add(compact)
    return forms


def _year(value: Any) -> int | None:
    m = re.search(r"\d{4}", str(value)) if value is not None else None
    return int(m.group()) if m else None


def is_retracted(record: dict) -> bool:
    if record.get("retracted") is True:
        return True
    title = str(record.get("title") or "").casefold()
    if any(m in title for m in RETRACTION_MARKERS):
        return True
    pubtypes = record.get("publication_types") or []
    if isinstance(pubtypes, str):
        pubtypes = [pubtypes]
    return any(str(p).strip().casefold() in RETRACTION_PUBTYPES for p in pubtypes)


def compare(a: dict, b: dict) -> dict:
    """Compare record `a` (ledger) with independent record `b`.

    Returns {"status": ..., "fields": {field: status}, "title_score": float, "notes": [..]}.
    """
    fields: dict[str, str] = {}
    notes: list[str] = []

    pa, pb = norm_pmid(a.get("pmid")), norm_pmid(b.get("pmid"))
    if pa and pb:
        fields["pmid"] = PASS if pa == pb else FAIL
        if pa != pb:
            notes.append(f"PMID differs ({pa} vs {pb})")

    da, db = norm_doi(a.get("doi")), norm_doi(b.get("doi"))
    if da and db:
        fields["doi"] = PASS if da == db else FAIL
        if da != db:
            notes.append(f"DOI differs ({a.get('doi')} vs {b.get('doi')})")
    else:
        fields["doi"] = REVIEW
        notes.append("DOI missing on one side")

    score = title_score(a.get("title"), b.get("title"))
    if score >= TITLE_PASS:
        fields["title"] = PASS
    elif score >= TITLE_REVIEW:
        fields["title"] = REVIEW
        notes.append(f"title similarity {score:.2f}")
    else:
        fields["title"] = FAIL
        notes.append(f"title similarity {score:.2f} — likely a different paper")

    fa, fb = surname_forms(a.get("first_author")), surname_forms(b.get("first_author"))
    if fa & fb:
        fields["first_author"] = PASS
    else:
        fields["first_author"] = REVIEW
        notes.append(f"first author differs ({a.get('first_author')} vs {b.get('first_author')})")

    ya, yb = _year(a.get("year")), _year(b.get("year"))
    if ya is not None and yb is not None:
        fields["year"] = PASS if abs(ya - yb) <= 1 else REVIEW
        if abs(ya - yb) > 1:
            notes.append(f"year differs ({ya} vs {yb})")

    if is_retracted(a) or is_retracted(b):
        fields["retraction"] = FAIL
        notes.append("retracted publication")

    return {
        "status": worst(*fields.values()),
        "fields": fields,
        "title_score": round(score, 3),
        "notes": notes,
    }
