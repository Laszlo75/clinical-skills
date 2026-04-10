# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A thin, user-facing trigger skill for clinical literature searches. It parses a clinical topic with the researcher, dispatches the sibling `evidence-search` agent (shipped in `clinical-evidence/agents/`) to perform the actual PubMed + Scholar Gateway + guideline search in isolated context, validates the resulting hidden reference ledger, and writes two Zotero export files (`.bib` + `.txt`) from it.

The skill exists because Claude Code agents cannot be invoked directly by a user — this is the user-facing trigger phrase that dispatches the agent. The narrative evidence summary document (`.md` + `.docx`) that used to be this skill's output is now produced by the sibling `research-summary` consumer skill.

## Repository Structure

- **SKILL.md** — The thin trigger skill (~180 lines). 5-step workflow: parse + confirm topic → dispatch evidence-search agent → validate ledger → write `.bib` + PMIDs → point at next skill.
- **references/ledger_schema.md** — **Single source of truth** for the YAML reference ledger format. Read by every consumer in the plugin (`research-summary`, `protocol-reviewer`) and by the `evidence-search` agent (which inlines the essential parts because it runs in isolated context).
- **references/consumer_integration.md** — Integration guide for any downstream skill that consumes the ledger. Documents the discover/validate/consume pattern.
- **references/pubmed_strategy.md** — PubMed search construction patterns and quality assessment heuristics. Kept for human reference; the agent inlines the parts it needs.
- **scripts/validate_ledger.py** — Executable validator for the ledger. Run by this skill (Step 3) and by every downstream consumer skill before loading the ledger.
- **evals/evals.json** — Test scenarios for the skill.

## Key Design Decisions

- **Agent-first execution**: The tool-heavy search work runs in the isolated `evidence-search` subagent so PubMed metadata fetches, Scholar Gateway passages, and full-text retrievals do not pollute the main conversation context. The skill waits for the agent's short structured summary and then validates the canonical ledger the agent wrote.
- **Invisible reference ledger**: During the search, references are recorded in a structured YAML ledger (PMID, DOI, authors, title copied verbatim from PubMed after each `get_article_metadata` call). The ledger is written to a hidden canonical path (`<workspace>/.literature_search_ledger.yaml`) so the researcher never sees it — its primary purpose is to anchor the anti-hallucination write-to-file pattern, and its secondary purpose is to hand off verified evidence to downstream skills. The `.bib` file and PMID list are generated solely from this ledger to prevent DOI/title fabrication.
- **Authoritative schema in one place**: `references/ledger_schema.md` is the single source of truth for the ledger format. The `evidence-search` agent inlines the essential fields because it can't reliably read that file from its isolated context, but the validator script is the real ground truth that prevents drift.
- **Executable validation**: Every ledger is validated by `scripts/validate_ledger.py` before any downstream consumption. Prose checklists drift; scripts don't.
- **2 user-facing outputs + 1 hidden ledger**: The researcher receives `.bib` and `.txt` files. The hidden YAML ledger is present in the workspace but does not appear in any user-facing file list. Narrative `.md`/`.docx` is the job of `research-summary`.

## Output Files (per search)

User-facing outputs:

1. `[Topic_Name]_References.bib` — BibTeX for Zotero import
2. `[Topic_Name]_PMIDs.txt` — PMID list for Zotero bulk import

Internal (hidden) artifact — not counted among the user-facing outputs:

- `.literature_search_ledger.yaml` — structured reference ledger at the canonical hidden path. Not shown to the researcher. Consumed by downstream skills (`research-summary`, `protocol-reviewer`). Validated by `scripts/validate_ledger.py` at the end of every search.

## Tool Dependencies

Required:

- **Python 3 + PyYAML** — required to run the ledger validator (`scripts/validate_ledger.py`)
- **evidence-search agent** — ships in the same `clinical-evidence` plugin at `../../agents/evidence-search.md`

The agent in turn requires (not this skill directly):

- **PubMed MCP** (`search_articles`, `get_article_metadata`, `get_full_text_article`, `find_related_articles`)
- **Scholar Gateway** (`semanticSearch`)
- **WebSearch / WebFetch** — for national guidelines

Optional (enhance agent coverage when available):

- **bioRxiv MCP** (`search_preprints`, `search_published_preprints`) — preprint search for emerging evidence
- **Clinical Trials MCP** (`search_trials`, `get_trial_details`, `analyze_endpoints`) — ongoing trial data

## AI Use Policy (ISO 42001)

**System identity:** Claude Opus 4.6 (Anthropic), accessed via Claude Desktop with PubMed and Scholar Gateway integrations.

**Intended use:** AI-assisted literature search and reference ledger construction. The system retrieves, structures, and verifies evidence; it does not make clinical decisions and does not produce the narrative evidence summary (that is handled by the `research-summary` consumer skill).

**Human oversight:** All AI-generated outputs are advisory only. Every evidence summary or protocol review that ultimately consumes this ledger must be critically appraised by a clinician before informing clinical decisions.

**Transparency:** The ledger carries an AI-system metadata block recording the plugin version, model identifier, ledger schema version, and search date. Every downstream consumer propagates that metadata into its own transparency disclaimer.

**Reference integrity:** DOIs and article metadata are retrieved programmatically from PubMed by the `evidence-search` agent and written directly to the hidden reference ledger in the same turn they are retrieved. The agent re-verifies every reference character-by-character against PubMed in its verification step, and this skill then runs `scripts/validate_ledger.py` before writing any export files. The system never fabricates identifiers and never reconstructs fields from memory.

## Clinical Content Rules

- DOIs must be copied verbatim from the ledger (which was verified against PubMed by the agent) — never from memory
- The ledger's verification step re-fetches metadata for ALL references and compares character-by-character — not a spot-check
- Target 15–30 high-quality references per search
