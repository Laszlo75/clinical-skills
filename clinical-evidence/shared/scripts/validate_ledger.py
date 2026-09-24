#!/usr/bin/env python3
"""Validate a clinical-evidence YAML reference ledger against schema v1.x (1.0–1.3).

Usage:
    python validate_ledger.py <path_to_ledger.yaml>

Exit codes:
    0 — ledger is valid. WARN lines may still be printed; they are non-blocking.
    1 — ledger has one or more ERROR issues. Do not proceed.
    2 — ledger file missing or unparseable YAML.

This script is the executable counterpart to ../references/ledger_schema.md and is
the single source of truth for what a valid ledger looks like. Every producer and
consumer of the reference ledger must run this script before relying on
the ledger contents.

Schema version supported: 1.x
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "ERROR: PyYAML is not installed. Install with: pip install pyyaml\n"
    )
    sys.exit(2)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from refmatch import grade_in_source, norm_doi  # noqa: E402


SUPPORTED_MAJOR = 1
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
PMID_RE = re.compile(r"^\d+$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ALLOWED_SOURCES = {"pubmed", "scholar_gateway", "both"}
ALLOWED_PREPRINT_SERVERS = {"medrxiv", "biorxiv"}
ALLOWED_TRIAL_PHASES = {"Phase I", "Phase II", "Phase III", "Phase IV"}
ALLOWED_TRIAL_STATUSES = {"RECRUITING", "ACTIVE_NOT_RECRUITING", "COMPLETED"}
ALLOWED_INTEGRITY_STATUSES = {"pass", "review"}  # "fail" rows are moved to excluded_references
ALLOWED_CERTAINTY = {"high", "moderate", "low", "very low"}  # GRADE certainty (schema 1.2)
ALLOWED_CURRENCY = {"current", "past_review_date", "superseded", "withdrawn", "draft", "unknown"}  # 1.3
RETRACTION_MARKERS = ("[Retracted]", "[Retraction of:", "Retracted:")


def _check_optional_str(entry: dict, fields: tuple, base: str, issues: "Issues") -> None:
    for field in fields:
        if field in entry and entry[field] is not None and not isinstance(entry[field], str):
            issues.error(f"{base}.{field}", "must be a string if present")


def _check_questions_field(entry: dict, base: str, issues: "Issues") -> None:
    qs = entry.get("questions")
    if qs is not None and (not isinstance(qs, list) or not all(isinstance(q, str) for q in qs)):
        issues.error(f"{base}.questions", "must be a list of question ids (strings) if present")


class Issues:
    """Collects ERROR and WARN messages as the validator runs."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, field: str, msg: str) -> None:
        self.errors.append(f"ERROR: {field} — {msg}")

    def warn(self, field: str, msg: str) -> None:
        self.warnings.append(f"WARN: {field} — {msg}")

    def has_errors(self) -> bool:
        return bool(self.errors)

    def print_all(self) -> None:
        for line in self.errors:
            print(line)
        for line in self.warnings:
            print(line)


def _parse_version(raw: Any) -> tuple[int, int, int] | None:
    """Parse a semver string into (major, minor, patch). Returns None if unparseable."""
    if not isinstance(raw, str):
        return None
    parts = raw.strip().split(".")
    if len(parts) < 2 or len(parts) > 3:
        return None
    try:
        major = int(parts[0])
        minor = int(parts[1])
        patch = int(parts[2]) if len(parts) == 3 else 0
    except ValueError:
        return None
    return (major, minor, patch)


