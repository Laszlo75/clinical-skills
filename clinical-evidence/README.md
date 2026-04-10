# clinical-evidence

A Claude Code plugin for clinical evidence synthesis and protocol review. Bundles two co-designed skills that work together invisibly to produce draft evidence summaries and protocol review documents for a UK NHS clinical audience.

## What's inside

Two skills that share a hidden, verified reference ledger:

| Skill | What it does |
|-------|---------------|
| [`literature-search`](./skills/literature-search/) | Searches PubMed, Scholar Gateway, and national guideline bodies on a clinical topic. Verifies every reference against PubMed metadata. Produces a structured evidence summary (`.md` + `.docx`), a BibTeX file, and a PMID list. |
| [`protocol-reviewer`](./skills/protocol-reviewer/) | Reads an uploaded clinical protocol (PDF/Word), cross-references it against current guidelines and published evidence, and produces a structured `.docx` review document with actionable recommendations and evidence grades. |

The two skills are designed to be used together — the researcher never has to manage handoff files or reference lists between them. The evidence gathered by `literature-search` is picked up automatically by `protocol-reviewer` via a hidden reference ledger in the workspace.

## How it works in practice

Two typical workflows:

**Workflow 1 — Search first, then review:**

1. *"Literature search on CMV prophylaxis in solid organ transplant recipients"* → `literature-search` runs, producing an evidence summary and reference files.
2. Upload a protocol. *"Review this protocol"* → `protocol-reviewer` finds the reference ledger from the previous search and produces the review document without asking about files.

**Workflow 2 — Review directly:**

1. Upload a protocol. *"Review this protocol against current guidelines"* → `protocol-reviewer` finds no ledger in the workspace, auto-triggers `literature-search` on the protocol's topic, and then produces the review.

Both workflows produce the same 4 + 4 user-facing files (one set per skill):

| File | Purpose |
|------|---------|
| `*_Evidence_Summary_*.md` / `*_Review_*.md` | Markdown source |
| `*_Evidence_Summary_*.docx` / `*_Review_*.docx` | Formatted Word document |
| `*_References.bib` | BibTeX for Zotero |
| `*_PMIDs.txt` | PMID list for Zotero bulk import |

## Installation

```text
/plugin marketplace add Laszlo75/clinical-skills
/plugin install clinical-evidence
```

## Requirements

- [Claude Desktop](https://claude.ai/download) with MCP connector support
- Recommended model: **Claude Opus 4.6**
- MCP connectors enabled:
  - **PubMed** — literature search and article metadata
  - **Scholar Gateway** — semantic search
  - Optional: **bioRxiv** (preprints), **Clinical Trials** (ongoing trials)
- **pandoc** — markdown to `.docx` (`brew install pandoc` on macOS, `sudo apt install pandoc` on Linux)
- **Python 3 + PyYAML** — used by the ledger validator

## Example prompts

- *"Search for evidence on CMV prophylaxis in solid organ transplant recipients"*
- *"What does the latest literature say about perioperative anticoagulation in DOAC patients?"*
- *"Review this rituximab protocol against current guidelines"*
- *"Check this ABO-incompatible transplant protocol for updates"*

## Per-skill documentation

Each skill has its own README and `CLAUDE.md` inside its folder:

- [`skills/literature-search/README.md`](./skills/literature-search/README.md)
- [`skills/literature-search/CLAUDE.md`](./skills/literature-search/CLAUDE.md)
- [`skills/protocol-reviewer/README.md`](./skills/protocol-reviewer/README.md)
- [`skills/protocol-reviewer/CLAUDE.md`](./skills/protocol-reviewer/CLAUDE.md)

## AI Use & Governance (ISO 42001)

These skills are AI-assisted. Every generated document carries a "DRAFT — NOT FOR CLINICAL USE" callout and a transparency disclaimer naming the model, the MCP sources used, and the skill version. References are retrieved programmatically from PubMed and verified character-by-character before they reach any user-facing document. Clinical judgement and final sign-off remain the responsibility of the reviewing clinician and the approving MDT.

## License

MIT. See the [marketplace LICENSE](../LICENSE).
