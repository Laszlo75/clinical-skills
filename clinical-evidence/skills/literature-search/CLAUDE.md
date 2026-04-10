# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude Code skill (custom prompt) that performs systematic clinical literature searches using PubMed and Scholar Gateway. Given a clinical topic, it searches for current national guidelines and published evidence, then produces a structured evidence summary document (.docx), a BibTeX file, and a PMID list for the researcher — plus an internal hidden YAML reference ledger used for quality control and for downstream skills to consume.

This skill is designed to be used standalone (for journal clubs, grant applications, teaching, clinical questions) or as the first step in a multi-skill workflow with consumers like `protocol-reviewer` (its sibling in the `clinical-evidence` plugin) and the future `literature-review` skill.

## Repository Structure

- **SKILL.md** — The skill definition (prompt). Defines the 6-step workflow: parse topic → search guidelines → search evidence → verify references → generate summary → validate ledger + output files.
- **assets/reference.docx** — Pandoc reference template for .docx output (Arial, A4, navy headings, headers/footers).
- **references/evidence_summary_template.md** — Markdown template and pandoc conversion instructions for the evidence summary document.
- **references/pubmed_strategy.md** — PubMed search construction patterns and quality assessment heuristics.
- **references/ledger_schema.md** — **Single source of truth** for the YAML reference ledger format. Every field, every type, the semver policy, producer and consumer contracts.
- **references/consumer_integration.md** — Integration guide for any downstream skill that consumes the ledger. Documents the discover/validate/consume pattern.
- **scripts/validate_ledger.py** — Executable validator for the ledger. Run by this skill at the end of each search as a self-check and by every consumer before loading the ledger.
- **evals/evals.json** — Test scenarios for the skill.

## Key Design Decisions

- **Markdown-first approach**: The evidence summary is written as Markdown with YAML frontmatter, then converted to .docx via pandoc.
- **Invisible reference ledger for quality control**: During search, references are recorded in a structured YAML ledger (PMID, DOI, authors, title copied verbatim from PubMed after each `get_article_metadata` call). The ledger is written to a hidden canonical path (`<workspace>/.literature_search_ledger.yaml`) so the researcher never sees it — its primary purpose is to anchor the anti-hallucination write-to-file pattern, and its secondary purpose is to hand off verified evidence to downstream skills. The .bib and reference list are generated solely from this ledger to prevent DOI/title fabrication.
- **Authoritative schema in one place**: `references/ledger_schema.md` is the single source of truth for the ledger format. SKILL.md and every consumer point at it rather than duplicating the schema. Schema is versioned independently of the skill via `ledger_schema_version` (current: `1.0`).
- **Structured evidence grades**: Guideline recommendations carry a structured `grade` object (`system`, `code`, `display`) rather than a free-text string, so downstream consumers can filter and aggregate by evidence strength.
- **Executable validation**: Every ledger is validated by `scripts/validate_ledger.py` before any downstream consumption. Prose checklists drift; scripts don't.
- **Dual search strategy**: Both PubMed MCP (keyword/MeSH) and Scholar Gateway (semantic search) are used for each topic — they return complementary results.
- **4 user-facing outputs + 1 hidden ledger**: The researcher receives `.md`, `.docx`, `.bib`, and `.txt` files. The hidden YAML ledger is present in the workspace but does not appear in any user-facing file list.

## Build / Conversion Command

```bash
pandoc "[Topic_Name]_Evidence_Summary_[Year].md" \
  -o "[Topic_Name]_Evidence_Summary_[Year].docx" \
  --reference-doc=assets/reference.docx \
  --from=markdown+yaml_metadata_block \
  --to=docx
```

## Output Files (per search)

User-facing outputs:

1. `[Topic_Name]_Evidence_Summary_[Year].md` — Markdown source
2. `[Topic_Name]_Evidence_Summary_[Year].docx` — Word document
3. `[Topic_Name]_References.bib` — BibTeX for Zotero
4. `[Topic_Name]_PMIDs.txt` — PMID list for Zotero bulk import

Internal (hidden) artifact — not counted among the user-facing outputs:

- `.literature_search_ledger.yaml` — structured reference ledger at the canonical hidden path. Not shown to the researcher. Consumed by downstream skills (e.g., protocol-reviewer). Validated by `scripts/validate_ledger.py` at the end of every search.

## Tool Dependencies

Required:
- **PubMed MCP** (`search_articles`, `get_article_metadata`, `get_full_text_article`, `find_related_articles`)
- **Scholar Gateway** (`semanticSearch`)
- **WebSearch / WebFetch** — for national guidelines
- **pandoc** — markdown to .docx conversion

Optional (enhance coverage when available):
- **bioRxiv MCP** (`search_preprints`, `search_published_preprints`) — preprint search for emerging evidence
- **Clinical Trials MCP** (`search_trials`, `get_trial_details`, `analyze_endpoints`) — ongoing trial data

## AI Use Policy (ISO 42001)

**System identity:** Claude Opus 4.6 (Anthropic), accessed via Claude Desktop with PubMed and Scholar Gateway integrations.

**Intended use:** AI-assisted literature search and evidence synthesis. The system retrieves, structures, and summarises evidence; it does not make clinical decisions.

**Human oversight:** All AI-generated outputs are advisory only. Every evidence summary must be critically appraised by a clinician before informing clinical decisions.

**Transparency:** Each evidence summary is generated as an explicit draft with a "DRAFT — NOT FOR CLINICAL USE" callout and a transparency disclaimer disclosing AI involvement.

**Reference integrity:** DOIs and article metadata are retrieved programmatically from PubMed and written directly to the hidden reference ledger in the same turn they are retrieved, then re-verified character-by-character against PubMed in Step 4, then structurally validated by `scripts/validate_ledger.py` before the search completes. The system never fabricates identifiers and never reconstructs fields from memory.

## Clinical Content Rules

- Always include evidence grades inline (e.g., "BTS Grade 1C", "NICE Strength: Strong")
- Frame findings in UK NHS context (MHRA, NICE TAs, UK registries)
- Numbered in-text citations in square brackets: `[1]`, `[2, 3]`
- DOIs must be copied verbatim from `get_article_metadata` directly to `.literature_search_ledger.yaml` (the hidden canonical path) — never from memory
- Step 4 verification re-fetches metadata for ALL references and compares character-by-character — not a spot-check
- Target 15-30 high-quality references per search