def _check_metadata(metadata: Any, issues: Issues) -> None:
    if not isinstance(metadata, dict):
        issues.error("metadata", "must be a mapping")
        return

    # Schema version — the critical field.
    raw_version = metadata.get("ledger_schema_version")
    if raw_version is None:
        issues.error(
            "metadata.ledger_schema_version",
            "missing — legacy unversioned ledger; regenerate using the "
            "clinical-evidence plugin's evidence-search agent",
        )
    else:
        parsed = _parse_version(raw_version)
        if parsed is None:
            issues.error(
                "metadata.ledger_schema_version",
                f"unparseable version string: {raw_version!r}",
            )
        elif parsed[0] != SUPPORTED_MAJOR:
            issues.error(
                "metadata.ledger_schema_version",
                f"schema MAJOR version {parsed[0]} is not supported "
                f"(this validator supports {SUPPORTED_MAJOR}.x)",
            )

    # Required metadata fields.
    for field in ("topic", "search_date", "skill_version", "model_id"):
        value = metadata.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            issues.error(f"metadata.{field}", "missing or empty")

    # search_date format + sanity.
    sd = metadata.get("search_date")
    if isinstance(sd, str) and not ISO_DATE_RE.match(sd):
        issues.error(
            "metadata.search_date",
            f"not ISO 8601 YYYY-MM-DD: {sd!r}",
        )
    elif isinstance(sd, date):
        # PyYAML will convert YYYY-MM-DD to a datetime.date. Accept it.
        pass

    # mesh_terms and guideline_bodies — lists, may be empty but should exist.
    for field in ("mesh_terms", "guideline_bodies"):
        value = metadata.get(field)
        if value is None:
            issues.warn(f"metadata.{field}", "missing — recommended but not required")
        elif not isinstance(value, list):
            issues.error(f"metadata.{field}", "must be a list")

    # review questions (schema 1.2, optional)
    questions = metadata.get("questions")
    if questions is not None:
        if not isinstance(questions, list) or not all(
            isinstance(q, dict) and isinstance(q.get("id"), str) and isinstance(q.get("text"), str)
            for q in questions
        ):
            issues.error("metadata.questions", "must be a list of {id, text} mappings if present")


def _check_grade(grade: Any, path: str, issues: Issues) -> None:
    if not isinstance(grade, dict):
        issues.error(
            f"{path}.grade",
            "must be a structured mapping with system/code/display (legacy free-text "
            "strings are not supported in schema 1.0)",
        )
        return
    for field in ("system", "code", "display"):
        value = grade.get(field)
        if not isinstance(value, str) or not value.strip():
            issues.error(f"{path}.grade.{field}", "missing or not a non-empty string")


def _check_guidelines(guidelines: Any, issues: Issues, seen_ref_ids: set[int]) -> None:
    if guidelines is None:
        issues.error("guidelines", "missing top-level section")
        return
    if not isinstance(guidelines, list):
        issues.error("guidelines", "must be a list")
        return
    # An empty list is allowed (a search may return zero published guidelines).
    for i, g in enumerate(guidelines):
        base = f"guidelines[{i}]"
        if not isinstance(g, dict):
            issues.error(base, "must be a mapping")
            continue
        ref_id = g.get("ref_id")
        if not isinstance(ref_id, int):
            issues.error(f"{base}.ref_id", "must be an integer")
        else:
            if ref_id in seen_ref_ids:
                issues.error(f"{base}.ref_id", f"duplicate ref_id {ref_id}")
            seen_ref_ids.add(ref_id)
        if g.get("type") != "guideline":
            issues.error(f"{base}.type", "must be the literal string 'guideline'")
        for field in ("title", "organisation", "url"):
            if not isinstance(g.get(field), str) or not g.get(field).strip():
                issues.error(f"{base}.{field}", "missing or not a non-empty string")
        if not isinstance(g.get("year"), int):
            issues.error(f"{base}.year", "must be an integer")
        _check_questions_field(g, base, issues)
        _check_optional_str(g, ("edition",), base, issues)
        cached = g.get("cached_on")
        if cached is not None and not (isinstance(cached, date) or ISO_DATE_RE.match(str(cached))):
            issues.error(f"{base}.cached_on", f"not ISO 8601 YYYY-MM-DD: {cached!r}")
        cur = g.get("currency")
        if cur is not None:
            if not isinstance(cur, dict) or cur.get("status") not in ALLOWED_CURRENCY:
                issues.error(f"{base}.currency.status", f"must be one of {sorted(ALLOWED_CURRENCY)}")
            elif cur["status"] != "current":
                issues.warn(f"{base}.currency", f"{g.get('organisation')} {g.get('year')}: {cur['status']}"
                            + (f" — {cur['note']}" if cur.get("note") else ""))
        recs = g.get("key_recommendations")
        if recs is None:
            issues.warn(f"{base}.key_recommendations", "missing — empty list recommended")
        elif not isinstance(recs, list):
            issues.error(f"{base}.key_recommendations", "must be a list")
        else:
            for j, r in enumerate(recs):
                rpath = f"{base}.key_recommendations[{j}]"
                if not isinstance(r, dict):
                    issues.error(rpath, "must be a mapping")
                    continue
                if not isinstance(r.get("text"), str) or not r.get("text").strip():
                    issues.error(f"{rpath}.text", "missing or not a non-empty string")
                _check_grade(r.get("grade"), rpath, issues)
                if isinstance(r.get("grade"), dict) and not grade_in_source(r):
                    issues.warn(f"{rpath}.grade",
                                f"{r['grade'].get('display')!r} not found in the quoted source text "
                                "— don't quote it as the guideline's grade")
                _check_optional_str(r, ("source_quote", "section"), rpath, issues)
                acc = r.get("accessed")
                if acc is not None and not (isinstance(acc, date) or ISO_DATE_RE.match(str(acc))):
                    issues.error(f"{rpath}.accessed", f"not ISO 8601 YYYY-MM-DD: {acc!r}")


