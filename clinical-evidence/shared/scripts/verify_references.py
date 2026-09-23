#!/usr/bin/env python3
"""Cross-check a reference ledger against an independent second reading.

Usage:
    python verify_references.py <ledger.yaml> --against <refs_b.yaml> [--apply]
                                [--report <verification_report.csv>]

The ledger (reading A) is written by the evidence-search agent. The second reading
(B) is written by the reference-checker agent, which re-reads every PMID from PubMed
in a fresh context without ever seeing A. A transcription error would have to be made
identically twice to pass. Fields are compared tolerantly (see refmatch.py): spelling,
diacritic, case and markup differences pass; a different identifier or paper fails.

refs_b.yaml format — a list (or {"references": [...]}) of:
    - pmid: "29596116"          # or null for DOI-only records
      doi: "10.1097/TP.0000000000002191"
      title: "..."
      first_author: "Kotton CN"
      year: 2018
      journal: "Transplantation"
      publication_types: ["Journal Article", "Practice Guideline"]
      not_found: false          # true if PubMed had no record for the identifier

With --apply the ledger is updated in place:
    - every reference gets `integrity: {status, checked_on, notes}`;
    - agreed DOIs are stored in bare form (e.g. a URL-form DOI becomes "10.xxx/…");
    - `fail` references move to top-level `excluded_references` (with a reason), so
      they can never be cited;
    - metadata.ledger_schema_version becomes "1.1".

Exit codes: 0 — done (review rows allowed); 1 — bad input; 2 — ledger missing/unparseable.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    sys.stderr.write("ERROR: PyYAML is not installed. Install with: pip install pyyaml\n")
    sys.exit(2)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import refmatch  # noqa: E402
from refmatch import FAIL, PASS, REVIEW  # noqa: E402

REPORT_COLUMNS = [
    "ref_id", "pmid", "doi", "status", "pmid_check", "doi_check", "title_check",
    "first_author_check", "year_check", "retraction_check", "title_score", "notes",
]


def _load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _index_b(records: list[dict]) -> tuple[dict[str, dict], dict[str, dict]]:
    by_pmid: dict[str, dict] = {}
    by_doi: dict[str, dict] = {}
    for rec in records:
        if not isinstance(rec, dict):
            continue
        pmid = refmatch.norm_pmid(rec.get("pmid"))
        doi = refmatch.norm_doi(rec.get("doi"))
        if pmid:
            by_pmid[pmid] = rec
        if doi:
            by_doi[doi] = rec
    return by_pmid, by_doi


def check_reference(ref: dict, by_pmid: dict, by_doi: dict) -> dict:
    pmid = refmatch.norm_pmid(ref.get("pmid"))
    doi = refmatch.norm_doi(ref.get("doi"))
    b = by_pmid.get(pmid) if pmid else None
    if b is None and doi:
        b = by_doi.get(doi)

    if b is None:
        return {"status": REVIEW, "fields": {}, "title_score": "",
                "notes": ["not independently checked (missing from second reading)"]}
    if b.get("not_found"):
        if pmid:
            return {"status": FAIL, "fields": {"pmid": FAIL}, "title_score": "",
                    "notes": [f"PMID {pmid} not found in PubMed"]}
        return {"status": REVIEW, "fields": {}, "title_score": "",
                "notes": ["DOI-only reference not found in PubMed; not cross-checked"]}
    return refmatch.compare(ref, b)


def _adopt_bare_doi(ref: dict, result: dict, by_pmid: dict, by_doi: dict) -> None:
    """When both readings agree on the DOI, store it in bare form ("10.xxx/…").

    Agreement is judged after normalisation, so a DOI written as a URL or with a
    "doi:" prefix passes the check; the stored value should still be the bare form
    the rest of the pipeline expects. PubMed's casing is preferred when available.
    """
    if result["fields"].get("doi") != PASS:
        return
    b = by_pmid.get(refmatch.norm_pmid(ref.get("pmid"))) or by_doi.get(refmatch.norm_doi(ref.get("doi")))
    source = (b or {}).get("doi") or ref.get("doi")
    bare = refmatch.bare_doi(source)
    if bare and bare != ref.get("doi"):
        ref["doi"] = bare


def verify(ledger_path: Path, b_path: Path, apply: bool, report_path: Path | None) -> int:
    if not ledger_path.exists():
        sys.stderr.write(f"ERROR: ledger not found: {ledger_path}\n")
        return 2
    try:
        ledger = _load_yaml(ledger_path)
    except yaml.YAMLError as e:
        sys.stderr.write(f"ERROR: ledger is not valid YAML: {e}\n")
        return 2
    if not isinstance(ledger, dict) or not isinstance(ledger.get("references"), list):
        sys.stderr.write("ERROR: ledger has no references list\n")
        return 1
    if not b_path.exists():
        sys.stderr.write(f"ERROR: second reading not found: {b_path}\n")
        return 1
    try:
        b_data = _load_yaml(b_path)
    except yaml.YAMLError as e:
        sys.stderr.write(f"ERROR: second reading is not valid YAML: {e}\n")
        return 1
    if isinstance(b_data, dict):
        b_data = b_data.get("references")
    if not isinstance(b_data, list):
        sys.stderr.write("ERROR: second reading must be a list of records\n")
        return 1

    by_pmid, by_doi = _index_b(b_data)
    today = date.today().isoformat()
    kept, excluded, rows = [], [], []
    counts = {PASS: 0, REVIEW: 0, FAIL: 0}

    for ref in ledger["references"]:
        if not isinstance(ref, dict):
            kept.append(ref)
            continue
        result = check_reference(ref, by_pmid, by_doi)
        status = result["status"]
        counts[status] += 1
        note = "; ".join(result["notes"])
        f = result["fields"]
        rows.append({
            "ref_id": ref.get("ref_id"), "pmid": ref.get("pmid") or "", "doi": ref.get("doi") or "",
            "status": status, "pmid_check": f.get("pmid", ""), "doi_check": f.get("doi", ""),
            "title_check": f.get("title", ""), "first_author_check": f.get("first_author", ""),
            "year_check": f.get("year", ""), "retraction_check": f.get("retraction", ""),
            "title_score": result["title_score"], "notes": note,
        })
        if status == FAIL:
            excluded.append({
                "ref_id": ref.get("ref_id"), "pmid": ref.get("pmid"), "doi": ref.get("doi"),
                "title": ref.get("title"), "reason": note or "failed verification",
            })
        else:
            _adopt_bare_doi(ref, result, by_pmid, by_doi)
            ref["integrity"] = {"status": status, "checked_on": today, "notes": note}
            kept.append(ref)

    report_path = report_path or ledger_path.parent / ".clinical-evidence" / "verification_report.csv"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    if apply:
        ledger["references"] = kept
        if excluded:
            ledger["excluded_references"] = (ledger.get("excluded_references") or []) + excluded
        meta = ledger.setdefault("metadata", {})
        meta["ledger_schema_version"] = "1.1"
        meta["verification"] = f"independent second reading, cross-checked {today}"
        with ledger_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(ledger, f, sort_keys=False, allow_unicode=True, width=100)

    print(f"Verified {sum(counts.values())} references: "
          f"{counts[PASS]} pass, {counts[REVIEW]} review, {counts[FAIL]} fail")
    for row in rows:
        if row["status"] == FAIL:
            print(f"EXCLUDED ref {row['ref_id']} (PMID {row['pmid'] or '—'}): {row['notes']}")
    for row in rows:
        if row["status"] == REVIEW:
            print(f"REVIEW ref {row['ref_id']} (PMID {row['pmid'] or '—'}): {row['notes']}")
    print(f"Report: {report_path}" + ("" if apply else "  (ledger not modified; pass --apply)"))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--against", type=Path, required=True, help="second reading (refs_b.yaml)")
    parser.add_argument("--apply", action="store_true", help="write results into the ledger")
    parser.add_argument("--report", type=Path, default=None, help="CSV report path")
    args = parser.parse_args()
    return verify(args.ledger, args.against, args.apply, args.report)


if __name__ == "__main__":
    sys.exit(main())
