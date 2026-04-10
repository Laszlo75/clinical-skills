# Clinical Literature Search

A Claude skill that searches PubMed, Scholar Gateway, and national guideline websites for clinical evidence on a given topic, producing a structured evidence summary document and verified reference list.

## What It Does

Provide a clinical topic and the skill will:

1. **Parse and plan** — derive MeSH terms, identify relevant guideline bodies
2. **Search national guidelines** (BTS, NICE, KDIGO, BSH, SIGN, etc.) via web search
3. **Search published evidence** using both PubMed (keyword/MeSH) and Scholar Gateway (semantic search)
4. **Verify references** — every DOI, title, and first author is re-checked character-by-character against PubMed; no fabricated identifiers
5. **Generate an evidence summary** (.docx) with guidelines, recent evidence, and evidence gaps
6. **Export references** as BibTeX (.bib) and PMID list (.txt) for Zotero import

## Output Files

Each search produces four user-facing files:

| File | Purpose |
|------|---------|
| `*_Evidence_Summary_*.md` | Markdown source for the evidence summary |
| `*_Evidence_Summary_*.docx` | Formatted Word document (via pandoc) |
| `*_References.bib` | BibTeX file for Zotero/reference manager import |
| `*_PMIDs.txt` | PMID list for Zotero bulk import |

The skill also writes a hidden reference ledger at `.literature_search_ledger.yaml` in the same workspace. This is an internal artifact used for quality control (preventing DOI hallucination via incremental write-to-file) and for downstream skills like `protocol-reviewer` (its sibling in this plugin) to consume automatically. Researchers do not need to open, edit, or manage this file.

## Requirements

- [Claude Desktop](https://claude.ai/download) or another Claude client with MCP connector support
- **Recommended model**: Claude Opus 4.6 — the literature search, evidence appraisal, and reference integrity steps benefit from stronger reasoning capability
- The following MCP connectors enabled:
  - **PubMed** — literature search and article metadata
  - **Scholar Gateway** — semantic search across peer-reviewed literature
- **pandoc** — for markdown to .docx conversion
- The skill is designed for **UK NHS context** (references MHRA, NICE TAs, UK registries)

### Optional MCP connectors (enhance coverage)

- **bioRxiv** — searches medRxiv/bioRxiv for preprints on rapidly evolving topics
- **Clinical Trials** — searches ClinicalTrials.gov for ongoing/completed trials to enrich the Evidence Gaps section

## Installation

This skill ships as part of the **clinical-evidence** plugin in the [clinical-skills](https://github.com/Laszlo75/clinical-skills) marketplace. Install the whole plugin (not the skill on its own) so `literature-search` and its sibling `protocol-reviewer` stay in sync:

```text
/plugin marketplace add Laszlo75/clinical-skills
/plugin install clinical-evidence@clinical-skills
```

### After installation

1. **Enable the required MCP connectors** in Claude Desktop (Settings → Connectors):
   - **PubMed** — for literature search, article metadata, and full text retrieval
   - **Scholar Gateway** — for semantic search across peer-reviewed literature
2. **Install pandoc**: `brew install pandoc` (macOS) or `sudo apt install pandoc` (Linux)

## Example Prompts

- *"Search for evidence on CMV prophylaxis in solid organ transplant recipients"*
- *"What does the latest literature say about perioperative anticoagulation in DOAC patients?"*
- *"Literature search on rituximab dosing for ABO-incompatible kidney transplantation"*

## Integration with protocol-reviewer

The `protocol-reviewer` skill (sibling in this plugin) picks up this skill's output invisibly. Two common workflows:

- **Run literature-search first in a workspace, then review a protocol in the same workspace** — protocol-reviewer silently discovers the hidden ledger already present and uses it.
- **Upload a protocol without running a search first** — protocol-reviewer auto-triggers this skill on the fly, and then consumes the ledger it just produced.

Either way, the clinician never has to manage reference files or YAML between the two steps. See [`references/consumer_integration.md`](references/consumer_integration.md) for the integration contract used by all downstream skills.

## Related Skills

- **protocol-reviewer** — reviews clinical protocols against evidence, consuming this skill's hidden YAML ledger. Ships in the same `clinical-evidence` plugin.

## AI Use & Governance (ISO 42001)

This tool uses AI-assisted evidence synthesis. AI outputs are advisory only and must be critically appraised by a clinician. The AI system is Claude (Anthropic), accessed via Claude Desktop with PubMed and Scholar Gateway integrations.

Every evidence summary is generated as a draft with a "DRAFT — NOT FOR CLINICAL USE" callout and transparency disclaimer. References are retrieved programmatically from PubMed and verified against source metadata.

See [`CLAUDE.md`](CLAUDE.md) for the full AI use policy.

## Trigger Phrases

The skill activates on phrases like: "literature search", "search PubMed", "find evidence on", "what does the latest evidence say about", "evidence review", "reference list for", or any request for clinical evidence on a specific topic.
