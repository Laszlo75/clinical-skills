#!/usr/bin/env python3
"""Write Zotero export files from a clinical-evidence reference ledger.

Usage:
    python ledger_to_exports.py <ledger.yaml> [--prefix PREFIX] [--outdir DIR]

Produces two files in the workspace:
    <PREFIX>_References.bib   — one BibTeX entry per peer-reviewed reference
    <PREFIX>_PMIDs.txt        — one PMID per line, for Zotero bulk import

Exit codes:
    0 — exports written (a WARN line may still be printed, e.g. zero references).
    1 — bad arguments.
    2 — ledger file missing or unparseable YAML.

This script is the single source of truth for the export file format. Consumer
skills (research-summary, protocol-reviewer) call it rather than hand-writing
BibTeX, so the format cannot drift and reference fields are copied verbatim from
the validated ledger instead of being reconstructed from memory.

Scope: only the ledger's `references[]` array is exported. Guidelines are cited
in the generated document's reference list but are not BibTeX records. The PMID
file lists references whose `pmid` field is non-null (Scholar Gateway-only
references are omitted from the .txt but still appear in the .bib by DOI).

Run validate_ledger.py first — this script assumes a structurally valid ledger
and does not re-check the schema.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "ERROR: PyYAML is not installed. Install with: pip install pyyaml\n"
    )
    sys.exit(2)


ET_AL_TOKENS = {"et al", "et al.", "and others", "others"}


def _slugify(text: str) -> str:
    """Turn a free-text topic into a filename-safe prefix."""
    slug = re.sub(r"[^0-9A-Za-z]+", "_", text).strip("_")
    return slug or "References"


def _brace_safe(value: Any) -> str:
    """Render a field value safe to drop inside BibTeX braces.

    Stray braces would break the entry, so they are neutralised. Other
    characters are left verbatim — Zotero's BibTeX import is lenient and the
    ledger fields were copied verbatim from PubMed; we do not LaTeX-escape.
    """
    return str(value).replace("{", "(").replace("}", ")")


def _bib_authors(authors_full: str) -> str:
    """Convert a ledger author list to a BibTeX `and`-separated string.

    The ledger stores authors as `Kotton CN, Kumar D, Caliendo AM, et al.`.
    BibTeX separates authors with ` and ` and uses the keyword `others` for
    a trailing "et al.".
    """
    parts = [p.strip() for p in authors_full.split(",") if p.strip()]
    out = []
    for part in parts:
        if part.lower().rstrip(".") in {t.rstrip(".") for t in ET_AL_TOKENS}:
            out.append("others")
        else:
            out.append(_brace_safe(part))
    return " and ".join(out)


def _cite_key(ref: dict, used: set[str]) -> str:
    """A stable, unique BibTeX cite key: pmid<PMID>, else doi-derived."""
    pmid = ref.get("pmid")
    if pmid is not None and str(pmid).strip():
        base = f"pmid{str(pmid).strip()}"
    else:
        doi = str(ref.get("doi", "")).strip()
        base = "ref" + re.sub(r"[^0-9A-Za-z]+", "", doi) if doi else "ref"
    key = base
    suffix = ord("a")
    while key in used:
        key = f"{base}{chr(suffix)}"
        suffix += 1
    used.add(key)
    return key


def _bib_entry(ref: dict, key: str) -> str:
    """Render one @article entry. Fields are emitted only when present."""
    lines = [f"@article{{{key},"]
    fields: list[tuple[str, str]] = []

    authors_full = ref.get("authors_full") or ref.get("first_author") or ""
    if authors_full:
        fields.append(("author", _bib_authors(authors_full)))
    if ref.get("title"):
        fields.append(("title", "{" + _brace_safe(ref["title"]) + "}"))
    if ref.get("journal"):
        fields.append(("journal", _brace_safe(ref["journal"])))
    if ref.get("year") is not None:
        fields.append(("year", _brace_safe(ref["year"])))
    if str(ref.get("volume", "")).strip():
        fields.append(("volume", _brace_safe(ref["volume"])))
    if str(ref.get("pages", "")).strip():
        fields.append(("pages", _brace_safe(ref["pages"])))
    if ref.get("pmid") is not None and str(ref["pmid"]).strip():
        fields.append(("pmid", _brace_safe(ref["pmid"])))
    if ref.get("doi"):
        fields.append(("doi", _brace_safe(ref["doi"])))

    width = max(len(name) for name, _ in fields)
    body = []
    for name, value in fields:
        body.append(f"  {name.ljust(width)} = {{{value}}}")
    lines.append(",\n".join(body))
    lines.append("}")
    return "\n".join(lines)


def write_exports(ledger_path: Path, prefix: str | None, outdir: Path | None) -> int:
    if not ledger_path.exists():
        sys.stderr.write(f"ERROR: ledger file not found: {ledger_path}\n")
        return 2
    try:
        with ledger_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        sys.stderr.write(f"ERROR: ledger file is not valid YAML: {e}\n")
        return 2
    if not isinstance(data, dict):
        sys.stderr.write("ERROR: ledger top level must be a YAML mapping\n")
        return 2

    metadata = data.get("metadata") or {}
    references = data.get("references") or []
    if not isinstance(references, list):
        sys.stderr.write("ERROR: references must be a list\n")
        return 2

    if prefix is None:
        prefix = _slugify(str(metadata.get("topic", "")))
    if outdir is None:
        outdir = ledger_path.resolve().parent
    outdir.mkdir(parents=True, exist_ok=True)

    bib_path = outdir / f"{prefix}_References.bib"
    pmid_path = outdir / f"{prefix}_PMIDs.txt"

    used_keys: set[str] = set()
    entries = []
    pmids: list[str] = []
    for ref in references:
        if not isinstance(ref, dict):
            continue
        entries.append(_bib_entry(ref, _cite_key(ref, used_keys)))
        pmid = ref.get("pmid")
        if pmid is not None and str(pmid).strip():
            pmids.append(str(pmid).strip())

    bib_path.write_text("\n\n".join(entries) + ("\n" if entries else ""), encoding="utf-8")
    pmid_path.write_text("\n".join(pmids) + ("\n" if pmids else ""), encoding="utf-8")

    if not entries:
        print("WARN: ledger contained zero references — wrote empty export files")
    print(f"Wrote {len(entries)} BibTeX entries to {bib_path}")
    print(f"Wrote {len(pmids)} PMIDs to {pmid_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write Zotero .bib + PMID exports from a reference ledger."
    )
    parser.add_argument("ledger", type=Path, help="path to .literature_search_ledger.yaml")
    parser.add_argument(
        "--prefix",
        default=None,
        help="output filename prefix (default: slug of metadata.topic). "
        "Pass the same [Topic_Name] used for the .md/.docx so all files match.",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=None,
        help="output directory (default: the ledger's own directory)",
    )
    args = parser.parse_args()
    return write_exports(args.ledger, args.prefix, args.outdir)


if __name__ == "__main__":
    sys.exit(main())
