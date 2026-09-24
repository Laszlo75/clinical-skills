#!/usr/bin/env python3
"""Merge partial ledgers from parallel evidence-search agents into one ledger.

Usage:
    python merge_ledgers.py <part.yaml> [<part.yaml> ...] --out <ledger.yaml>

When a protocol raises several independent review questions, the consuming skill may
dispatch one evidence-search agent per question cluster, each writing its own partial
ledger. This script combines them:

- guidelines de-duplicated on (organisation, normalised title, year); their
  key_recommendations are unioned;
- references de-duplicated on PMID, else DOI (case-insensitive); preprints on DOI;
  ongoing trials on NCT id;
- `questions` lists on duplicate entries are unioned, so an entry keeps every review
  question it was found for;
- ref_ids are renumbered 1..N (guidelines, then references, then preprints);
- metadata: topics and distinct model ids joined, mesh_terms / guideline_bodies / questions unioned, latest
  search_date, highest ledger_schema_version.

Run it before verification — ref_ids change here and nothing has cited them yet.
Exit codes: 0 — merged; 1 — bad arguments or a part is not a ledger; 2 — unreadable file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    sys.stderr.write("ERROR: PyYAML is not installed. Install with: pip install pyyaml\n")
    sys.exit(2)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from refmatch import norm_doi, norm_pmid, norm_title  # noqa: E402


def _union(a: list | None, b: list | None) -> list:
    out = list(a or [])
    for item in b or []:
        if item not in out:
            out.append(item)
    return out


def _version_key(v: Any) -> tuple:
    try:
        return tuple(int(x) for x in str(v).split("."))
    except ValueError:
        return (0,)


def _ref_key(ref: dict) -> str:
    pmid = norm_pmid(ref.get("pmid"))
    return f"pmid:{pmid}" if pmid else f"doi:{norm_doi(ref.get('doi'))}"


def _guideline_key(g: dict) -> str:
    return f"{str(g.get('organisation', '')).casefold()}|{norm_title(g.get('title'))}|{g.get('year')}"


def _merge_entries(existing: dict, new: dict) -> None:
    existing["questions"] = _union(existing.get("questions"), new.get("questions"))
    if not existing["questions"]:
        existing.pop("questions")
    if "key_recommendations" in new:
        texts = {r.get("text") for r in existing.get("key_recommendations") or []}
        for rec in new.get("key_recommendations") or []:
            if rec.get("text") not in texts:
                existing.setdefault("key_recommendations", []).append(rec)


def merge(parts: list[dict]) -> dict:
    meta: dict[str, Any] = {}
    sections: dict[str, dict[str, dict]] = {s: {} for s in ("guidelines", "references", "preprints")}
    trials: dict[str, dict] = {}
    keyfuncs = {"guidelines": _guideline_key, "references": _ref_key,
                "preprints": lambda p: f"doi:{norm_doi(p.get('doi'))}"}

    for part in parts:
        m = part.get("metadata") or {}
        if not meta:
            meta = dict(m)
        else:
            if m.get("topic") and m["topic"] not in str(meta.get("topic", "")):
                meta["topic"] = f"{meta.get('topic')}; {m['topic']}" if meta.get("topic") else m["topic"]
            for field in ("mesh_terms", "guideline_bodies", "questions"):
                if m.get(field):
                    meta[field] = _union(meta.get(field), m[field])
            if m.get("model_id") and m["model_id"] not in str(meta.get("model_id", "")):
                meta["model_id"] = f"{meta['model_id']}; {m['model_id']}" if meta.get("model_id") else m["model_id"]
            if str(m.get("search_date", "")) > str(meta.get("search_date", "")):
                meta["search_date"] = m["search_date"]
            if _version_key(m.get("ledger_schema_version")) > _version_key(meta.get("ledger_schema_version")):
                meta["ledger_schema_version"] = m["ledger_schema_version"]
        for section, table in sections.items():
            for entry in part.get(section) or []:
                if not isinstance(entry, dict):
                    continue
                key = keyfuncs[section](entry)
                if key in table:
                    _merge_entries(table[key], entry)
                else:
                    table[key] = dict(entry)
        for t in part.get("ongoing_trials") or []:
            if isinstance(t, dict) and t.get("nct_id") and t["nct_id"] not in trials:
                trials[t["nct_id"]] = dict(t)

    merged: dict[str, Any] = {"metadata": meta}
    next_id = 1
    for section in ("guidelines", "references", "preprints"):
        entries = list(sections[section].values())
        for entry in entries:
            entry["ref_id"] = next_id
            next_id += 1
        if entries or section != "preprints":
            merged[section] = entries
    if trials:
        merged["ongoing_trials"] = list(trials.values())
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("parts", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    parts = []
    for path in args.parts:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as e:
            sys.stderr.write(f"ERROR: cannot read {path}: {e}\n")
            return 2
        if not isinstance(data, dict) or "references" not in data:
            sys.stderr.write(f"ERROR: {path} is not a ledger (no references section)\n")
            return 1
        parts.append(data)

    merged = merge(parts)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        yaml.safe_dump(merged, f, sort_keys=False, allow_unicode=True, width=100)
    n_in = sum(len(p.get("references") or []) for p in parts)
    print(f"Merged {len(parts)} partial ledgers: {n_in} references in, "
          f"{len(merged['references'])} after de-duplication, "
          f"{len(merged['guidelines'])} guidelines -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
