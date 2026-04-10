# Clinical Evidence Summary Writer

A Claude skill that writes structured narrative evidence summary documents (`.md` + `.docx`) from a verified clinical literature search, with in-text citations, evidence grades, and a formatted reference list.

## What It Does

Ask for an evidence summary on a clinical topic and the skill will:

1. **Pick up the evidence base invisibly** — if a recent literature search already exists in this workspace, the hidden reference ledger is used automatically; otherwise the sibling `evidence-search` agent (bundled in the same `clinical-evidence` plugin) is dispatched on the fly
2. **Validate** the ledger using the bundled executable validator
3. **Write a narrative evidence summary** with guidelines, recent evidence, conflicting recommendations, emerging evidence, and evidence gaps
4. **Convert to a Word document** using pandoc with the bundled reference template

You never have to manage reference files or YAML — the handoff between the search and the summary is completely internal.

## Output Files

Each summary produces two files:

| File                          | Purpose                                        |
|-------------------------------|------------------------------------------------|
| `*_Evidence_Summary_*.md`     | Markdown source for the evidence summary       |
| `*_Evidence_Summary_*.docx`   | Formatted Word document (via pandoc)           |

**Need `.bib` and PMID files for Zotero?** Run the sibling `literature-search` skill — those exports belong to that skill. If you've already run `literature-search` in the same workspace, the files are already there.

## Requirements

- [Claude Desktop](https://claude.ai/download) or another Claude client with MCP connector support
- The sibling `evidence-search` agent — automatically present because both components ship together in the `clinical-evidence` plugin
- **pandoc** — for markdown to `.docx` conversion
- **Python 3 with PyYAML** — for running the bundled ledger validator
- The skill is designed for **UK NHS context** (references MHRA, NICE TAs, UK registries)

## Installation

This skill ships as part of the **clinical-evidence** plugin in the [clinical-skills](https://github.com/Laszlo75/clinical-skills) marketplace. Install the whole plugin (not the skill on its own) — `research-summary` depends on the `evidence-search` agent and on the ledger contract files in `literature-search/references/`:

```text
/plugin marketplace add Laszlo75/clinical-skills
/plugin install clinical-evidence@clinical-skills
```

### After installation

1. **Install pandoc**: `brew install pandoc` (macOS) or `sudo apt install pandoc` (Linux)
2. **Ensure PyYAML is available**: `pip install pyyaml` (needed by the bundled ledger validator)

## Example Prompts

- *"Write the evidence summary now."* (after running `literature-search` in the same workspace)
- *"Produce a narrative literature review on letermovir prophylaxis in kidney transplant recipients."*
- *"Summarise the current evidence on DOACs for perioperative anticoagulation for our teaching session."*
- *"I need a formal evidence summary document on CAR-T in relapsed DLBCL for the MDT."*

## AI Use & Governance (ISO 42001)

This tool uses AI-assisted evidence synthesis to produce a narrative clinical evidence summary. AI outputs are advisory only and must be critically appraised by a clinician before informing clinical decisions. The AI system is Claude (Anthropic), accessed via Claude Desktop.

Every evidence summary is generated as an explicit draft with a "DRAFT — NOT FOR CLINICAL USE" callout. The transparency disclaimer includes a "Reviewed and approved by" placeholder — the clinician fills this in after reviewing and approving the document. References are copied verbatim from the YAML reference ledger, which was verified against PubMed by the `evidence-search` agent.

See [`CLAUDE.md`](CLAUDE.md) for the full AI use policy.

## Trigger Phrases

The skill activates on phrases like: "write the evidence summary", "produce a narrative literature review", "evidence summary document", "write up the evidence on", "summarise the literature on", or any request for a written evidence document on a clinical topic.
