# Clinical Evidence Summary

A Claude skill that writes structured narrative evidence summary documents (`.md` + `.docx`) from a verified clinical literature search, with in-text citations, evidence grades, and a formatted reference list.

## What It Does

Ask for an evidence summary on a clinical topic and the skill will:

1. **Pick up the evidence base invisibly** — if a recent search already exists in this workspace, the hidden reference ledger is used automatically; otherwise the `evidence-search` agent (bundled in the same `clinical-evidence` plugin) is dispatched on the fly
2. **Check every reference independently** — a second agent re-reads each record from PubMed and a script cross-checks the two readings; anything pointing at the wrong paper is excluded
3. **Write a narrative evidence summary** with guidelines, recent evidence, conflicting recommendations, emerging evidence, and evidence gaps
4. **Produce a Word document** in the house style
5. **Write Zotero exports** (`.bib` + PMID list) from the same ledger using the shared `ledger_to_exports.py` script

You never have to manage reference files or YAML — the handoff between the search and the summary is completely internal.

## Output Files

Each summary produces four files:

| File                          | Purpose                                        |
|-------------------------------|------------------------------------------------|
| `*_Evidence_Summary_*.md`     | Markdown source for the evidence summary       |
| `*_Evidence_Summary_*.docx`   | Formatted Word document (house style)           |
| `*_References.bib`            | BibTeX file for Zotero/reference manager import |
| `*_PMIDs.txt`                 | PMID list for Zotero bulk import               |

## Requirements

- [Claude Desktop](https://claude.ai/download) or another Claude client with MCP connector support
- The sibling `evidence-search` agent — automatically present because both components ship together in the `clinical-evidence` plugin
- A Word-document capability — built into Claude Desktop / Cowork; alternatively **pandoc** (optional)
- **Python 3 with PyYAML** — for the bundled verification, validation and formatting scripts
- The skill is designed for **UK NHS context** (references MHRA, NICE TAs, UK registries)

## Installation

This skill ships as part of the **clinical-evidence** plugin in the [clinical-skills](https://github.com/Laszlo75/clinical-skills) marketplace. Install the whole plugin (not the skill on its own) — `research-summary` depends on the `evidence-search` agent and on the shared contract files in the plugin's `shared/` directory (schema, validator, export script):

```text
/plugin marketplace add Laszlo75/clinical-skills
/plugin install clinical-evidence@clinical-skills
```

### After installation

1. **Ensure PyYAML is available**: `pip install pyyaml` (needed by the bundled scripts)
2. *Optional:* pandoc, if your environment has no built-in Word-document capability

## Example Prompts

- *"Search the literature on letermovir prophylaxis in kidney transplant recipients and write it up."*
- *"Write the evidence summary now."* (after a search has already been run in the same workspace)
- *"Produce a narrative literature review on letermovir prophylaxis in kidney transplant recipients."*
- *"Summarise the current evidence on DOACs for perioperative anticoagulation for our teaching session."*
- *"I need a formal evidence summary document on CAR-T in relapsed DLBCL for the MDT."*

## AI Use & Governance (ISO 42001)

This tool uses AI-assisted evidence synthesis to produce a narrative clinical evidence summary. AI outputs are advisory only and must be critically appraised by a clinician before informing clinical decisions. The AI system is Claude (Anthropic), accessed via Claude Cowork or Claude Code.

Every evidence summary is generated as an explicit draft with a "DRAFT — NOT FOR CLINICAL USE" callout. The transparency disclaimer includes a "Reviewed and approved by" placeholder — the clinician fills this in after reviewing and approving the document. Reference metadata comes from PubMed via the `evidence-search` agent and is independently re-read by the `reference-checker` agent and cross-checked before anything is cited; references that fail the check are excluded.

See [`CLAUDE.md`](CLAUDE.md) for the full AI use policy.

## Trigger Phrases

The skill activates on phrases like: "write the evidence summary", "produce a narrative literature review", "evidence summary document", "write up the evidence on", "summarise the literature on", or any request for a written evidence document on a clinical topic.