def _check_references(
    references: Any, issues: Issues, seen_ref_ids: set[int], verified_schema: bool = False
) -> None:
    if references is None:
        issues.error("references", "missing top-level section")
        return
    if not isinstance(references, list):
        issues.error("references", "must be a list")
        return
    if len(references) == 0:
        issues.warn(
            "references",
            "empty — a search with zero peer-reviewed references is unusual",
        )
    seen_dois: dict[str, int] = {}
    for i, r in enumerate(references):
        base = f"references[{i}]"
        if not isinstance(r, dict):
            issues.error(base, "must be a mapping")
            continue
        # ref_id
        ref_id = r.get("ref_id")
        if not isinstance(ref_id, int):
            issues.error(f"{base}.ref_id", "must be an integer")
        else:
            if ref_id in seen_ref_ids:
                issues.error(f"{base}.ref_id", f"duplicate ref_id {ref_id}")
            seen_ref_ids.add(ref_id)
        # pmid — may be null for scholar_gateway-only refs
        pmid = r.get("pmid")
        if pmid is not None:
            if not isinstance(pmid, (str, int)) or not PMID_RE.match(str(pmid)):
                issues.error(f"{base}.pmid", f"not numeric: {pmid!r}")
        # doi — required, must match format
        doi = r.get("doi")
        if not isinstance(doi, str) or not doi.strip():
            issues.error(f"{base}.doi", "missing or not a non-empty string")
        elif not DOI_RE.match(doi):
            issues.error(f"{base}.doi", f"does not match DOI format 10.XXXX/...: {doi!r}")
        else:
            key = norm_doi(doi)
            if key in seen_dois:
                issues.error(
                    f"{base}.doi",
                    f"duplicate DOI already used at references[{seen_dois[key]}]",
                )
            else:
                seen_dois[key] = i
        # string fields
        for field in (
            "first_author",
            "authors_full",
            "title",
            "journal",
            "key_finding",
        ):
            value = r.get(field)
            if not isinstance(value, str) or not value.strip():
                issues.error(f"{base}.{field}", "missing or not a non-empty string")
        # year integer
        if not isinstance(r.get("year"), int):
            issues.error(f"{base}.year", "must be an integer")
        # volume/pages may be empty strings (papers sometimes have none)
        for field in ("volume", "pages"):
            if field in r and not isinstance(r[field], str):
                issues.error(f"{base}.{field}", "must be a string (may be empty)")
        # source enum
        source = r.get("source")
        if source not in ALLOWED_SOURCES:
            issues.error(
                f"{base}.source",
                f"must be one of {sorted(ALLOWED_SOURCES)}, got {source!r}",
            )
        # full_text_reviewed boolean
        if not isinstance(r.get("full_text_reviewed"), bool):
            issues.error(f"{base}.full_text_reviewed", "must be a boolean")
        # optional appraisal fields (schema 1.2)
        _check_questions_field(r, base, issues)
        _check_optional_str(r, ("study_design", "population"), base, issues)
        if "sample_size" in r and r["sample_size"] is not None and not isinstance(r["sample_size"], int):
            issues.error(f"{base}.sample_size", "must be an integer if present")
        cert = r.get("certainty")
        if cert is not None and str(cert).lower() not in ALLOWED_CERTAINTY:
            issues.error(f"{base}.certainty", f"must be one of {sorted(ALLOWED_CERTAINTY)}, got {cert!r}")
        # integrity block (schema 1.1, written by verify_references.py --apply)
        integrity = r.get("integrity")
        if integrity is None:
            if verified_schema:
                issues.warn(f"{base}.integrity", "missing — reference not independently verified")
        elif not isinstance(integrity, dict):
            issues.error(f"{base}.integrity", "must be a mapping")
        elif integrity.get("status") not in ALLOWED_INTEGRITY_STATUSES:
            issues.error(
                f"{base}.integrity.status",
                f"must be one of {sorted(ALLOWED_INTEGRITY_STATUSES)}, got "
                f"{integrity.get('status')!r} (failed references belong in excluded_references)",
            )
        # retraction check on title
        title = r.get("title")
        if isinstance(title, str):
            for marker in RETRACTION_MARKERS:
                if marker.lower() in title.lower():
                    issues.error(
                        f"{base}.title",
                        f"appears to be a retracted paper (contains {marker!r}); "
                        "retracted papers must be removed from the ledger",
                    )
                    break


