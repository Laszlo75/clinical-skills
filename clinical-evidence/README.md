# clinical-evidence

A Claude Code plugin for clinical evidence synthesis and protocol review. Bundles two co-designed skills and three agents that work together invisibly to produce verified reference ledgers, narrative evidence summaries, and protocol review documents for a UK NHS clinical audience.

## What's inside

Two skills that share one hidden, verified reference ledger:

| Skill | What it does |
| --- | --- |
| [`research-summary`](./skills/research-summary/) | The user-facing entry point for a literature search or evidence summary. Dispatches the `evidence-search` agent (or reuses a ledger already in the workspace), then writes a structured narrative evidence summary (`.md` + `.docx`) plus Zotero export files (`.bib` + PMID list). Covers guidelines, recent evidence, conflicting recommendations, emerging evidence, and evidence gaps. |
| [`protocol-reviewer`](./skills/protocol-reviewer/) | Reads an uploaded clinical protocol (PDF/Word), cross-references it against the ledger, and produces a section-by-section `.docx` review document with actionable recommendations, evidence grades, and Zotero exports. Dispatches `evidence-search` if no ledger exists. |

### The agents

Both skills share a single subagent at [`agents/evidence-search.md`](./agents/evidence-search.md) that runs the actual PubMed + Scholar Gateway + guideline search work in isolated context. Researchers never interact with the agent directly — it's dispatched automatically by whichever skill needs a fresh ledger. Running the search inside an agent keeps the tool-heavy traffic (PubMed metadata calls, Scholar Gateway passages, full-text retrievals) out of the main conversation, so downstream synthesis has a clean slate to work from.

Searches run as several `evidence-search` agents in parallel — one per cluster of questions — and are merged. The skill then checks every PMID/DOI pair independently with PubMed's ID converter, and `shared/scripts/verify_references.py` excludes anything that doesn't match before a single reference is cited.

## How it works in practice

Three typical workflows:

**Workflow 1 — Search → narrative summary:**

1. *"Literature search on CMV prophylaxis in solid organ transplant recipients"* → `research-summary` activates, dispatches `evidence-search`, validates the ledger, and writes the evidence summary (`.md` + `.docx`) plus `.bib` + PMID exports — all in one pass.

**Workflow 2 — Search → protocol review:**

1. *"Literature search on ABO-incompatible kidney transplantation, then write it up"* → `research-summary` runs as above.
2. Upload a protocol. *"Review this protocol"* → `protocol-reviewer` finds the ledger from the previous search and produces the review document without asking about files.

**Workflow 3 — Review directly:**

1. Upload a protocol. *"Review this protocol against current guidelines"* → `protocol-reviewer` finds no ledger, dispatches the `evidence-search` agent on the protocol's topic in isolated context, and then produces the review.

In all three workflows, the ledger handoff is invisible to the researcher — there are no reference files or YAML to manage between skills.

## Output files

Each skill has its own output set. No duplication between skills.

| Skill | User-facing files |
| --- | --- |
| `research-summary` | `*_Evidence_Summary_*.md`, `*_Evidence_Summary_*.docx`, `*_References.bib`, `*_PMIDs.txt` |
| `protocol-reviewer` | `*_Review_*.md`, `*_Review_*.docx`, `*_Evidence_Table.xlsx` (+ `.csv`), `*_Traceability.csv`, `*_References.bib`, `*_PMIDs.txt` |

`protocol-reviewer` also appends one row per review to `clinical-evidence-register.csv` in the workspace — the clinician's audit trail (MDT outcome, appraiser, and notes columns are left for you to fill in; the CSV reads straight into R).

The hidden `.literature_search_ledger.yaml` is present in the workspace after any skill runs but is never listed as a user-facing output. The `evidence-search` agent produces only this hidden ledger — no user-facing files of its own.

## Installation

```text
/plugin marketplace add Laszlo75/clinical-skills
/plugin install clinical-evidence
```

## Requirements

- [Claude Desktop](https://claude.ai/download) — Claude Cowork or Claude Code — with MCP connector support
- **Recommended model: Claude Opus 5.5 (`claude-opus-5-5`) at high effort** for the skills; the search agents run on Claude Sonnet. This is the one place the plugin names a specific model version; everything else refers to "the latest Claude Opus".
  - *Claude Code:* the skills pin `model: opus` + `effort: high`, the `evidence-search` agent pins `model: sonnet` (retrieval and tagging) and the `second-reviewer` agent pins `model: opus`.
  - *Claude Cowork:* the model is chosen in the app — select Opus 5.5 and enable extended thinking before running a skill.
- MCP connectors enabled:
  - **PubMed** — literature search and article metadata
  - **Scholar Gateway** — semantic search
  - Optional: **bioRxiv** (preprints), **Clinical Trials** (ongoing trials)
- **Python 3 + PyYAML** — for the bundled verification, validation, formatting and export scripts
- *Optional:* **pandoc** — only needed if your environment has no built-in Word-document capability (Claude Desktop / Cowork create `.docx` natively)

## Example prompts

- *"Search for evidence on CMV prophylaxis in solid organ transplant recipients"*
- *"What does the latest literature say about perioperative anticoagulation in DOAC patients?"*
- *"Write the evidence summary document now."*
- *"Review this rituximab protocol against current guidelines"*
- *"Check this ABO-incompatible transplant protocol for updates"*

## Per-component documentation

Each skill has its own README and `CLAUDE.md` inside its folder:

- [`skills/research-summary/README.md`](./skills/research-summary/README.md)
- [`skills/research-summary/CLAUDE.md`](./skills/research-summary/CLAUDE.md)
- [`skills/protocol-reviewer/README.md`](./skills/protocol-reviewer/README.md)
- [`skills/protocol-reviewer/CLAUDE.md`](./skills/protocol-reviewer/CLAUDE.md)
- [`agents/evidence-search.md`](./agents/evidence-search.md) — the shared search agent
- [`agents/second-reviewer.md`](./agents/second-reviewer.md) — challenges each protocol-review judgement against its evidence
- [`shared/references/ledger_schema.md`](./shared/references/ledger_schema.md) — the ledger contract
- [`shared/references/consumer_integration.md`](./shared/references/consumer_integration.md) — how a consumer plugs in

## AI Use & Governance (ISO 42001)

These components are AI-assisted. Every generated document carries a "DRAFT — NOT FOR CLINICAL USE" callout and a transparency disclaimer naming the model, the MCP sources used, and the plugin version. Reference metadata is retrieved from PubMed, and every PMID/DOI pair is then checked independently against PubMed before it can be cited; any reference whose identifiers point to different papers, or that is retracted, is excluded. Clinical judgement and final sign-off remain the responsibility of the reviewing clinician and the approving MDT.

## License

MIT. See the [marketplace LICENSE](../LICENSE).
