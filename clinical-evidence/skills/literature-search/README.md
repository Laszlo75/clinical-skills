# Clinical Literature Search

A Claude skill that searches PubMed, Scholar Gateway, and national guideline websites for clinical evidence on a given topic, producing a verified reference ledger plus Zotero-friendly export files. The narrative evidence summary document is produced by the sibling `research-summary` skill (same plugin) — this skill handles the search and verification.

## What It Does

Provide a clinical topic and the skill will:

1. **Parse and confirm** — derive MeSH terms, identify relevant guideline bodies, confirm scope with the researcher
2. **Dispatch the `evidence-search` agent** — the tool-heavy search workflow (PubMed + Scholar Gateway + guideline fetch + reference verification) runs in an isolated subagent context so the main conversation stays clean
3. **Validate the ledger** — runs the bundled executable validator against the canonical hidden ledger the agent produced
4. **Export for Zotero** — writes `.bib` and PMID list files from the validated ledger
5. **Point at the next skill** — tells the researcher how to produce a narrative evidence summary (`research-summary`) or review a clinical protocol (`protocol-reviewer`) against the same evidence

## Output Files

Each search produces two user-facing files:

| File               | Purpose                                          |
|--------------------|--------------------------------------------------|
| `*_References.bib` | BibTeX file for Zotero/reference manager import  |
| `*_PMIDs.txt`      | PMID list for Zotero bulk import                 |

The skill also writes a hidden reference ledger at `.literature_search_ledger.yaml` in the same workspace. This is an internal artifact used for quality control (preventing DOI hallucination via incremental write-to-file) and for downstream skills in the same plugin (`research-summary`, `protocol-reviewer`) to consume automatically. Researchers do not need to open, edit, or manage this file.

**Want a narrative evidence summary document?** Run the sibling `research-summary` skill after this one — it reads the ledger and produces `.md` + `.docx` files.

## Requirements

- [Claude Desktop](https://claude.ai/download) or another Claude client with MCP connector support
- **Recommended model**: Claude Opus 4.6 — the literature search, evidence appraisal, and reference integrity steps benefit from stronger reasoning capability
- The following MCP connectors enabled:
  - **PubMed** — literature search and article metadata
  - **Scholar Gateway** — semantic search across peer-reviewed literature
- **Python 3 + PyYAML** — used by the bundled ledger validator
- The skill is designed for **UK NHS context** (references MHRA, NICE TAs, UK registries)

### Optional MCP connectors (enhance coverage)

- **bioRxiv** — searches medRxiv/bioRxiv for preprints on rapidly evolving topics
- **Clinical Trials** — searches ClinicalTrials.gov for ongoing/completed trials to enrich the Evidence Gaps section

## Installation

This skill ships as part of the **clinical-evidence** plugin in the [clinical-skills](https://github.com/Laszlo75/clinical-skills) marketplace. Install the whole plugin (not the skill on its own) so `literature-search`, its sibling `research-summary` and `protocol-reviewer` skills, and the shared `evidence-search` agent all stay in sync:

```text
/plugin marketplace add Laszlo75/clinical-skills
/plugin install clinical-evidence@clinical-skills
```

### After installation

1. **Enable the required MCP connectors** in Claude Desktop (Settings → Connectors):
   - **PubMed** — for literature search, article metadata, and full text retrieval
   - **Scholar Gateway** — for semantic search across peer-reviewed literature
2. **Ensure PyYAML is available**: `pip install pyyaml` (needed by the bundled ledger validator)

## Example Prompts

- *"Search for evidence on CMV prophylaxis in solid organ transplant recipients"*
- *"What does the latest literature say about perioperative anticoagulation in DOAC patients?"*
- *"Literature search on rituximab dosing for ABO-incompatible kidney transplantation"*

## Integration with research-summary and protocol-reviewer

The two consumer skills in this plugin pick up this skill's hidden ledger invisibly:

- **Run literature-search first, then `research-summary` in the same workspace** — produces a narrative evidence summary `.md` + `.docx`, reading the existing ledger.
- **Run literature-search first, then `protocol-reviewer` in the same workspace** — reviews an uploaded protocol against the existing ledger.
- **Skip straight to `research-summary` or `protocol-reviewer`** — each consumer auto-triggers the `evidence-search` agent if no ledger exists yet, then loops back to its own workflow.

Either way, the clinician never has to manage reference files or YAML between the two steps. See [`references/consumer_integration.md`](references/consumer_integration.md) for the integration contract used by all downstream skills.

## Related Components

- **research-summary** — produces a narrative evidence summary document from this skill's ledger. Ships in the same `clinical-evidence` plugin.
- **protocol-reviewer** — reviews clinical protocols against the same ledger. Ships in the same plugin.
- **evidence-search** (agent) — the isolated subagent that runs the actual search work on behalf of all three skills. Ships at `clinical-evidence/agents/evidence-search.md`.

## AI Use & Governance (ISO 42001)

This tool uses AI-assisted evidence synthesis. AI outputs are advisory only and must be critically appraised by a clinician. The AI system is Claude (Anthropic), accessed via Claude Desktop with PubMed and Scholar Gateway integrations.

References are retrieved programmatically from PubMed by the `evidence-search` agent and verified against source metadata character-by-character before the ledger is handed off. The bundled validator enforces structural correctness before any export files are written.

See [`CLAUDE.md`](CLAUDE.md) for the full AI use policy.

## Trigger Phrases

The skill activates on phrases like: "literature search", "search PubMed", "find evidence on", "what does the latest evidence say about", "evidence review", "reference list for", or any request for clinical evidence on a specific topic.
