#!/usr/bin/env python3
"""Format ledger entries as a numbered Vancouver reference list.

Usage:
    python format_references.py <ledger.yaml> --ids 5,2,9 [--json]
    python format_references.py <ledger.yaml> --all [--json]

`--ids` lists ledger ref_ids in citation order: the first id becomes [1], the second
[2], and so on. Output is Markdown (numbered list with clickable DOI/URL links) or, with
--json, a list of {number, ref_id, kind, markdown, plain, url} objects for code that
builds the .docx directly. Either way, reference text comes from the verified ledger
and is never retyped.

Covers `guidelines`, `references` and `preprints`. An id that is unknown, or that was
moved to `excluded_references` by verification, is an error.

Exit codes: 0 — ok; 1 — unknown/excluded id or bad arguments; 2 — ledger missing/unparseable.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from refmatch import bare_doi  # noqa: E402

try:
    import yaml
except ImportError:
    sys.stderr.write("ERROR: PyYAML is not installed. Install with: pip install pyyaml\n")
    sys.exit(2)

MAX_AUTHORS = 6
_ET_AL = re.compile(r"^(et al\.?|and others|others)$", re.I)


def _s(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _sentence(text: str) -> str:
    text = text.strip()
    return text if not text or text[-1] in ".?!" else text + "."


def _authors(authors_full: str, first_author: str) -> str:
    parts = [p.strip() for p in (authors_full or first_author).split(",") if p.strip()]
    truncated = any(_ET_AL.match(p) for p in parts)
    names = [p for p in parts if not _ET_AL.match(p)]
    if len(names) > MAX_AUTHORS:
        names, truncated = names[:MAX_AUTHORS], True
    return ", ".join(names) + (", et al." if truncated else ".") if names else ""


def _article(ref: dict) -> tuple[str, str, str]:
    authors = _authors(_s(ref.get("authors_full")), _s(ref.get("first_author")))
    title = _sentence(_s(ref.get("title")))
    journal = _s(ref.get("journal"))
    year, volume, pages = _s(ref.get("year")), _s(ref.get("volume")), _s(ref.get("pages"))
    source = year + (f";{volume}" if volume else "") + (f":{pages}" if pages else "") + "."
    pmid, doi = _s(ref.get("pmid")), bare_doi(ref.get("doi"))
    url = f"https://doi.org/{doi}" if doi else ""
    tail_plain = (f" PMID: {pmid}." if pmid else "") + (f" doi:{doi}" if doi else "")
    tail_md = (f" PMID: {pmid}." if pmid else "") + (f" [doi:{doi}]({url})" if doi else "")
    head = " ".join(x for x in (authors, title) if x)
    plain = f"{head} {journal}. {source}{tail_plain}".strip()
    md = f"{head} *{journal}*. {source}{tail_md}".strip()
    return md, plain, url


def _guideline(g: dict) -> tuple[str, str, str]:
    org, title, year, url = (_s(g.get(k)) for k in ("organisation", "title", "year", "url"))
    base = f"{_sentence(org)} {_sentence(title)} {year}.".strip()
    return (f"{base} Available from: [{url}]({url})" if url else base,
            f"{base} Available from: {url}" if url else base, url)


def _preprint(p: dict) -> tuple[str, str, str]:
    authors = _authors(_s(p.get("authors")), "")
    title = _s(p.get("title")).rstrip(".")
    server = {"medrxiv": "medRxiv", "biorxiv": "bioRxiv"}.get(_s(p.get("server")).lower(), _s(p.get("server")))
    doi = bare_doi(p.get("doi"))
    url = f"https://doi.org/{doi}" if doi else ""
    head = f"{authors} {title} [preprint]. {server}. {_s(p.get('year'))}.".strip()
    return (f"{head} [doi:{doi}]({url})" if doi else head,
            f"{head} doi:{doi}" if doi else head, url)


def build_index(ledger: dict) -> dict[int, tuple[str, dict]]:
    index: dict[int, tuple[str, dict]] = {}
    for kind, section in (("guideline", "guidelines"), ("article", "references"), ("preprint", "preprints")):
        for entry in ledger.get(section) or []:
            if isinstance(entry, dict) and isinstance(entry.get("ref_id"), int):
                index[entry["ref_id"]] = (kind, entry)
    return index


def format_entries(ledger: dict, ids: list[int]) -> list[dict]:
    index = build_index(ledger)
    excluded = {e.get("ref_id") for e in ledger.get("excluded_references") or [] if isinstance(e, dict)}
    problems = []
    for ref_id in ids:
        if ref_id in excluded:
            problems.append(f"ref_id {ref_id} was excluded by verification and must not be cited")
        elif ref_id not in index:
            problems.append(f"ref_id {ref_id} is not in the ledger")
    if problems:
        raise ValueError("; ".join(problems))

    formatters = {"article": _article, "guideline": _guideline, "preprint": _preprint}
    out = []
    for number, ref_id in enumerate(ids, start=1):
        kind, entry = index[ref_id]
        md, plain, url = formatters[kind](entry)
        out.append({"number": number, "ref_id": ref_id, "kind": kind,
                    "markdown": md, "plain": plain, "url": url})
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("ledger", type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ids", help="comma-separated ref_ids in citation order")
    group.add_argument("--all", action="store_true", help="every citable entry, in ref_id order")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of Markdown")
    args = parser.parse_args()

    if not args.ledger.exists():
        sys.stderr.write(f"ERROR: ledger not found: {args.ledger}\n")
        return 2
    try:
        with args.ledger.open("r", encoding="utf-8") as f:
            ledger = yaml.safe_load(f)
    except yaml.YAMLError as e:
        sys.stderr.write(f"ERROR: ledger is not valid YAML: {e}\n")
        return 2
    if not isinstance(ledger, dict):
        sys.stderr.write("ERROR: ledger must be a mapping\n")
        return 2

    if args.all:
        ids = sorted(build_index(ledger))
    else:
        try:
            ids = [int(x) for x in args.ids.split(",") if x.strip()]
        except ValueError:
            sys.stderr.write("ERROR: --ids must be comma-separated integers\n")
            return 1
        if len(set(ids)) != len(ids):
            sys.stderr.write("ERROR: --ids contains duplicates\n")
            return 1

    try:
        entries = format_entries(ledger, ids)
    except ValueError as e:
        sys.stderr.write(f"ERROR: {e}\n")
        return 1

    if args.json:
        print(json.dumps(entries, ensure_ascii=False, indent=2))
    else:
        for e in entries:
            print(f"{e['number']}. {e['markdown']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
