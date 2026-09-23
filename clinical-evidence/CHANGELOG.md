# Changelog

All notable changes to the `clinical-evidence` plugin are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/).

## [2.0.1] - 2026-09-23

### Changed

- **Recommended model is now Claude Opus 5.5 at maximum effort.** The specific version is named in one place only (the plugin README); skills, agent, and maintainer docs refer to "the latest Claude Opus" so the next model bump is a one-line change. Added Claude Cowork setup notes (select the model in the app and enable extended thinking).
- **`evidence-search` agent pinned to `model: opus`** (was `inherit`), so the search and reference verification can no longer silently run on a lighter model when the parent session is not Opus.
- **Model identifier in disclaimers, ledger, and register** now records the self-reported model ID plus the configured tier (e.g. `claude-opus-5-5 (configured: opus, effort max)`), giving the audit trail a second anchor because models can misreport their own ID.
- Trimmed over-emphatic prompt wording ("think deeply and extensively", "single most important instruction") that is redundant at maximum effort; the reasons behind each rule are kept.
- Reference guidance relaxed for current models: ~20–40 references (was 15–30) and full text for up to ~15 key papers (was 5–10), still quality over quantity.

### Fixed

- **Evaluation register no longer lives inside the plugin install.** It was written to `reviews/evaluation_register.csv` in the skill directory, which is replaced on every plugin update, wiping the audit trail. It is now `<workspace>/clinical-evidence-register.csv`. If you have an old register, copy it out of the plugin cache before updating.
- **Script and asset paths are anchored to the skill directory.** Commands such as `python ../../shared/scripts/validate_ledger.py` and `--reference-doc=assets/reference.docx` were relative to the skill directory but run from the researcher's workspace. Every command now uses a `[skill-path]` placeholder resolved to the skill's absolute base directory, with quoting for paths containing spaces.
- `evidence-search` no longer falls back to a hard-coded `skill_version: "2.0.0"`; it writes `"unknown"` if the dispatcher did not pass a version.
- Plugin README said "all three skills" share the agent — there are two.
- Per-skill `CLAUDE.md` files carried "when working with code in this repository" boilerplate; they are now labelled as maintainer notes.

### Compatibility

- No workflow or ledger schema change. Ledger schema stays at `1.0`; existing ledgers remain valid.

## [2.0.0] - 2026-05-25

### Removed

- **`literature-search` skill removed.** Its only unique responsibilities — being the user-facing trigger for a bare search and writing the Zotero export files — were folded into `research-summary`. The skill had become a thin wrapper around the `evidence-search` agent: the other two skills already dispatched the agent directly and never routed through it.

### Changed

- **`research-summary` is now the user-facing entry point for a literature search or evidence summary.** It absorbed `literature-search`'s trigger phrases ("literature search", "search PubMed", "find evidence on", "reference list for", "what does the latest evidence say about", etc.) and now produces **four** files — `.md`, `.docx`, `.bib`, and `PMIDs.txt` — up from two. The narrative document and the Zotero exports come from the same validated ledger in a single pass.
- **Shared contract files moved to a plugin-level `shared/` directory.** [`ledger_schema.md`](./shared/references/ledger_schema.md), [`consumer_integration.md`](./shared/references/consumer_integration.md), `pubmed_strategy.md`, and [`validate_ledger.py`](./shared/scripts/validate_ledger.py) moved from `skills/literature-search/` to `shared/`. The contract is now owned by no single skill; both consumers reference it via `../../shared/...`.
- **`protocol-reviewer`'s graceful-degradation fallback removed.** It previously fell back to reading `../literature-search/SKILL.md` when the agent was unavailable; that path no longer exists, so the agent is now the only search route (an unknown-subagent error tells the researcher to reinstall the plugin).

### Added

- **`shared/scripts/ledger_to_exports.py`** — an executable script that writes the `.bib` + PMID exports from the validated ledger. Both consumer skills call it instead of hand-writing BibTeX, so the export format cannot drift and reference fields are copied verbatim from the ledger (the same executable-over-prose principle as the validator).

### Fixed

- `protocol-reviewer/references/document_template.md` pointed at a non-existent `../literature-search/references/evidence_summary_template.md` for the BibTeX format; it now invokes the shared export script.
- `research-summary`'s template contradicted itself (its "produce the exports" step vs. its "those belong to literature-search" output note); reconciled — the skill now owns the exports.
- The two pre-existing BibTeX formats disagreed (PMID-keyed vs. AuthorYear-keyed); the shared export script settles on one canonical PMID-keyed format.
- `marketplace.json` carried redundant version numbers (a cosmetic top-level catalog version, plus a per-plugin entry version that had drifted to `1.0.0` while `plugin.json` read `1.1.0`). Both marketplace `version` fields were removed — `plugin.json` is now the single source of truth, which is the version Claude Code resolves first anyway.

### Compatibility

- **Breaking: the `literature-search` skill no longer exists.** Anyone who invoked it by name should use `research-summary`, which now covers search + summary + Zotero exports. Its trigger phrases activate `research-summary` instead.
- **Ledger schema stays at `1.0`.** No format change — existing ledgers remain consumable by both skills and the agent. The contract files moved location but their content is unchanged.

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
