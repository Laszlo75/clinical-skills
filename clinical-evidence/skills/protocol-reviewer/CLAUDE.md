# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude Code skill (custom prompt) that reviews clinical protocols against current national guidelines and published evidence. It reads an uploaded clinical protocol (PDF/Word), cross-references it against an evidence base, and produces a structured .docx review document with actionable recommendations.

The skill picks up its evidence base invisibly: if a recent literature search has been run in the same workspace, the hidden reference ledger is used directly; otherwise the sibling `literature-search` skill (bundled in the same `clinical-evidence` plugin) is auto-triggered. **The researcher is never asked about reference files, YAML, or file paths** — they simply upload a protocol and ask for a review.

## Repository Structure

- **SKILL.md** — The skill definition (prompt). Defines the 5-step workflow: read protocol → discover + validate + load hidden reference ledger → cross-reference → generate review → log to evaluation register.
- **assets/reference.docx** — Pandoc reference template for .docx output (Arial, A4, navy headings, headers/footers).
- **references/document_template.md** — Markdown template and pandoc conversion instructions for the review document.
- **evals/evals.json** — Test scenarios for the skill.
- **reviews/** — Local evaluation register (gitignored). Contains `evaluation_register.csv` for tracking review outcomes.

## Key Design Decisions

- **Invisible handoff**: Evidence flows from `literature-search` to this skill via a hidden YAML ledger at `<workspace>/.literature_search_ledger.yaml`. The ledger is an internal quality-control and handoff artifact; the researcher never sees, edits, or is asked about it. Discovery is a single fixed path — either the file exists (use it) or it doesn't (auto-trigger literature-search).
- **Authoritative schema**: The ledger format is defined in one place — [`../literature-search/references/ledger_schema.md`](../literature-search/references/ledger_schema.md). This skill targets ledger schema `1.x`. The integration pattern lives in [`../literature-search/references/consumer_integration.md`](../literature-search/references/consumer_integration.md). Both are the single source of truth for every downstream consumer.
- **Executable validation**: Step 2 validates the ledger by running `../literature-search/scripts/validate_ledger.py`. This eliminates prose-drift between producer and consumer — the script is the contract.
- **Markdown-first approach**: The review is written as Markdown with YAML frontmatter, then converted to .docx via pandoc.
- **Reference integrity**: DOIs, titles, and author lists are copied verbatim from the hidden ledger (which in turn was verified against PubMed by the literature-search skill). This skill does not modify reference metadata.

## Build / Conversion Command

```bash
pandoc "[Protocol_Name]_Review_[Year].md" \
  -o "[Protocol_Name]_Review_[Year].docx" \
  --reference-doc=assets/reference.docx \
  --from=markdown+yaml_metadata_block \
  --to=docx
```

## Output Files (per review)

1. `[Protocol_Name]_Review_[Year].md` — Markdown source
2. `[Protocol_Name]_Review_[Year].docx` — Word document
3. `[Protocol_Name]_References.bib` — BibTeX for Zotero
4. `[Protocol_Name]_PMIDs.txt` — PMID list for Zotero bulk import

## Tool Dependencies

- **pandoc** — markdown to .docx conversion
- **Python 3 + PyYAML** — required to run the ledger validator (`../literature-search/scripts/validate_ledger.py`)
- **PubMed MCP, Scholar Gateway, WebSearch** — required only when there is no existing ledger in the workspace and literature-search must be auto-triggered

## AI Use Policy (ISO 42001)

**System identity:** Claude Opus 4.6 (Anthropic), accessed via Claude Desktop. This skill requires Opus 4.6 for the clinical reasoning and cross-referencing quality needed.

**Intended use:** AI-assisted evidence synthesis to support the review of clinical protocols against current national guidelines and published literature. The system cross-references and summarises evidence; it does not make clinical decisions.

**Human oversight:** All AI-generated outputs are advisory only. Every review must be critically appraised by a consultant-level clinician before informing protocol changes. Final recommendations are the responsibility of the reviewing clinician and the approving MDT.

**Transparency:** Each review document is generated as an explicit draft with a prominent "DRAFT — NOT FOR CLINICAL USE" callout. The transparency disclaimer (section 6) discloses AI involvement and includes a "Reviewed and approved by" placeholder for the clinician to complete after appraisal.

**Reference integrity:** DOIs and article metadata are copied verbatim from the hidden YAML reference ledger, which was verified against PubMed by the literature-search skill and structurally validated by `validate_ledger.py` before this skill consumes it. This skill never fabricates or reconstructs identifiers.

**Traceability:** Each review document includes an AI system metadata line recording the `clinical-evidence` plugin version, ledger schema version, model identifier, search date, and review date. A local evaluation register (`reviews/evaluation_register.csv`, gitignored) logs review outcomes and recommendation counts for ongoing quality monitoring.

## Clinical Content Rules

- Always include evidence grades inline (e.g., "BTS Grade 1C", "NICE Strength: Strong")
- Frame recommendations in UK NHS context (MHRA, NICE TAs, UK registries)
- Numbered in-text citations in square brackets: `[1]`, `[2, 3]`
- DOIs must be copied verbatim from the YAML reference ledger — never reconstructed from memory
- Target 15-30 high-quality references per review
