import csv
from datetime import datetime, timedelta

import run_log


def rows(ws):
    with (ws / ".clinical-evidence" / "run_log.csv").open() as f:
        return list(csv.DictReader(f))


def shift_last(ws, seconds):
    """Backdate the last row so durations are deterministic."""
    path = ws / ".clinical-evidence" / "run_log.csv"
    data = rows(ws)
    ts = datetime.fromisoformat(data[-1]["timestamp_utc"]) - timedelta(seconds=seconds)
    data[-1]["timestamp_utc"] = ts.isoformat()
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=run_log.COLUMNS)
        w.writeheader()
        w.writerows(data)


def test_stage_durations_tokens_and_summary(tmp_path):
    run_log.main([str(tmp_path), "start", "run", "--skill", "protocol-reviewer"])
    shift_last(tmp_path, 900)
    run_log.main([str(tmp_path), "start", "search"])
    shift_last(tmp_path, 600)
    run_log.main([str(tmp_path), "end", "search", "--tokens", "182,400"])
    run_log.main([str(tmp_path), "end", "run"])
    data = rows(tmp_path)
    search_end = next(r for r in data if r["stage"] == "search" and r["event"] == "end")
    assert 599 <= int(search_end["seconds"]) <= 601 and search_end["tokens"] == "182400"
    assert all(r["run"] == "1" and r["skill"] == "protocol-reviewer" for r in data)
    text = run_log.summary(tmp_path)
    assert text.startswith("Run 1 (protocol-reviewer): 15 min")
    assert "search" in text and "182,400 tokens" in text and "67%" in text


def test_new_run_increments(tmp_path):
    run_log.main([str(tmp_path), "start", "run", "--skill", "research-summary"])
    run_log.main([str(tmp_path), "start", "run", "--skill", "research-summary"])
    assert [r["run"] for r in rows(tmp_path)] == ["1", "2"]


def test_never_fails(tmp_path, capsys):
    assert run_log.main([]) == 0
    assert run_log.main([str(tmp_path), "bogus"]) == 0
    assert "WARN" in capsys.readouterr().out
    assert run_log.summary(tmp_path / "nowhere") == "No timing log yet."


def test_agent_rows_show_the_bottleneck(tmp_path):
    run_log.main([str(tmp_path), "start", "run", "--skill", "protocol-reviewer"])
    run_log.main([str(tmp_path), "start", "search"])
    shift_last(tmp_path, 760)
    run_log.main([str(tmp_path), "agent", "guidelines-uk", "--stage", "search",
                  "--seconds", "742", "--tokens", "410,000"])
    run_log.main([str(tmp_path), "agent", "literature-1", "--stage", "search",
                  "--seconds", "330", "--tokens", "150000"])
    run_log.main([str(tmp_path), "end", "search"])
    run_log.main([str(tmp_path), "end", "run"])
    text = run_log.summary(tmp_path)
    lines = text.splitlines()
    search = next(i for i, l in enumerate(lines) if l.strip().startswith("search"))
    assert "560,000 tokens" in lines[search]            # stage tokens = sum of its agents
    assert "guidelines-uk" in lines[search + 1] and "12 min 22 s" in lines[search + 1]
    assert "literature-1" in lines[search + 2]           # slowest first
    assert "agent tokens reported: 560,000" in text
