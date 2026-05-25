# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working on the `clinical-evidence` plugin.

## What This Is

A Claude Code plugin that bundles two co-designed clinical skills — `research-summary` and `protocol-reviewer` — plus one shared subagent, `evidence-search`, that does the actual PubMed/Scholar Gateway/guideline retrieval work. The skills share a hidden YAML reference ledger produced by the agent. Together they take a clinical topic or an uploaded protocol and produce a draft evidence summary and/or a draft protocol review document, all framed in UK NHS context and carrying ISO 42001 transparency disclaimers. `research-summary` is the user-facing entry point for a literature search or evidence summary (it dispatches the agent and also writes Zotero exports); `protocol-reviewer` reviews an uploaded protocol against the same evidence.

The plugin is the single distributable unit: the two skills and the agent are co-designed, share the hidden reference ledger and a plugin-level `shared/` contract directory, and are not intended to be installed independently.

## Repository Structure

```text
clinical-evidence/
├── .claude-plugin/plugin.json     # plugin manifest
├── README.md                      # plugin-level docs (installation + quick start)
├── CHANGELOG.md                   # plugin-level changelog (single source of version history)
├── CLAUDE.md                      # this file
├── agents/
│   └── evidence-search.md         # the shared subagent that runs the PubMed/Scholar/guideline search
├── shared/                        # contract layer, owned by no single skill
│   ├── references/
│   │   ├── ledger_schema.md         # SINGLE SOURCE OF TRUTH for the ledger format
│   │   ├── consumer_integration.md  # how any downstream skill plugs in
│   │   └── pubmed_strategy.md       # PubMed search-construction reference
│   └── scripts/
│       ├── validate_ledger.py       # executable validator (run by every consumer)
│       └── ledger_to_exports.py     # writes .bib + PMID exports from the ledger
└── skills/
    ├── research-summary/          # search + narrative evidence summary (user-facing search entry point)
    │   ├── SKILL.md
    │   ├── CLAUDE.md              # skill-specific guidance
    │   ├── README.md
    │   ├── assets/reference.docx  # pandoc template
    │   ├── references/
    │   │   └── evidence_summary_template.md
    │   └── evals/evals.json
    └── protocol-reviewer/         # protocol review consumer
        ├── SKILL.md
        ├── CLAUDE.md
        ├── README.md
        ├── assets/reference.docx
        ├── references/document_template.md
        └── evals/evals.json
```

Per-skill `CLAUDE.md` files live inside each skill folder and hold the skill-specific guidance (tool dependencies, clinical content rules, key design decisions). This plugin-level `CLAUDE.md` only covers what spans the whole plugin.

## Why these components ship together

The two skills and the agent are tightly coupled by design:

- **Shared subagent.** Both skills dispatch the same [`evidence-search` agent](./agents/evidence-search.md) to do the actual search work in isolated context. The agent runs in its own conversation so the tool-heavy traffic (PubMed metadata, Scholar Gateway passages, full-text retrievals, reference verification) never reaches the parent skill's context. This keeps the main conversation clean and lets downstream synthesis work from a short structured summary rather than thousands of lines of tool output.
- **Shared contract directory.** `research-summary/SKILL.md` and `protocol-reviewer/SKILL.md` reference [`shared/references/ledger_schema.md`](./shared/references/ledger_schema.md), [`shared/references/consumer_integration.md`](./shared/references/consumer_integration.md), [`shared/scripts/validate_ledger.py`](./shared/scripts/validate_ledger.py), and [`shared/scripts/ledger_to_exports.py`](./shared/scripts/ledger_to_exports.py) via `../../shared/...`. Each skill sits at `skills/<skill>/`, two levels below the plugin root, so those paths resolve. Splitting the plugin would break these pointers.
- **Shared hidden ledger.** When any skill dispatches the `evidence-search` agent, the agent writes an internal reference ledger to `<workspace>/.literature_search_ledger.yaml`. Any skill run later in the same workspace discovers, validates, and consumes that ledger automatically. Researchers never see or manage the ledger.
- **Single reference contract.** The ledger format is defined in exactly one place ([`shared/references/ledger_schema.md`](./shared/references/ledger_schema.md)). Every skill and the agent point at that file rather than duplicating the schema, and every consumer runs the bundled validator script to enforce it. The agent inlines the essential schema fields in its prompt because it can't reliably read the reference doc from its isolated context, but the executable validator is the ground truth that prevents drift.
- **Scripted exports.** The `.bib` + PMID exports are written by [`shared/scripts/ledger_to_exports.py`](./shared/scripts/ledger_to_exports.py), called by each consumer rather than hand-written. Like the validator, an executable export keeps the format from drifting and copies reference fields verbatim from the ledger.

## Versioning

The plugin is the only versioned unit. Per-skill SKILL.md files have no `version` frontmatter field, and per-skill CHANGELOGs do not exist. See the plugin-level [`CHANGELOG.md`](./CHANGELOG.md) for release history.

Current release: **2.0.0**.

**Semver policy:**

- MAJOR — breaking change to the researcher-facing workflow or to the ledger schema contract (which also bumps `ledger_schema_version` in [`ledger_schema.md`](./shared/references/ledger_schema.md)).
- MINOR — a new skill or agent added, a new capability, or a new required tool.
- PATCH — bug fixes, prose edits, reference-template updates.

## Build / Conversion Command

Both skills (`research-summary`, `protocol-reviewer`) use the same pandoc conversion pattern:

```bash
pandoc "[Name]_[DocType]_[Year].md" \
  -o "[Name]_[DocType]_[Year].docx" \
  --reference-doc=assets/reference.docx \
  --from=markdown+yaml_metadata_block \
  --to=docx
```

Each skill bundles its own `assets/reference.docx` — they are intentionally kept as independent copies so each skill stays self-contained even when loaded in isolation. Both skills also call the shared `shared/scripts/ledger_to_exports.py` to write the `.bib` + PMID exports from the ledger.

## Tool Dependencies

Required (whole plugin):

- **Python 3 + PyYAML** — used by the ledger validator and the export script, run by every consumer skill
- **PubMed MCP** — literature search and article metadata (used by the `evidence-search` agent)
- **Scholar Gateway MCP** — semantic search (used by the agent)
- **WebSearch / WebFetch** — national guideline pages (used by the agent)

Required for the narrative consumers (`research-summary`, `protocol-reviewer`):

- **pandoc** — markdown to `.docx` conversion

Optional (enhance agent coverage):

- **bioRxiv MCP** — preprints on rapidly evolving topics
- **Clinical Trials MCP** — ongoing trial data

## AI Use Policy (ISO 42001)

**System identity:** Claude Opus 4.7 (Anthropic), accessed via Claude Desktop.

**Intended use:** AI-assisted literature search, evidence synthesis, and cross-referencing of clinical protocols against current guidelines. The plugin retrieves, structures, and summarises evidence; it does not make clinical decisions.

**Human oversight:** Every output is advisory only and is generated as an explicit draft. The reviewing clinician and the approving MDT are responsible for critical appraisal, verification, and sign-off.

**Transparency:** Every generated document carries a "DRAFT — NOT FOR CLINICAL USE" callout and a transparency disclaimer naming the plugin (`clinical-evidence v…`), the model, the MCP sources used, and the generation date.

**Reference integrity:** DOIs and article metadata are retrieved programmatically from PubMed by the `evidence-search` agent and written directly to the hidden reference ledger in the same turn they are retrieved. References are re-verified character-by-character against PubMed before the ledger is handed off, and are then structurally validated by the bundled validator script before any user-facing document is generated. The system never fabricates identifiers and never reconstructs fields from memory.
