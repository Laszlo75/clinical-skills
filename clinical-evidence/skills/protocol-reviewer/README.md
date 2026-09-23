# Clinical Protocol Reviewer

A Claude skill that reviews clinical protocols against current national guidelines and published evidence, producing a structured Word document with evidence-graded recommendations.

## What It Does

Upload a clinical protocol (PDF or Word) and the skill will:

1. **Read and parse** the protocol, extracting key clinical topics, drugs, doses, and thresholds
2. **Pick up the evidence base invisibly** — if a recent search already exists in this workspace, it's used automatically; otherwise the `evidence-search` agent (bundled in the same `clinical-evidence` plugin) is dispatched on the fly
3. **Check every reference independently** — a second agent re-reads each record from PubMed and a script cross-checks the two readings
4. **Cross-reference** the protocol against current guidelines and recent evidence
5. **Generate a review document** (.docx) with section-by-section analysis and actionable recommendations
6. **Log to evaluation register** for ongoing quality monitoring

You never have to manage reference files or YAML — the evidence handoff is completely internal.

## Output Files

Each review produces these files:

| File | Purpose |
|------|---------|
| `*_Review_*.md` | Markdown source for the review |
| `*_Review_*.docx` | Formatted Word document (house style), with a traceability matrix appendix |
| `*_Evidence_Table.xlsx` / `.csv` | One row per cited source: design, population, size, certainty, key finding, which recommendations cite it (R-friendly) |
| `*_Traceability.csv` | Protocol statement → review question → evidence → verdict → second review |
| `*_References.bib` | BibTeX file for Zotero/reference manager import |
| `*_PMIDs.txt` | PMID list for Zotero bulk import |

## Requirements

- [Claude Desktop](https://claude.ai/download) or another Claude client with MCP connector support
- The `evidence-search` agent — automatically present because the agent and this skill ship together in the `clinical-evidence` plugin
- A Word-document capability — built into Claude Desktop / Cowork; alternatively **pandoc** (optional)
- **Python 3 with PyYAML** — for the bundled verification, validation and formatting scripts
- The skill is designed for **UK NHS context** (references MHRA, NICE TAs, UK registries)

## Installation

This skill ships as part of the **clinical-evidence** plugin in the [clinical-skills](https://github.com/Laszlo75/clinical-skills) marketplace. Install the whole plugin (not the skill on its own) — `protocol-reviewer` depends on the `evidence-search` agent and the shared contract files for the evidence handoff:

```text
/plugin marketplace add Laszlo75/clinical-skills
/plugin install clinical-evidence@clinical-skills
```

### After installation

1. **Ensure PyYAML is available**: `pip install pyyaml` (needed by the bundled scripts)
2. *Optional:* pandoc, if your environment has no built-in Word-document capability

## Example Prompts

- *"Here's our CMV prophylaxis protocol from 2016. Review it against current evidence."*
- *"Review this protocol — it needs updating. I'm a consultant transplant surgeon."*
- *"Is this protocol still current?"* (with a protocol PDF attached)
- *"I just ran a literature search on AIHA — now review this protocol against what you found."* (the skill picks up the recent evidence automatically from the workspace)

## AI Use & Governance (ISO 42001)

This tool uses AI-assisted evidence synthesis to support clinical protocol review. AI outputs are advisory only and must be critically appraised by a consultant-level clinician before informing protocol changes. The AI system is Claude (Anthropic), accessed via Claude Cowork or Claude Code.

Every review document is generated as an explicit draft with a "DRAFT — NOT FOR CLINICAL USE" callout. The transparency disclaimer (section 6) includes a "Reviewed and approved by" placeholder — the clinician fills this in after reviewing and approving the document. Reference metadata comes from PubMed via the `evidence-search` agent and is independently re-read by the `reference-checker` agent and cross-checked before anything is cited; references that fail the check are excluded.

An evaluation register in the researcher's workspace (`clinical-evidence-register.csv`) logs each review's outcomes and recommendation counts for ongoing quality monitoring.

See [`CLAUDE.md`](CLAUDE.md) for the full AI use policy.

## Trigger Phrases

The skill activates on phrases like: "review this protocol", "update this guideline", "check this against latest evidence", "is this protocol still current", "compare to BTS/NICE/SIGN guidelines", or any request involving a clinical document that needs reviewing.