def _check_preprints(preprints: Any, issues: Issues, seen_ref_ids: set[int] | None = None) -> None:
    if preprints is None:
        return  # optional
    if not isinstance(preprints, list):
        issues.error("preprints", "must be a list if present")
        return
    for i, p in enumerate(preprints):
        base = f"preprints[{i}]"
        if not isinstance(p, dict):
            issues.error(base, "must be a mapping")
            continue
        ref_id = p.get("ref_id")
        if seen_ref_ids is not None and isinstance(ref_id, int):
            if ref_id in seen_ref_ids:
                issues.error(f"{base}.ref_id", f"duplicate ref_id {ref_id}")
            seen_ref_ids.add(ref_id)
        for field in ("doi", "authors", "title", "key_finding"):
            if not isinstance(p.get(field), str) or not p.get(field).strip():
                issues.error(f"{base}.{field}", "missing or not a non-empty string")
        doi = p.get("doi")
        if isinstance(doi, str) and not DOI_RE.match(doi):
            issues.error(f"{base}.doi", f"does not match DOI format: {doi!r}")
        server = p.get("server")
        if server not in ALLOWED_PREPRINT_SERVERS:
            issues.error(
                f"{base}.server",
                f"must be one of {sorted(ALLOWED_PREPRINT_SERVERS)}, got {server!r}",
            )
        if not isinstance(p.get("year"), int):
            issues.error(f"{base}.year", "must be an integer")
        pub_doi = p.get("published_version_doi")
        if pub_doi is not None and (
            not isinstance(pub_doi, str) or not DOI_RE.match(pub_doi)
        ):
            issues.error(
                f"{base}.published_version_doi",
                f"must be null or a valid DOI, got {pub_doi!r}",
            )


