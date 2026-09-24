# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working on the `clinical-evidence` plugin.

## What This Is

A Claude Code plugin that bundles two co-designed clinical skills — `research-summary` and `protocol-reviewer` — plus three shared subagents: `guideline-search` (Opus, medium effort), which reads the current guideline documents and copies each recommendation and grade as printed; `evidence-search`, which does the PubMed/Scholar Gateway literature retrieval (several run in parallel, on Sonnet); and `second-reviewer`, which challenges practice-changing protocol-review judgements. The skills share a hidden YAML reference ledger produced by the agent. Together they take a clinical topic or an uploaded protocol and produce a draft evidence summary and/or a draft protocol review document, all framed in UK NHS context and carrying ISO 42001 transparency disclaimers. `research-summary` is the user-facing entry point for a literature search or evidence summary (it dispatches the agent and also writes Zotero exports); `protocol-reviewer` reviews an uploaded protocol against the same evidence.

The plugin is the single distributable unit: the two skills and the agent are co-designed, share the hidden reference ledger and a plugin-level `shared/` contract directory, and are not intended to be installed independently.

## Repository Structure

```text
clinical-evidence/
├── .claude-plugin/plugin.json     # plugin manifest
├── README.md                      # plugin-level docs (installation + quick start)
├── CHANGELOG.md                   # plugin-level changelog (single source of version history)
├── CLAUDE.md                      # this file
├── agents/
│   ├── guideline-search.md        # current guidelines: recommendations + grades copied from source
│   ├── evidence-search.md         # PubMed/Scholar literature search, writes a partial ledger
│   └── second-reviewer.md         # challenges practice-changing protocol-review judgements
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
│       ├── merge_ledgers.py         # combines partial ledgers from parallel searches
│       ├── guideline_cache.py       # keeps checked guidelines between runs (plugin data folder)
│       ├── review_tables.py         # protocol review: consistency checks, evidence table, traceability, register
│       ├── run_log.py               # per-stage timing (and agent token) log for benchmarking runs
│       ├── md_to_docx.py            # Markdown → .docx via pandoc (installs pypandoc_binary if needed)
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

- **Shared subagents.** Both skills dispatch the same [`evidence-search` agent](./agents/evidence-search.md) to do the actual search work in isolated context. The agent runs in its own conversation so the tool-heavy traffic (PubMed metadata, Scholar Gateway passages, full-text retrievals) never reaches the parent skill's context. This keeps the main conversation clean and lets downstream synthesis work from a short structured summary rather than thousands of lines of tool output. Searches run in parallel — 2–3 `guideline-search` agents split by guideline body plus one `evidence-search` agent per question cluster — then are merged with `merge_ledgers.py`.
- **Shared contract directory.** `research-summary/SKILL.md` and `protocol-reviewer/SKILL.md` reference [`shared/references/ledger_schema.md`](./shared/references/ledger_schema.md), [`shared/references/consumer_integration.md`](./shared/references/consumer_integration.md), [`shared/scripts/validate_ledger.py`](./shared/scripts/validate_ledger.py), and [`shared/scripts/ledger_to_exports.py`](./shared/scripts/ledger_to_exports.py) via `../../shared/...`. Each skill sits at `skills/<skill>/`, two levels below the plugin root, so those paths resolve. Splitting the plugin would break these pointers.
- **Shared hidden ledger.** When any skill dispatches the `evidence-search` agent, the agent writes an internal reference ledger to `<workspace>/.literature_search_ledger.yaml`. Any skill run later in the same workspace discovers, validates, and consumes that ledger automatically. Researchers never see or manage the ledger.
- **Single reference contract.** The ledger format is defined in exactly one place ([`shared/references/ledger_schema.md`](./shared/references/ledger_schema.md)). Every skill and the agent point at that file rather than duplicating the schema, and every consumer runs the bundled validator script to enforce it. The agent inlines the essential schema fields in its prompt because it can't reliably read the reference doc from its isolated context, but the executable validator is the ground truth that prevents drift.
- **Scripted exports.** The `.bib` + PMID exports are written by [`shared/scripts/ledger_to_exports.py`](./shared/scripts/ledger_to_exports.py), called by each consumer rather than hand-written. Like the validator, an executable export keeps the format from drifting and copies reference fields verbatim from the ledger.

## Versioning

The plugin is the only versioned unit. Per-skill SKILL.md files have no `version` frontmatter field, and per-skill CHANGELOGs do not exist. See the plugin-level [`CHANGELOG.md`](./CHANGELOG.md) for release history.

Current release: **2.5.1**.

**Semver policy:**

- MAJOR — breaking change to the researcher-facing workflow or to the ledger schema contract (which also bumps `ledger_schema_version` in [`ledger_schema.md`](./shared/references/ledger_schema.md)).
- MINOR — a new skill or agent added, a new capability, or a new required tool.
- PATCH — bug fixes, prose edits, reference-template updates.

## Document generation

Both skills write a `.md` source and a `.docx`. The `.docx` is made with the environment's built-in Word-document capability (Claude Desktop / Cowork) in the house style — A4, Arial, navy headings, title page, header/footer. If pandoc is available instead, the same style comes from each skill's `assets/reference.docx`:

```bash
pandoc "[Name]_[DocType]_[Year].md" -o "[Name]_[DocType]_[Year].docx" \
  --reference-doc="${CLAUDE_SKILL_DIR}/assets/reference.docx" --from=markdown+yaml_metadata_block
