# Changelog

All notable changes to the `clinical-evidence` plugin are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.1.0] - 2026-04-10

### Added

- **`evidence-search` agent** at [`agents/evidence-search.md`](./agents/evidence-search.md). The PubMed + Scholar Gateway + guideline search workflow now runs inside an isolated subagent context. Tool-heavy traffic (PubMed metadata calls, Scholar Gateway passages, full-text retrievals, reference verification) no longer reaches the parent conversation — consumer skills only see a short structured "ledger ready" result. The agent writes the canonical ledger to `<workspace>/.literature_search_ledger.yaml` exactly as before.
- **`research-summary` consumer skill** at [`skills/research-summary/`](./skills/research-summary/). Produces the narrative evidence summary (`.md` + `.docx`) from the hidden reference ledger, with bundled `assets/reference.docx` pandoc template and `references/evidence_summary_template.md`. Auto-dispatches the `evidence-search` agent if no ledger exists in the workspace.

### Changed

- **`literature-search` is now a thin trigger skill** (~180 lines, down from 527). Its job is to confirm scope with the researcher, dispatch the `evidence-search` agent, validate the returned ledger, and write `.bib` + PMID exports. It no longer produces `.md` or `.docx` evidence summaries — that responsibility moved to `research-summary`. At the end of a successful search it points the researcher at `research-summary` (for narrative synthesis) and `protocol-reviewer` (for protocol cross-referencing).
- **`protocol-reviewer` Step 2 auto-trigger** now dispatches the `evidence-search` agent directly via the Agent tool instead of reading the sibling `literature-search/SKILL.md` and running that workflow inline. This keeps the protocol review's main conversation free of search tool output. A graceful-degradation fallback to the old read-sibling-SKILL path remains for unusual install configurations.
- **Plugin-level docs** ([`README.md`](./README.md), [`CLAUDE.md`](./CLAUDE.md)) updated to describe the three-skill + one-agent architecture, the producer/consumer split, and the per-skill output responsibilities.
- **`assets/reference.docx`** and **`evidence_summary_template.md`** moved from `skills/literature-search/` to `skills/research-summary/` — they are the template for that skill's output.

### Compatibility

- **No breaking changes to the researcher-facing interface.** The direct-entry workflow (*"search the literature on X"*) still produces a verified ledger and reference exports. The *"review this protocol"* workflow still auto-triggers a search. The hidden ledger handoff remains invisible.
- **Ledger schema stays at `1.0`.** No format changes. Pre-existing ledgers from 1.0.0 installs are consumable by all three skills and the agent in 1.1.0 without modification.
- **Shared contract layer stays in `skills/literature-search/`** ([`ledger_schema.md`](./skills/literature-search/references/ledger_schema.md), [`consumer_integration.md`](./skills/literature-search/references/consumer_integration.md), [`validate_ledger.py`](./skills/literature-search/scripts/validate_ledger.py)). Consumer skills continue to reference it via sibling relative paths.

## [1.0.0] - 2026-04-10

### Added

Initial plugin release. Bundles two mature skills — `literature-search` and `protocol-reviewer` — that were previously distributed as the standalone repos [Laszlo75/literature-search](https://github.com/Laszlo75/literature-search) and [Laszlo75/protocol-reviewer](https://github.com/Laszlo75/protocol-reviewer). Both standalone repos are now archived; the clinical-evidence plugin is the canonical distribution from this point on.

**What the plugin contains:**

- **literature-search** — systematic search of PubMed, Scholar Gateway, and national guideline bodies (BTS, NICE, KDIGO, SIGN, BSH, etc.), with character-by-character verification of every reference against PubMed metadata. Produces a markdown + Word evidence summary, a BibTeX file, and a PMID list.
- **protocol-reviewer** — reads an uploaded clinical protocol, cross-references it against current guidelines and published evidence, and produces a structured Word review document with evidence grades and actionable recommendations.
- **Invisible handoff** between the two skills via a hidden reference ledger (`.literature_search_ledger.yaml`) in the workspace. Researchers never have to name, move, or manage this file.
- **Reference ledger schema** defined as a single source of truth at [`skills/literature-search/references/ledger_schema.md`](./skills/literature-search/references/ledger_schema.md).
- **Executable ledger validator** at [`skills/literature-search/scripts/validate_ledger.py`](./skills/literature-search/scripts/validate_ledger.py), run by both skills as a self-check.
- **ISO 42001 transparency disclaimers** baked into every generated document.

### Changed

- **Per-skill version numbers retired.** The plugin is the single versioned unit. SKILL.md frontmatter no longer carries a `version` field, and per-skill `CHANGELOG.md` files have been removed. The release history of each skill, up to the bundling point, remains available in the archived standalone repos.
- **Transparency disclaimer metadata** in both skill templates now reports `clinical-evidence v[plugin version]` as the single AI-system identifier, replacing the earlier two-token form (`literature-search v… + protocol-reviewer v…`).
- **Repository URLs** in all per-skill READMEs, CLAUDE.md files, and template disclaimers now point at this repo (`github.com/Laszlo75/clinical-skills`) instead of the archived standalone repos.

### Compatibility

- **Pre-existing reference ledgers** from standalone `literature-search` installs are still consumable by the plugin-bundled `protocol-reviewer` as long as they carry `ledger_schema_version: 1.x` — the ledger schema version is independent of the plugin version and is unchanged in this release.
- **The ledger schema** remains at `1.0`. If `literature-review` or any other future consumer needs a breaking schema change, the ledger schema version will bump independently of the plugin version.
