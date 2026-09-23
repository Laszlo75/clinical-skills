# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working on the `clinical-evidence` plugin.

## What This Is

A Claude Code plugin that bundles two co-designed clinical skills — `research-summary` and `protocol-reviewer` — plus two shared subagents: `evidence-search`, which does the PubMed/Scholar Gateway/guideline retrieval, and `reference-checker`, which independently re-reads every reference for verification. The skills share a hidden YAML reference ledger produced by the agent. Together they take a clinical topic or an uploaded protocol and produce a draft evidence summary and/or a draft protocol review document, all framed in UK NHS context and carrying ISO 42001 transparency disclaimers. `research-summary` is the user-facing entry point for a literature search or evidence summary (it dispatches the agent and also writes Zotero exports); `protocol-reviewer` reviews an uploaded protocol against the same evidence.

The plugin is the single distributable unit: the two skills and the agent are co-designed, share the hidden reference ledger and a plugin-level `shared/` contract directory, and are not intended to be installed independently.

## Repository Structure

```text
clinical-evidence/
├── .claude-plugin/plugin.json     # plugin manifest
├── README.md                      # plugin-level docs (installation + quick start)
├── CHANGELOG.md                   # plugin-level changelog (single source of version history)
├── CLAUDE.md                      # this file
├── agents/
│   ├── evidence-search.md         # runs the PubMed/Scholar/guideline search, writes the ledger
│   └── reference-checker.md       # independent second reading of every reference (identifiers only)
├── shared/                        # contract layer, owned by no single skill
│   ├── references/
│   │   ├── ledger_schema.md         # SINGLE SOURCE OF TRUTH for the ledger format
│   │   ├── consumer_integration.md  # how any downstream skill plugs in
│   │   └── pubmed_strategy.md       # PubMed search-construction reference
│   └── scripts/
│       ├── refmatch.py              # tolerant record comparison (library)
│       ├── verify_references.py     # cross-checks ledger vs second reading, excludes failures
│       ├── validate_ledger.py       # executable validator (run by every consumer)
│       ├── format_references.py     # Vancouver reference list from the ledger
│       └── ledger_to_exports.py     # writes .bib + PMID exports from the ledger
└── skills/
    ├── research-summary/          # search + narrative evidence summary (user-facing search entry point)
    │   ├── SKILL.md
    │   ├── CLAUDE.md              # skill-specific guidance
    │   ├── README.md
    │   ├── assets/reference.docx  # house-style reference (pandoc template when pandoc is used)
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

The two skills and the agents are tightly coupled by design:

- **Shared subagents.** Both skills dispatch the same [`evidence-search` agent](./agents/evidence-search.md) to do the actual search work in isolated context. The agent runs in its own conversation so the tool-heavy traffic (PubMed metadata, Scholar Gateway passages, full-text retrievals) never reaches the parent skill's context. This keeps the main conversation clean and lets downstream synthesis work from a short structured summary rather than thousands of lines of tool output. Both skills then dispatch [`reference-checker`](./agents/reference-checker.md) for the independent second reading.
- **Shared contract directory.** `research-summary/SKILL.md` and `protocol-reviewer/SKILL.md` reference [`shared/references/ledger_schema.md`](./shared/references/ledger_schema.md), [`shared/references/consumer_integration.md`](./shared/references/consumer_integration.md), [`shared/scripts/validate_ledger.py`](./shared/scripts/validate_ledger.py), and [`shared/scripts/ledger_to_exports.py`](./shared/scripts/ledger_to_exports.py) via `../../shared/...`. Each skill sits at `skills/<skill>/`, two levels below the plugin root, so those paths resolve. Splitting the plugin would break these pointers.
- **Shared hidden ledger.** When any skill dispatches the `evidence-search` agent, the agent writes an internal reference ledger to `<workspace>/.literature_search_ledger.yaml`. Any skill run later in the same workspace discovers, validates, and consumes that ledger automatically. Researchers never see or manage the ledger.
- **Single reference contract.** The ledger format is defined in exactly one place ([`shared/references/ledger_schema.md`](./shared/references/ledger_schema.md)). Every skill and the agent point at that file rather than duplicating the schema, and every consumer runs the bundled validator script to enforce it. The agent inlines the essential schema fields in its prompt because it can't reliably read the reference doc from its isolated context, but the executable validator is the ground truth that prevents drift.
- **Scripted exports.** The `.bib` + PMID exports are written by [`shared/scripts/ledger_to_exports.py`](./shared/scripts/ledger_to_exports.py), called by each consumer rather than hand-written. Like the validator, an executable export keeps the format from drifting and copies reference fields verbatim from the ledger.

## Versioning

The plugin is the only versioned unit. Per-skill SKILL.md files have no `version` frontmatter field, and per-skill CHANGELOGs do not exist. See the plugin-level [`CHANGELOG.md`](./CHANGELOG.md) for release history.

Current release: **2.1.1**.

**Semver policy:**

- MAJOR — breaking change to the researcher-facing workflow or to the ledger schema contract (which also bumps `ledger_schema_version` in [`ledger_schema.md`](./shared/references/ledger_schema.md)).
- MINOR — a new skill or agent added, a new capability, or a new required tool.
- PATCH — bug fixes, prose edits, reference-template updates.

## Document generation

Both skills write a `.md` source and a `.docx`. The `.docx` is made with the environment's built-in Word-document capability (Claude Desktop / Cowork) in the house style — A4, Arial, navy headings, title page, header/footer. If pandoc is available instead, the same style comes from each skill's `assets/reference.docx`:

```bash
pandoc "[Name]_[DocType]_[Year].md" -o "[Name]_[DocType]_[Year].docx" \
  --reference-doc="[skill-path]/assets/reference.docx" --from=markdown+yaml_metadata_block
