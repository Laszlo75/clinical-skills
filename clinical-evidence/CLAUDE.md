# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working on the `clinical-evidence` plugin.

## What This Is

A Claude Code plugin that bundles two clinical skills, `literature-search` and `protocol-reviewer`, which are designed to work together through an invisible handoff. Together they take a clinical topic or an uploaded protocol and produce a draft evidence summary and/or a draft protocol review document, all framed in UK NHS context and carrying ISO 42001 transparency disclaimers.

The plugin is the single distributable unit: the two skills are co-designed, share a hidden reference ledger, and are not intended to be installed independently.

## Repository Structure

```text
clinical-evidence/
├── .claude-plugin/plugin.json     # plugin manifest
├── README.md                      # plugin-level docs (installation + quick start)
├── CHANGELOG.md                   # plugin-level changelog (single source of version history)
├── CLAUDE.md                      # this file
└── skills/
    ├── literature-search/         # evidence gathering + reference verification
    │   ├── SKILL.md
    │   ├── CLAUDE.md              # skill-specific guidance
    │   ├── README.md
    │   ├── assets/reference.docx  # pandoc template
    │   ├── references/            # template + schema + integration contract
    │   │   ├── evidence_summary_template.md
    │   │   ├── ledger_schema.md         # SINGLE SOURCE OF TRUTH for the ledger format
    │   │   ├── consumer_integration.md  # how any downstream skill plugs in
    │   │   └── pubmed_strategy.md
    │   ├── scripts/validate_ledger.py   # executable validator (run by both skills)
    │   └── evals/evals.json
    └── protocol-reviewer/         # cross-referencing + recommendations
        ├── SKILL.md
        ├── CLAUDE.md
        ├── README.md
        ├── assets/reference.docx
        ├── references/document_template.md
        └── evals/evals.json
```

Per-skill `CLAUDE.md` files live inside each skill folder and hold the skill-specific guidance (tool dependencies, clinical content rules, key design decisions). This plugin-level `CLAUDE.md` only covers what spans both skills.

## Why these skills ship together

The two skills are tightly coupled by design:

- **Sibling relative paths.** `protocol-reviewer/SKILL.md` references [`../literature-search/references/ledger_schema.md`](./skills/literature-search/references/ledger_schema.md) and [`../literature-search/scripts/validate_ledger.py`](./skills/literature-search/scripts/validate_ledger.py). These paths resolve because both skills sit as siblings under `clinical-evidence/skills/`. Splitting the plugin would break these pointers.
- **Shared hidden ledger.** When `literature-search` runs, it writes an internal reference ledger to `<workspace>/.literature_search_ledger.yaml`. When `protocol-reviewer` runs in the same workspace, it discovers, validates, and consumes that ledger automatically. Researchers never see or manage the ledger.
- **Single reference contract.** The ledger format is defined in exactly one place ([`skills/literature-search/references/ledger_schema.md`](./skills/literature-search/references/ledger_schema.md)). Both skills point at that file rather than duplicating the schema, and both run the bundled validator script to enforce it.

## Versioning

The plugin is the only versioned unit. Per-skill SKILL.md files have no `version` frontmatter field, and per-skill CHANGELOGs do not exist. See the plugin-level [`CHANGELOG.md`](./CHANGELOG.md) for release history.

**Semver policy:**

- MAJOR — breaking change to the researcher-facing workflow or to the ledger schema contract (which also bumps `ledger_schema_version` in [`ledger_schema.md`](./skills/literature-search/references/ledger_schema.md)).
- MINOR — a new skill added (e.g. a future `literature-review`), a new capability, or a new required tool.
- PATCH — bug fixes, prose edits, reference-template updates.

## Build / Conversion Command

Both skills use the same pandoc conversion pattern:

```bash
pandoc "[Name]_[DocType]_[Year].md" \
  -o "[Name]_[DocType]_[Year].docx" \
  --reference-doc=assets/reference.docx \
  --from=markdown+yaml_metadata_block \
  --to=docx
```

Each skill bundles its own `assets/reference.docx` — they are intentionally kept as independent copies so each skill stays self-contained even when loaded in isolation.

## Tool Dependencies

Required (both skills):

- **pandoc** — markdown to `.docx` conversion
- **Python 3 + PyYAML** — used by the ledger validator

Required for `literature-search` (and for `protocol-reviewer` when it auto-triggers a search):

- **PubMed MCP** — literature search and article metadata
- **Scholar Gateway MCP** — semantic search
- **WebSearch / WebFetch** — national guideline pages

Optional (enhance coverage):

- **bioRxiv MCP** — preprints on rapidly evolving topics
- **Clinical Trials MCP** — ongoing trial data

## AI Use Policy (ISO 42001)

**System identity:** Claude Opus 4.6 (Anthropic), accessed via Claude Desktop.

**Intended use:** AI-assisted literature search, evidence synthesis, and cross-referencing of clinical protocols against current guidelines. The plugin retrieves, structures, and summarises evidence; it does not make clinical decisions.

**Human oversight:** Every output is advisory only and is generated as an explicit draft. The reviewing clinician and the approving MDT are responsible for critical appraisal, verification, and sign-off.

**Transparency:** Every generated document carries a "DRAFT — NOT FOR CLINICAL USE" callout and a transparency disclaimer naming the plugin (`clinical-evidence v…`), the model, the MCP sources used, and the generation date.

**Reference integrity:** DOIs and article metadata are retrieved programmatically from PubMed and written directly to the hidden reference ledger in the same turn they are retrieved. References are re-verified character-by-character against PubMed before the ledger is handed off, and are then structurally validated by the bundled validator script. The system never fabricates identifiers and never reconstructs fields from memory.