def _check_ongoing_trials(trials: Any, issues: Issues) -> None:
    if trials is None:
        return  # optional
    if not isinstance(trials, list):
        issues.error("ongoing_trials", "must be a list if present")
        return
    for i, t in enumerate(trials):
        base = f"ongoing_trials[{i}]"
        if not isinstance(t, dict):
            issues.error(base, "must be a mapping")
            continue
        nct = t.get("nct_id")
        if not isinstance(nct, str) or not nct.startswith("NCT"):
            issues.error(f"{base}.nct_id", f"must start with 'NCT', got {nct!r}")
        for field in ("title", "relevance"):
            if not isinstance(t.get(field), str) or not t.get(field).strip():
                issues.error(f"{base}.{field}", "missing or not a non-empty string")
        if t.get("phase") not in ALLOWED_TRIAL_PHASES:
            issues.error(
                f"{base}.phase",
                f"must be one of {sorted(ALLOWED_TRIAL_PHASES)}, got {t.get('phase')!r}",
            )
        if t.get("status") not in ALLOWED_TRIAL_STATUSES:
            issues.error(
                f"{base}.status",
                f"must be one of {sorted(ALLOWED_TRIAL_STATUSES)}, got {t.get('status')!r}",
            )
        ec = t.get("estimated_completion")
        if not isinstance(ec, str) or not re.match(r"^\d{4}-\d{2}$", ec):
            issues.error(
                f"{base}.estimated_completion",
                f"must be YYYY-MM string, got {ec!r}",
            )
        if not isinstance(t.get("sample_size"), int):
            issues.error(f"{base}.sample_size", "must be an integer")


def _check_excluded(excluded: Any, issues: Issues, seen_ref_ids: set[int]) -> None:
    if excluded is None:
        return  # optional (schema 1.1)
    if not isinstance(excluded, list):
        issues.error("excluded_references", "must be a list if present")
        return
    for i, e in enumerate(excluded):
        base = f"excluded_references[{i}]"
        if not isinstance(e, dict):
            issues.error(base, "must be a mapping")
            continue
        if not isinstance(e.get("reason"), str) or not e["reason"].strip():
            issues.error(f"{base}.reason", "missing or not a non-empty string")
        if e.get("ref_id") in seen_ref_ids:
            issues.error(
                f"{base}.ref_id",
                f"ref_id {e.get('ref_id')} is excluded but still present in guidelines/references",
            )


def _is_verified_schema(metadata: Any) -> bool:
    if not isinstance(metadata, dict):
        return False
    parsed = _parse_version(metadata.get("ledger_schema_version"))
    return parsed is not None and parsed[:2] >= (1, 1)


def validate_ledger(path: Path) -> int:
    if not path.exists():
        sys.stderr.write(f"ERROR: ledger file not found: {path}\n")
        return 2
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        sys.stderr.write(f"ERROR: ledger file is not valid YAML: {e}\n")
        return 2
    if not isinstance(data, dict):
        sys.stderr.write("ERROR: ledger top level must be a YAML mapping\n")
        return 2

    issues = Issues()
    seen_ref_ids: set[int] = set()

    _check_metadata(data.get("metadata"), issues)
    _check_guidelines(data.get("guidelines"), issues, seen_ref_ids)
    _check_references(
        data.get("references"), issues, seen_ref_ids,
        verified_schema=_is_verified_schema(data.get("metadata")),
    )
    _check_preprints(data.get("preprints"), issues, seen_ref_ids)
    _check_excluded(data.get("excluded_references"), issues, seen_ref_ids)
    _check_ongoing_trials(data.get("ongoing_trials"), issues)

    issues.print_all()

    if issues.has_errors():
        print(f"\nValidation FAILED: {len(issues.errors)} error(s), "
              f"{len(issues.warnings)} warning(s)")
        return 1
    print(f"\nValidation PASSED: 0 errors, {len(issues.warnings)} warning(s)")
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        sys.stderr.write(
            "Usage: python validate_ledger.py <path_to_ledger.yaml>\n"
        )
        return 2
    return validate_ledger(Path(sys.argv[1]))


if __name__ == "__main__":
    sys.exit(main())