```

`[skill-path]` is the skill's absolute base directory: shell commands run from the researcher's workspace, so every script and asset path must be anchored to it.

## Prompt style

Skills and agents are written for current, capable models: state the outcome, the hard constraints and why, and the checks the output must pass — not step-by-step procedure. Hard constraints live in the scripts wherever possible (validation, verification, reference formatting, exports), because executable checks cannot drift.

## Tests

`pytest -q` from the repository root (`pip install -r requirements-dev.txt`). Tests cover the shared scripts with planted fixtures in `tests/fixtures/`, plus the plugin structure: skill names and descriptions must stay within the loader limits (name ≤ 64 chars, lowercase-hyphen, matching the folder; description ≤ 1,024 chars, no XML tags) — a skill that breaks them is dropped silently. CI runs them on every push.

## Tool Dependencies

Required (whole plugin):

- **Python 3 + PyYAML** — used by the verification, validation, formatting and export scripts
- **PubMed MCP** — literature search and article metadata (used by the `evidence-search` agent)
- **Scholar Gateway MCP** — semantic search (used by the agent)
- **WebSearch / WebFetch** — national guideline pages (used by the agent)

Optional:

- **pandoc** — only if the environment cannot create Word documents natively

Optional connectors (enhance search coverage):

- **bioRxiv MCP** — preprints on rapidly evolving topics
- **Clinical Trials MCP** — ongoing trial data

## AI Use Policy (ISO 42001)

**System identity:** the latest Claude Opus model (Anthropic) at maximum effort (the currently recommended version is named in the plugin README) accessed via Claude Cowork or Claude Code in Claude Desktop.

**Intended use:** AI-assisted literature search, evidence synthesis, and cross-referencing of clinical protocols against current guidelines. The plugin retrieves, structures, and summarises evidence; it does not make clinical decisions.

**Human oversight:** Every output is advisory only and is generated as an explicit draft. The reviewing clinician and the approving MDT are responsible for critical appraisal, verification, and sign-off.

**Transparency:** Every generated document carries a "DRAFT — NOT FOR CLINICAL USE" callout and a transparency disclaimer naming the plugin (`clinical-evidence v…`), the model, the MCP sources used, and the generation date.

**Reference integrity:** the `evidence-search` agent copies reference metadata into the hidden ledger straight from PubMed tool output. Before anything is cited, the `reference-checker` agent — given only the identifiers — re-reads every record from PubMed in a fresh context, and `verify_references.py` cross-checks the two readings. The comparison tolerates formatting differences (case, diacritics, markup, epub vs print year) but excludes any reference whose identifier or title points to a different paper, and any retracted paper. The validator then checks structure, and `format_references.py` generates the reference list so reference text is never retyped.
