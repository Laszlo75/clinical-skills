"""Structural checks that Cowork / Claude Code enforce when loading the plugin.

A skill that breaks these rules is dropped silently (2.1.0 shipped with a
1,353-character research-summary description and Cowork showed only one skill).
"""
import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "clinical-evidence"
SKILLS = sorted((PLUGIN / "skills").glob("*/SKILL.md"))
AGENTS = sorted((PLUGIN / "agents").glob("*.md"))


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} must start with YAML frontmatter"
    return yaml.safe_load(text.split("---", 2)[1])


def test_expected_components_present():
    assert {p.parent.name for p in SKILLS} == {"research-summary", "protocol-reviewer"}
    assert {p.stem for p in AGENTS} == {"evidence-search", "guideline-search", "second-reviewer"}


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_skill_frontmatter_limits(path):
    fm = frontmatter(path)
    name, description = fm.get("name"), fm.get("description")
    assert name == path.parent.name, "skill name must match its folder"
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) and len(name) <= 64
    assert isinstance(description, str) and description.strip()
    assert len(description) <= 1024, f"description is {len(description)} chars (max 1024)"
    assert not re.search(r"<[^>]+>", description), "no XML/HTML tags in skill descriptions"


@pytest.mark.parametrize("path", AGENTS, ids=lambda p: p.stem)
def test_agent_frontmatter(path):
    fm = frontmatter(path)
    assert fm.get("name") == path.stem
    assert isinstance(fm.get("description"), str) and fm["description"].strip()


def test_manifests_agree():
    plugin = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
    entry = next(p for p in market["plugins"] if p["name"] == plugin["name"])
    assert (ROOT / entry["source"]).resolve() == PLUGIN.resolve()
    assert re.fullmatch(r"\d+\.\d+\.\d+", plugin["version"])


def test_agent_models():
    models = {p.stem: (frontmatter(p).get("model"), frontmatter(p).get("effort")) for p in AGENTS}
    assert models["guideline-search"] == ("opus", "medium")   # guidelines are the backbone
    assert models["evidence-search"][0] == "sonnet"
    for model, effort in models.values():
        assert effort in (None, "low", "medium", "high", "xhigh", "max")
