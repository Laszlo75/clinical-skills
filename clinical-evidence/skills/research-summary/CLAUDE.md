# CLAUDE.md

Maintainer notes for this skill. The runtime instructions live in `SKILL.md`; this file records design decisions for anyone editing the skill.

## What This Is

A Claude Code skill (custom prompt) that produces a structured narrative evidence summary document (`.md` + `.docx`) plus Zotero exports (`.bib` + PMID list) from a verified YAML reference ledger. It either picks up an existing ledger in the workspace silently or dispatches the `evidence-search` agent to build one, then writes a Word document covering guidelines, recent evidence, conflicting recommendations, emerging evidence, and evidence gaps. This skill is the user-facing entry point for "what does the evidence say about X" — it absorbed the search-trigger phrases of the former `literature-search` skill.

The skill picks up its evidence base invisibly: if a recent search has been run in the same workspace, the hidden reference ledger is used directly; otherwise the `evidence-search` agent (bundled in the same `clinical-evidence` plugin) is dispatched on the fly. **The researcher is never asked about reference files, YAML, or file paths** — they simply ask about a topic and receive the documents.

## Repository Structure

- **SKILL.md** — The skill definition (prompt). Defines the workflow: discover + validate + load hidden reference ledger → write markdown → convert to `.docx` → write `.bib` + PMID exports.
- **assets/reference.docx** — Pandoc reference template for `.docx` output (Arial, A4, navy headings, headers/footers).
- **references/evidence_summary_template.md** — Markdown template and pandoc conversion instructions for the evidence summary document.
- **evals/evals.json** — Test scenarios for the skill.

## Key Design Decisions

- **Invisible handoff**: Evidence flows from the `evidence-search` agent to this skill via a hidden YAML ledger at `<workspace>/.literature_search_ledger.yaml`. The ledger is an internal quality-control and handoff artifact; the researcher never sees, edits, or is asked about it. Discovery is a single fixed path — either the file exists (use it) or it doesn't (auto-trigger the agent).
- **Authoritative schema**: The ledger format is defined in one place — [`../../shared/references/ledger_schema.md`](../../shared/references/ledger_schema.md). This skill targets ledger schema `1.x`. The integration pattern lives in [`../../shared/references/consumer_integration.md`](../../shared/references/consumer_integration.md). Both are the single source of truth for every downstream consumer.
- **Executable validation**: Step 1b validates the ledger by running `../../shared/scripts/validate_ledger.py`. This eliminates prose-drift between producer and consumer — the script is the contract.
- **Agent-based dispatch**: When no ledger exists, this skill dispatches the `evidence-search` agent so the tool-heavy search work runs in isolated context and does not pollute the main conversation.
- **Markdown-first approach**: The evidence summary is written as Markdown with YAML frontmatter, then converted to `.docx` via pandoc.
- **Reference integrity**: DOIs, titles, and author lists are copied verbatim from the hidden ledger (which in turn was verified against PubMed by the `evidence-search` agent). This skill does not modify reference metadata.
- **Scripted exports**: The `.bib` and PMID files are written by the shared `../../shared/scripts/ledger_to_exports.py` script (Step 4), not hand-written. Like the validator, an executable export keeps the format from drifting and copies fields verbatim from the ledger.

## Build / Conversion Command

```bash
pandoc "[Topic_Name]_Evidence_Summary_[Year].md" \
  -o "[Topic_Name]_Evidence_Summary_[Year].docx" \
  --reference-doc="[skill-path]/assets/reference.docx" \
  --from=markdown+yaml_metadata_block \
  --to=docx
```

## Output Files (per summary)

1. `[Topic_Name]_Evidence_Summary_[Year].md` — Markdown source
2. `[Topic_Name]_Evidence_Summary_[Year].docx` — Word document
3. `[Topic_Name]_References.bib` — BibTeX for Zotero import (from `ledger_to_exports.py`)
4. `[Topic_Name]_PMIDs.txt` — PMID list for Zotero bulk import (from `ledger_to_exports.py`)

## Tool Dependencies

- **pandoc** — markdown to `.docx` conversion
- **Python 3 + PyYAML** — required to run the ledger validator (`../../shared/scripts/validate_ledger.py`) and the export script (`../../shared/scripts/ledger_to_exports.py`)
- **evidence-search agent** — required only when there is no existing ledger in the workspace and the agent must be dispatched
- **PubMed MCP, Scholar Gateway, WebSearch / WebFetch** — required only for the agent's dispatch path, not for this skill directly

## AI Use Policy (ISO 42001)

**System identity:** the latest Claude Opus model (Anthropic) at maximum effort (the currently recommended version is named in the plugin README) accessed via Claude Cowork or Claude Code. The clinical reasoning and narrative synthesis need the strongest available model.

**Intended use:** AI-assisted narrative synthesis of clinical evidence into a structured summary document. The system synthesises and summarises evidence; it does not make clinical decisions.

**Human oversight:** All AI-generated outputs are advisory only. Every evidence summary must be critically appraised by a clinician before informing clinical decisions.

**Transparency:** Each evidence summary document is generated as an explicit draft with a prominent "DRAFT — NOT FOR CLINICAL USE" callout. The transparency disclaimer discloses AI involvement and includes a "Reviewed and approved by" placeholder for the clinician to complete after appraisal.

**Reference integrity:** DOIs and article metadata are copied verbatim from the hidden YAML reference ledger, which was verified against PubMed by the `evidence-search` agent and structurally validated by `validate_ledger.py` before this skill consumes it. This skill never fabricates or reconstructs identifiers.

**Traceability:** Each evidence summary includes an AI system metadata line recording the `clinical-evidence` plugin version, ledger schema version, model identifier, search date, and document date.

## Clinical Content Rules

- Always include evidence grades inline (e.g., "BTS Grade 1C", "NICE Strength: Strong")
- Use `grade.display` from the ledger verbatim — do not reconstruct from `system` + `code`
- Frame findings in UK NHS context (MHRA, NICE TAs, UK registries)
- Numbered in-text citations in square brackets: `[1]`, `[2, 3]`
- DOIs must be copied verbatim from the YAML reference ledger — never reconstructed from memory
- Target roughly 20–40 high-quality references per summary; do not pad narrow topics
