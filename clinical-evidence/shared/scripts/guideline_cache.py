#!/usr/bin/env python3
"""Keep checked guidelines between runs, so they aren't re-read every time.

Usage:
    python guideline_cache.py get   <cache_dir> --out <file.yaml> [--max-age-days 90]
    python guideline_cache.py put   <cache_dir> <ledger.yaml>
    python guideline_cache.py list  <cache_dir>
    python guideline_cache.py clear <cache_dir> [--older-than-days N]

The cache lives in the researcher's own folder (`<workspace>/.clinical-evidence/
guideline_cache`): in Claude Cowork each task runs in a temporary sandbox and the plugin
data folder isn't provided, so the selected folder is the only place that persists.
Every review run from the same folder reuses it. One YAML file per guideline edition (organisation + title + year), holding the ledger entry: edition,
currency, and every recommendation extracted so far with its verbatim quote, grade and
`accessed` date.

- `get` writes the entries checked within `--max-age-days` to one file, for the
  guideline agents. Each entry carries `cached_on`, the date its document was last read.
- `put` stores the guidelines of a finished ledger. Recommendations are merged (by
  text) with those already cached, so the cache grows across topics. An entry the
  agent re-read this run (no `cached_on` in the ledger) is stamped with today's date;
  one it reused unread keeps its original date, so reuse never makes an entry look
  fresher than it is.
- `list` shows what is cached; `clear` empties it (or only entries older than N days),
  e.g. to force a fresh check of every guideline.

Standard library + PyYAML. Exit codes: 0 — ok; 1 — bad arguments; 2 — unreadable file.
Caching is an optimisation: a missing or unreadable cache just means a full search.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    sys.stderr.write("ERROR: PyYAML is not installed. Install with: pip install pyyaml\n")
    sys.exit(2)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from refmatch import norm_title  # noqa: E402

RUN_FIELDS = ("ref_id", "questions")      # belong to one run, not to the guideline


def _slug(g: dict) -> str:
    org = re.sub(r"[^a-z0-9]+", "-", str(g.get("organisation", "")).casefold()).strip("-")
    title = re.sub(r"\s+", "-", norm_title(g.get("title")))
    return f"{org[:40]}__{title[:80]}__{g.get('year')}".strip("-_") or "unnamed"


def _as_date(v: Any) -> date | None:
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v))
    except ValueError:
        return None


def _entries(cache: Path) -> list[tuple[Path, dict]]:
    out = []
    for path in sorted(cache.glob("*.yaml")) if cache.is_dir() else []:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue                            # a damaged entry is just a cache miss
        if isinstance(data, dict) and _as_date(data.get("cached_on")):
            out.append((path, data))
    return out


def get(cache: Path, out: Path, max_age_days: int, today: date) -> int:
    cutoff = today - timedelta(days=max_age_days)
    fresh = [g for _, g in _entries(cache) if _as_date(g["cached_on"]) >= cutoff]
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        yaml.safe_dump({"cache_date": today.isoformat(), "max_age_days": max_age_days,
                        "guidelines": fresh}, f, sort_keys=False, allow_unicode=True, width=100)
    print(f"{len(fresh)} cached guideline(s) checked within {max_age_days} days -> {out}")
    return 0


def put(cache: Path, ledger: dict, today: date) -> int:
    cache.mkdir(parents=True, exist_ok=True)
    stored = refreshed = 0
    for g in ledger.get("guidelines") or []:
        if not isinstance(g, dict) or not g.get("title"):
            continue
        entry = {k: v for k, v in g.items() if k not in RUN_FIELDS}
        reread = not entry.get("cached_on")
        path = cache / f"{_slug(g)}.yaml"
        old = {}
        if path.exists():
            try:
                old = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError):
                old = {}
        texts = {r.get("text") for r in entry.get("key_recommendations") or []}
        merged_recs = list(entry.get("key_recommendations") or [])
        merged_recs += [r for r in old.get("key_recommendations") or [] if r.get("text") not in texts]
        entry["key_recommendations"] = merged_recs
        if reread:
            entry["cached_on"] = today.isoformat()
            refreshed += 1
        else:
            dates = [d for d in (_as_date(entry.get("cached_on")), _as_date(old.get("cached_on"))) if d]
            entry["cached_on"] = max(dates).isoformat() if dates else today.isoformat()
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(entry, f, sort_keys=False, allow_unicode=True, width=100)
        stored += 1
    print(f"Cached {stored} guideline(s) ({refreshed} read this run) in {cache}")
    return 0


def list_cache(cache: Path, today: date) -> int:
    entries = _entries(cache)
    if not entries:
        print(f"Guideline cache is empty ({cache})")
        return 0
    for _, g in entries:
        age = (today - _as_date(g["cached_on"])).days
        status = (g.get("currency") or {}).get("status", "unknown")
        print(f"{g.get('organisation')} {g.get('year')} — {g.get('title')} | "
              f"{len(g.get('key_recommendations') or [])} recs | {status} | checked {age} days ago")
    return 0


def clear(cache: Path, older_than: int | None, today: date) -> int:
    removed = 0
    for path, g in _entries(cache):
        if older_than is None or (today - _as_date(g["cached_on"])).days > older_than:
            path.unlink()
            removed += 1
    print(f"Removed {removed} cached guideline(s) from {cache}")
    return 0


def main(argv: list[str] | None = None, today: date | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("get"); g.add_argument("cache", type=Path)
    g.add_argument("--out", type=Path, required=True)
    g.add_argument("--max-age-days", type=int, default=90)
    u = sub.add_parser("put"); u.add_argument("cache", type=Path); u.add_argument("ledger", type=Path)
    ls = sub.add_parser("list"); ls.add_argument("cache", type=Path)
    c = sub.add_parser("clear"); c.add_argument("cache", type=Path)
    c.add_argument("--older-than-days", type=int)
    args = p.parse_args(argv)
    today = today or date.today()

    if args.cmd == "get":
        return get(args.cache, args.out, args.max_age_days, today)
    if args.cmd == "put":
        try:
            ledger = yaml.safe_load(args.ledger.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as e:
            sys.stderr.write(f"ERROR: cannot read {args.ledger}: {e}\n")
            return 2
        if not isinstance(ledger, dict):
            sys.stderr.write(f"ERROR: {args.ledger} is not a ledger\n")
            return 1
        return put(args.cache, ledger, today)
    if args.cmd == "list":
        return list_cache(args.cache, today)
    return clear(args.cache, args.older_than_days, today)


if __name__ == "__main__":
    sys.exit(main())
