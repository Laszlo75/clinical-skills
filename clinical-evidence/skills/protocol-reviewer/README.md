# Clinical Protocol Reviewer

A Claude skill that reviews clinical protocols against current national guidelines and published evidence, producing a structured Word document with evidence-graded recommendations.

## What It Does

Upload a clinical protocol (PDF or Word) and the skill will:

1. **Read and parse** the protocol, extracting key clinical topics, drugs, doses, and thresholds
2. **Pick up the evidence base invisibly** — if a recent literature search already exists in this workspace, it's used automatically; otherwise the sibling `literature-search` skill (bundled in the same `clinical-evidence` plugin) is triggered on the fly
3. **Cross-reference** the protocol against current guidelines and recent evidence
4. **Generate a review document** (.docx) with section-by-section analysis and actionable recommendations
5. **Log to evaluation register** for ongoing quality monitoring

You never have to manage reference files or YAML — the handoff between the two skills is completely internal.

## Output Files

Each review produces four files:

| File | Purpose |
|------|---------|
| `*_Review_*.md` | Markdown source for the review |
| `*_Review_*.docx` | Formatted Word document (via pandoc) |
| `*_References.bib` | BibTeX file for Zotero/reference manager import |
| `*_PMIDs.txt` | PMID list for Zotero bulk import |

## Requirements

- [Claude Desktop](https://claude.ai/download) or another Claude client with MCP connector support
- The sibling `literature-search` skill — automatically present because both skills ship together in the `clinical-evidence` plugin
- **pandoc** — for markdown to .docx conversion
- **Python 3 with PyYAML** — for running the bundled ledger validator
- The skill is designed for **UK NHS context** (references MHRA, NICE TAs, UK registries)

## Installation

This skill ships as part of the **clinical-evidence** plugin in the [clinical-skills](https://github.com/Laszlo75/clinical-skills) marketplace. Install the whole plugin (not the skill on its own) — `protocol-reviewer` depends on its sibling `literature-search` for the evidence handoff:

```text
/plugin marketplace add Laszlo75/clinical-skills
/plugin install clinical-evidence@clinical-skills
```

### After installation

1. **Install pandoc**: `brew install pandoc` (macOS) or `sudo apt install pandoc` (Linux)
2. **Ensure PyYAML is available**: `pip install pyyaml` (needed by the bundled ledger validator)

## Example Prompts

- *"Here's our CMV prophylaxis protocol from 2016. Review it against current evidence."*
- *"Review this protocol — it needs updating. I'm a consultant transplant surgeon."*
- *"Is this protocol still current?"* (with a protocol PDF attached)
- *"I just ran a literature search on AIHA — now review this protocol against what you found."* (the skill picks up the recent evidence automatically from the workspace)

## AI Use & Governance (ISO 42001)

This tool uses AI-assisted evidence synthesis to support clinical protocol review. AI outputs are advisory only and must be critically appraised by a consultant-level clinician before informing protocol changes. The AI system is Claude (Anthropic), accessed via Claude Desktop.

Every review document is generated as an explicit draft with a "DRAFT — NOT FOR CLINICAL USE" callout. The transparency disclaimer (section 6) includes a "Reviewed and approved by" placeholder — the clinician fills this in after reviewing and approving the document. References are copied verbatim from the YAML reference ledger, which was verified against PubMed by the literature-search skill.

A local evaluation register (`reviews/evaluation_register.csv`, gitignored) logs each review's outcomes and recommendation counts for ongoing quality monitoring.

See [`CLAUDE.md`](CLAUDE.md) for the full AI use policy.

## Trigger Phrases

The skill activates on phrases like: "review this protocol", "update this guideline", "check this against latest evidence", "is this protocol still current", "compare to BTS/NICE/SIGN guidelines", or any request involving a clinical document that needs reviewing.
