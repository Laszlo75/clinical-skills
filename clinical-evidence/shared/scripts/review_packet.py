#!/usr/bin/env python3
"""Build a compact packet for the second reviewer: only what it needs to check.

Usage:
    python review_packet.py --ledger <ledger.yaml> --map <protocol_map.yaml>
        --judgements <judgements.yaml> --ids J3,J5,J9 --out <packet.yaml>

The second reviewer used to read the whole evidence ledger (often 100+ entries) to
check a handful of judgements, and with two reviewers in parallel each read it all.
The packet holds, for the listed judgements only:

  judgements  the draft judgements, each with the protocol statement it concerns
  evidence    every ledger entry they cite (MDT options included), with the fields a
              reviewer checks: guideline recommendations with verbatim quotes and
              grades, or a paper's identifiers, design, population, size, certainty and
              key finding
  other_evidence
              every other ledger entry tagged with the same review questions but not
              cited — so the reviewer can spot evidence that was overlooked or that
              contradicts the judgement, not just check what was cited
  questions   the review questions those judgements answer

Standard library + PyYAML. Exit codes: 0 — ok; 1 — unknown judgement id or cited
ref_id missing from the ledger; 2 — unreadable file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("ERROR: PyYAML is not installed. Install with: pip install pyyaml\n")
    sys.exit(2)

GUIDELINE_FIELDS = ("ref_id", "organisation", "title", "year", "edition", "currency", "url")
REC_FIELDS = ("text", "grade", "source_quote", "section")
PAPER_FIELDS = ("ref_id", "first_author", "title", "journal", "year", "pmid", "doi",
                "study_design", "population", "sample_size", "certainty", "key_finding")


def _load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _cited(j: dict) -> list:
    refs = list(j.get("evidence") or [])
    for opt in j.get("options") or []:
        refs += [r for r in (opt.get("evidence") or []) if r not in refs]
    return refs


def build(ledger: dict, pmap: dict, judgements: list, ids: list[str]) -> tuple[dict, list[str]]:
    errors = []
    by_id = {j.get("id"): j for j in judgements if isinstance(j, dict)}
    statements = {s.get("id"): s for s in pmap.get("statements") or []}
    questions = {q.get("id"): q for q in pmap.get("questions") or []}
    entries = {}
    for section in ("guidelines", "references", "preprints"):
        for e in ledger.get(section) or []:
            if isinstance(e, dict) and isinstance(e.get("ref_id"), int):
                entries[e["ref_id"]] = (section, e)

    picked, refs, qids = [], [], []
    for jid in ids:
        j = by_id.get(jid)
        if j is None:
            errors.append(f"unknown judgement {jid}")
            continue
        st = statements.get(j.get("statement")) or {}
        picked.append({**{k: v for k, v in j.items() if k != "second_review"},
                       "protocol_statement": {k: st.get(k) for k in ("section", "text") if st.get(k)}
                       or None})
        refs += [r for r in _cited(j) if r not in refs]
        if j.get("question") and j["question"] not in qids:
            qids.append(j["question"])

    def trim(section: str, e: dict) -> dict:
        if section == "guidelines":
            item = {k: e[k] for k in GUIDELINE_FIELDS if e.get(k) is not None}
            item["type"] = "guideline"
            item["key_recommendations"] = [{k: rec[k] for k in REC_FIELDS if rec.get(k) is not None}
                                           for rec in e.get("key_recommendations") or []]
        else:
            item = {k: e[k] for k in PAPER_FIELDS if e.get(k) is not None}
            item["type"] = "preprint" if section == "preprints" else "paper"
        return item

    evidence = []
    for r in sorted(refs):
        if r not in entries:
            errors.append(f"cited ref_id {r} is not in the ledger")
            continue
        evidence.append(trim(*entries[r]))
    other = [trim(section, e) for r, (section, e) in sorted(entries.items())
             if r not in refs and set(e.get("questions") or []) & set(qids)]

    packet = {"questions": [questions[q] for q in qids if q in questions],
              "judgements": picked, "evidence": evidence, "other_evidence": other}
    return packet, errors


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--ledger", type=Path, required=True)
    p.add_argument("--map", type=Path, required=True, dest="pmap")
    p.add_argument("--judgements", type=Path, required=True)
    p.add_argument("--ids", required=True, help="comma-separated judgement ids")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        ledger, pmap, judgements = _load(args.ledger), _load(args.pmap), _load(args.judgements)
    except (OSError, yaml.YAMLError) as e:
        sys.stderr.write(f"ERROR: cannot read input: {e}\n")
        return 2
    ids = [i.strip() for i in args.ids.split(",") if i.strip()]
    packet, errors = build(ledger or {}, pmap or {}, judgements or [], ids)
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        yaml.safe_dump(packet, f, sort_keys=False, allow_unicode=True, width=100)
    n_all = sum(len(ledger.get(s) or []) for s in ("guidelines", "references", "preprints"))
    print(f"Packet: {len(packet['judgements'])} judgements, {len(packet['evidence'])} of "
          f"{n_all} evidence entries -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
