#!/usr/bin/env python3
"""Record how long each stage of a run takes (and its token cost, when known).

Usage:
    python run_log.py <workspace> start <stage> [--skill NAME]
    python run_log.py <workspace> end <stage> [--tokens N] [--note TEXT]
    python run_log.py <workspace> agent <name> --stage <stage> [--seconds S] [--tokens N]
    python run_log.py <workspace> summary

Appends to <workspace>/.clinical-evidence/run_log.csv (created if needed):
    timestamp_utc, run, skill, stage, event, seconds, tokens, note

- `start run` begins a new run (the run number increments); other stages belong to
  the latest run.
- `end` computes the seconds since the matching `start` of that stage in this run.
- `--tokens` is the agent's reported token usage for the stage (e.g. from the
  subagent's completion report); leave it out when unknown.
- `agent` records one dispatched agent's own duration and tokens, as reported when it
  finishes (e.g. `agent guidelines-uk --stage search --seconds 540 --tokens 210000`).
  Parallel agents overlap, so the slowest one sets the stage time; this shows which.
- `summary` prints one line per stage of the latest run — seconds, share of the total,
  tokens — plus the total, for the hand-over message and for benchmarking versions
  against each other. The CSV reads straight into R.

Standard library only; never fails the run — on any error it prints a warning and
exits 0, because timing is diagnostic, not part of the clinical output.
"""

from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

COLUMNS = ["timestamp_utc", "run", "skill", "stage", "event", "seconds", "tokens", "note"]


def _path(workspace: Path) -> Path:
    return workspace / ".clinical-evidence" / "run_log.csv"


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _append(path: Path, row: dict) -> None:
    new = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        if new:
            writer.writeheader()
        writer.writerow(row)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _current_run(rows: list[dict]) -> int:
    return max((int(r["run"]) for r in rows if r.get("run", "").isdigit()), default=0)


def record(workspace: Path, event: str, stage: str, skill: str = "", tokens: str = "",
           note: str = "") -> str:
    path = _path(workspace)
    rows = _read(path)
    run = _current_run(rows) + (1 if (event == "start" and stage == "run") or not rows else 0)
    if not skill:
        skill = next((r["skill"] for r in reversed(rows) if r["run"] == str(run) and r["skill"]), "")
    now = _now()
    seconds = ""
    if event == "end":
        start = next((r for r in reversed(rows) if r["run"] == str(run) and r["stage"] == stage
                      and r["event"] == "start"), None)
        if start:
            seconds = str(int((now - datetime.fromisoformat(start["timestamp_utc"])).total_seconds()))
    _append(path, {"timestamp_utc": now.isoformat(), "run": run, "skill": skill, "stage": stage,
                   "event": event, "seconds": seconds, "tokens": tokens, "note": note})
    return seconds


def record_agent(workspace: Path, name: str, stage: str, seconds: str, tokens: str) -> None:
    path = _path(workspace)
    rows = _read(path)
    run = _current_run(rows) or 1
    skill = next((r["skill"] for r in reversed(rows) if r["run"] == str(run) and r["skill"]), "")
    _append(path, {"timestamp_utc": _now().isoformat(), "run": run, "skill": skill,
                   "stage": f"{stage}/{name}", "event": "agent", "seconds": seconds,
                   "tokens": tokens, "note": ""})


def _fmt(seconds: int) -> str:
    return f"{seconds // 60:3d} min {seconds % 60:02d} s"


def summary(workspace: Path) -> str:
    rows = _read(_path(workspace))
    if not rows:
        return "No timing log yet."
    run = str(_current_run(rows))
    ends = [r for r in rows if r["run"] == run and r["event"] == "end" and r["seconds"]]
    total_row = next((r for r in ends if r["stage"] == "run"), None)
    stages = [r for r in ends if r["stage"] != "run"]
    total = int(total_row["seconds"]) if total_row else sum(int(r["seconds"]) for r in stages)
    lines = [f"Run {run} ({stages[0]['skill'] if stages and stages[0]['skill'] else 'clinical-evidence'}): "
             f"{total // 60} min {total % 60:02d} s total"]
    agents = [r for r in rows if r["run"] == run and r["event"] == "agent"]
    tok_total = 0
    for r in stages:
        s = int(r["seconds"])
        share = f"{100 * s / total:3.0f}%" if total else "  - "
        mine = [a for a in agents if a["stage"].split("/", 1)[0] == r["stage"]]
        tokens = int(r["tokens"]) if r["tokens"].isdigit() else \
            sum(int(a["tokens"]) for a in mine if a["tokens"].isdigit())
        tok = f" · {tokens:,} tokens" if tokens else ""
        tok_total += tokens
        lines.append(f"  {r['stage']:<16} {_fmt(s)}  {share}{tok}")
        for a in sorted(mine, key=lambda a: -int(a["seconds"] or 0)):
            secs = _fmt(int(a["seconds"])) if a["seconds"].isdigit() else "        ?"
            atok = f" · {int(a['tokens']):,} tokens" if a["tokens"].isdigit() else ""
            lines.append(f"    - {a['stage'].split('/', 1)[1]:<20} {secs}{atok}")
    if tok_total:
        lines.append(f"  agent tokens reported: {tok_total:,}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    try:
        if len(argv) < 2:
            raise ValueError("usage: run_log.py <workspace> start|end <stage> | summary")
        workspace, command = Path(argv[0]), argv[1]
        if command == "summary":
            print(summary(workspace))
            return 0
        if command == "agent" and len(argv) >= 3:
            opts = argv[3:]
            get = lambda flag: opts[opts.index(flag) + 1] if flag in opts and opts.index(flag) + 1 < len(opts) else ""
            secs, tokens = get("--seconds"), get("--tokens").replace(",", "")
            record_agent(workspace, argv[2], get("--stage") or "search",
                         secs if secs.isdigit() else "", tokens if tokens.isdigit() else "")
            return 0
        if command not in ("start", "end") or len(argv) < 3:
            raise ValueError("usage: run_log.py <workspace> start|end <stage> [options]")
        stage, opts = argv[2], argv[3:]
        get = lambda flag: opts[opts.index(flag) + 1] if flag in opts and opts.index(flag) + 1 < len(opts) else ""
        tokens = get("--tokens").replace(",", "")
        seconds = record(workspace, command, stage, skill=get("--skill"),
                         tokens=tokens if tokens.isdigit() else "", note=get("--note"))
        if command == "end" and seconds:
            print(f"{stage}: {int(seconds) // 60} min {int(seconds) % 60:02d} s")
    except Exception as e:  # timing must never break a clinical run
        print(f"WARN: run_log: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
