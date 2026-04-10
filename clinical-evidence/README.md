# clinical-evidence

A Claude Code plugin for clinical evidence synthesis and protocol review. Bundles three co-designed skills and one shared agent that work together invisibly to produce verified reference ledgers, narrative evidence summaries, and protocol review documents for a UK NHS clinical audience.

## What's inside

Three skills that share one hidden, verified reference ledger:

| Skill | What it does |
| --- | --- |
| [`literature-search`](./skills/literature-search/) | User-facing trigger for clinical literature searches. Confirms scope with the researcher, dispatches the `evidence-search` agent, validates the hidden ledger the agent produces, and writes Zotero export files (`.bib` + PMID list). Does not produce narrative documents — those belong to the two consumer skills below. |
| [`research-summary`](./skills/research-summary/) | Writes a structured narrative evidence summary document (`.md` + `.docx`) from the ledger. Covers guidelines, recent evidence, conflicting recommendations, emerging evidence, and evidence gaps. Auto-triggers `evidence-search` if no ledger exists in the workspace. |
| [`protocol-reviewer`](./skills/protocol-reviewer/) | Reads an uploaded clinical protocol (PDF/Word), cross-references it against the ledger, and produces a section-by-section `.docx` review document with actionable recommendations and evidence grades. Auto-triggers `evidence-search` if no ledger exists. |

### The `evidence-search` agent

All three skills share a single subagent at [`agents/evidence-search.md`](./agents/evidence-search.md) that runs the actual PubMed + Scholar Gateway + guideline search work in isolated context. Researchers never interact with the agent directly — it's dispatched automatically by whichever skill needs a fresh ledger. Running the search inside an agent keeps the tool-heavy traffic (PubMed metadata calls, Scholar Gateway passages, full-text retrievals, reference verification) out of the main conversation, so downstream synthesis has a clean slate to work from.

## How it works in practice

Three typical workflows:

**Workflow 1 — Search → narrative summary:**

1. *"Literature search on CMV prophylaxis in solid organ transplant recipients"* → `literature-search` activates, confirms scope, dispatches `evidence-search`, validates the ledger, and writes `.bib` + PMID files.
2. *"Now write the evidence summary document"* → `research-summary` finds the existing ledger, validates it, and writes `.md` + `.docx`.

**Workflow 2 — Search → protocol review:**

1. *"Literature search on ABO-incompatible kidney transplantation"* → `literature-search` runs as above.
2. Upload a protocol. *"Review this protocol"* → `protocol-reviewer` finds the ledger from the previous search and produces the review document without asking about files.

**Workflow 3 — Review directly:**

1. Upload a protocol. *"Review this protocol against current guidelines"* → `protocol-reviewer` finds no ledger, dispatches the `evidence-search` agent on the protocol's topic in isolated context, and then produces the review.

In all three workflows, the ledger handoff is invisible to the researcher — there are no reference files or YAML to manage between skills.

## Output files

Each skill has its own output set. No duplication between skills.

| Skill | User-facing files |
| --- | --- |
| `literature-search` | `*_References.bib`, `*_PMIDs.txt` |
| `research-summary` | `*_Evidence_Summary_*.md`, `*_Evidence_Summary_*.docx` |
| `protocol-reviewer` | `*_Review_*.md`, `*_Review_*.docx`, `*_References.bib`, `*_PMIDs.txt` |

The hidden `.literature_search_ledger.yaml` is present in the workspace after any skill runs but is never listed as a user-facing output.

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
- *"Write the evidence summary document now."*
- *"Review this rituximab protocol against current guidelines"*
- *"Check this ABO-incompatible transplant protocol for updates"*

## Per-component documentation

Each skill has its own README and `CLAUDE.md` inside its folder:

- [`skills/literature-search/README.md`](./skills/literature-search/README.md)
- [`skills/literature-search/CLAUDE.md`](./skills/literature-search/CLAUDE.md)
- [`skills/research-summary/README.md`](./skills/research-summary/README.md)
- [`skills/research-summary/CLAUDE.md`](./skills/research-summary/CLAUDE.md)
- [`skills/protocol-reviewer/README.md`](./skills/protocol-reviewer/README.md)
- [`skills/protocol-reviewer/CLAUDE.md`](./skills/protocol-reviewer/CLAUDE.md)
- [`agents/evidence-search.md`](./agents/evidence-search.md) — the shared search agent

## AI Use & Governance (ISO 42001)

These components are AI-assisted. Every generated document carries a "DRAFT — NOT FOR CLINICAL USE" callout and a transparency disclaimer naming the model, the MCP sources used, and the plugin version. References are retrieved programmatically from PubMed and verified character-by-character before they reach any user-facing document. Clinical judgement and final sign-off remain the responsibility of the reviewing clinician and the approving MDT.

## License

MIT. See the [marketplace LICENSE](../LICENSE).