```

Paths use Claude Code's built-in variables, which are filled in inside SKILL.md: `${CLAUDE_PLUGIN_ROOT}` (the installed plugin folder) and `${CLAUDE_SKILL_DIR}` (the skill's folder). Shell commands run from the researcher's workspace, so every script and asset path is anchored to them. Files read with the Read tool, such as `shared/references/*.md`, are not filled in, so the skill's Paths section gives the absolute values.

## Prompt style

Skills and agents are written for current, capable models: state the outcome, the hard constraints and why, and the checks the output must pass — not step-by-step procedure. Hard constraints live in the scripts wherever possible (validation, verification, reference formatting, exports), because executable checks cannot drift.

## Tests

`pytest -q` from the repository root (`pip install -r requirements-dev.txt`). Tests cover the shared scripts with planted fixtures in `tests/fixtures/`, plus the plugin structure: skill names and descriptions must stay within the loader limits (name ≤ 64 chars, lowercase-hyphen, matching the folder; description ≤ 1,024 chars, no XML tags) — a skill that breaks them is dropped silently. CI runs them on every push.

## Tool Dependencies

Required (whole plugin):

- **Python 3 + PyYAML** — used by the verification, validation, formatting and export scripts
- **PubMed MCP** — literature search and article metadata (used by the `evidence-search` agent)
- **Scholar Gateway MCP** — semantic search (used by the agent)
- **WebSearch / WebFetch** — guideline documents (used by the `guideline-search` agent)

Optional:

- **pandoc** — only if the environment cannot create Word documents natively

Optional connectors (enhance search coverage):

- **bioRxiv MCP** — preprints on rapidly evolving topics
- **Clinical Trials MCP** — ongoing trial data

## AI Use Policy (ISO 42001)

**System identity:** the latest Claude Opus model (Anthropic) at high effort, with Opus at medium effort for the guideline agent and Claude Sonnet for the literature agents (the currently recommended version is named in the plugin README) accessed via Claude Cowork or Claude Code in Claude Desktop.

**Intended use:** AI-assisted literature search, evidence synthesis, and cross-referencing of clinical protocols against current guidelines. The plugin retrieves, structures, and summarises evidence; it does not make clinical decisions.

**Human oversight:** Every output is advisory only and is generated as an explicit draft. The reviewing clinician and the approving MDT are responsible for critical appraisal, verification, and sign-off.

**Transparency:** Every generated document carries a "DRAFT — NOT FOR CLINICAL USE" callout and a transparency disclaimer naming the plugin (`clinical-evidence v…`), the model, the MCP sources used, and the generation date.

**Reference integrity:** the `evidence-search` agent copies reference metadata into the hidden ledger straight from PubMed tool output. Before anything is cited, the skill checks every PMID/DOI pair independently with PubMed's ID converter, and `verify_references.py` excludes any reference whose identifiers point to different papers, or that is retracted. The validator then checks structure, and `format_references.py` generates the reference list so reference text is never retyped.

**Guideline grades:** the `guideline-search` agent copies each grade exactly as the guideline prints it, with a verbatim quote. A grade counts as confirmed only if it appears in that quote (`refmatch.grade_in_source`); the validator flags unconfirmed grades, consumers don't quote them, and `review_tables.py` refuses a protocol-review grade that isn't a confirmed grade of a cited guideline.
