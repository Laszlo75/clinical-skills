# Changelog

All notable changes to the `clinical-evidence` plugin are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/).

## [2.5.1] - 2026-09-24

### Added

- **Per-agent timing.** `run_log.py agent <name> --stage <stage> --seconds S --tokens N` records each dispatched agent's own duration and tokens. The summary lists them under their stage, slowest first, so it shows which parallel agent set the pace. The 2.5.0 search took 12:39 against a 6–8 minute estimate, and the stage total couldn't show why.
- **Compact second-review packet.** `shared/scripts/review_packet.py` gives the second reviewer only the judgements to review, their protocol statements and the evidence they cite, instead of the whole ledger. In 2.5.0 two parallel reviewers each read the full ledger: second-review tokens rose 54% and the time barely moved.

### Changed (readability)

- **No judgement ids in the document.** J1, J2 … stay in the working files and the traceability spreadsheet. The document uses plain topic headings and section numbers; the summary table's first column is the section number, and the appendix matrix starts with the protocol section.

### Changed (accuracy)

- **Guideline agents run at high effort** (Opus), up from medium. Guidelines are the backbone of every review.
- **The second review also covers aligned judgements with low confidence.** An unchallenged "retain" on thin evidence is where the 2.4.0 errors hid (the pre-transplant infection interval, the blood-product exclusions). `review_tables.py` warns when one goes unreviewed.

- **The second reviewer sees what was left out.** The review packet also includes `other_evidence`, every uncited ledger entry on the same review questions, so the reviewer can catch evidence that was overlooked or that contradicts a judgement. It also gets the ledger path for wider checks, and is told accuracy outweighs speed.
- **"Aligned — clarify wording".** Right-but-loosely-worded practice stays aligned instead of counting as a minor update. The 2.5.0 run had 1 aligned against 20 minor updates, which mixed real changes with wording tidy-ups.
- **Older UK guidance against newer guidance.** When a UK guideline predates different, newer guidance, both are shown with dates, e.g. NICE CG165 (2013) lamivudine against newer entecavir/tenofovir advice. The second reviewer checks for this.

### Fixed

- **Second-review output format.** The example gave a YAML list followed by a top-level `missing:` key, which is not valid YAML, and the reviewer copied it. The format is now a mapping (`reviews:` plus `missing:`), and the reviewer checks that its file parses. A new test parses every YAML example in the prompts and reference docs.
- **Working files in the researcher's folder.** In Cowork the lead used the sandbox home (`/home/claude/.clinical-evidence`) as the workspace. The run log, register and reusable search were written where the researcher can't see them and lost after the session. `<workspace>` is now defined as the researcher's selected folder, never the shell's home directory.

## [2.5.0] - 2026-09-24

### Added

- **Guideline cache.** Checked guidelines are kept in the plugin's persistent data folder (`${CLAUDE_PLUGIN_DATA}/guideline_cache`), which survives plugin updates, and reused across runs. `shared/scripts/guideline_cache.py` provides `get`, `put`, `list` and `clear`.
  - The skill loads the cache before the search and stores the checked guidelines after verification.
  - The guideline agents:
    - reuse an entry checked within 30 days without fetching the document;
    - re-check only currency for entries 31–90 days old;
    - read the document again only when the current questions need a recommendation the entry lacks.
  - Recommendations accumulate across topics. Reusing an entry never refreshes its `cached_on` date (the date its document was last read), so age reflects the last real reading.
  - The disclaimer states how many guidelines were read in the run and how many were reused, with the oldest check date.
  - Asking for a fresh guideline check bypasses the cache.
- Ledger schema 1.3 gains optional `cached_on` on guidelines (backward compatible).

## [2.4.2] - 2026-09-24

Ideas adopted from Anthropic's `plugin-dev` plugin.

### Changed

- **Built-in path variables.** Skills now use `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_SKILL_DIR}`, which Claude Code fills in with the real install paths. Previously the model had to work out the absolute path behind a `[skill-path]/../../` placeholder at every command. A fallback remains for environments that don't fill them in.

### Added

- **Reference-integrity tests.** Every script, template or asset a prompt points to (through the path variables or a Markdown link) must exist. Agent frontmatter must use a valid model and colour and include an `<example>` block. A broken path now fails CI instead of a clinical run.

## [2.4.1] - 2026-09-24

The 2.4.0 test run gave the strongest review so far, but the search took 15 min, against 6 in 2.3.0: the single guideline agent was the bottleneck while the literature agents waited.

### Changed

- **Guideline work split across 2–3 parallel `guideline-search` agents**, by guideline body:
  - UK bodies of the core specialty;
  - UK cross-specialty bodies (NICE, BSH, Green Book, MHRA …);
  - international bodies.

  Each agent names important guidelines from outside its own bodies rather than reading them. Every document is still read once, on Opus, so token use should be similar.
- **Second review split** between two parallel reviewers when more than about eight items are sent.
- **Citation style:** one bracket per citation point, numbers ascending, runs collapsed (`[2, 22–25]`).
- **Self-contained protocol positions.** Every subsection, aligned items included, states what the protocol says in terms a reader understands without the heading. "Retain" now means no change; anything else is at least a minor update.
- **Reasoned recommendations.** Every recommendation gives its reason, "Retain" included. Indirect evidence is labelled as indirect, and a value no source addresses is stated as expert opinion (a 2.4.0 item read "Retain [6]", citing post-desensitisation infection data for a pre-transplant infection interval).
- **Wording matches the evidence.** "Must" and "unsafe" need a guideline or clear safety evidence. When current practice is wrong only in some cases, the review names those cases. (A 2.4.0 review called donor-group plasma unsafe on the strength of one study; BSH supports it except for bidirectional mismatch.)
- **Grades stay with the recommendation that carries them.** A grade is never attached to a statement of what a guideline does not cover.

## [2.4.0] - 2026-09-24

### Added

- **`guideline-search` agent (Opus, medium effort).** Guidelines are the backbone of every review, so a dedicated agent now covers them, in parallel with the literature agents:
  - finds the UK and international guidelines for all the questions, including adjacent bodies (e.g. BSH, UKHSA Green Book and MHRA for a transplant protocol);
  - confirms each is the current edition (`currency`: current, past review date, superseded …);
  - reads the guideline documents themselves;
  - extracts the specific recommendations (doses, thresholds, timings);
  - copies each grade exactly as printed, with a verbatim quote. Ungraded guidance is recorded as `ungraded`, never given a borrowed grade.
- **Grade provenance check.** A grade counts only if it appears in the guideline's quoted text (`refmatch.grade_in_source`). Recommendations with no guideline behind them (trends, observational data, expert opinion) stay allowed: they are written ungraded, with their evidence and certainty stated.
  - `validate_ledger.py` warns about unconfirmed grades and about guidelines that are not current.
  - Consumers don't quote unconfirmed grades.
  - `review_tables.py` refuses (for schema 1.3 ledgers) a judgement whose grade isn't a confirmed grade of a guideline it cites.
  - The evidence table gains a `currency` column and marks unconfirmed grades.
- **Ledger schema 1.3** (backward compatible): optional `edition`, `currency`, `pmid`, `doi` on guidelines, and `grade.quote`.

### Changed

- `evidence-search` (Sonnet) now covers only the primary literature and no longer fetches guideline pages.
- The second reviewer checks grades and currency at source for safety-flagged items.
- **One reconciled recommendation per item.** The review document no longer shows "Second reviewer" paragraphs. The lead reconciles each challenge as `revised`, `kept` (with reasons) or `mdt_decision`. The second reviewer's comments and the resolution stay in the traceability CSV/xlsx and appendix, for audit.
- **Uncertainty goes to the MDT.** When both views are defensible, the document presents a "For MDT decision" block: two or more options, each with cited pros and cons, and the choice left to the MDT. `review_tables.py` requires an `outcome` for every disagreement, and at least two options (with valid evidence) for an MDT decision. It adds `outcome` and `mdt_options` to the traceability table, and a `for_mdt_decision` count to the register (older registers are migrated).
- **Specificity kept.** The second reviewer must propose an evidence-based alternative rather than defer to "unit protocol" when a guideline gives a specific value; the lead may not resolve a disagreement that way either.
- **Cleaner prose.** Grades are written naturally ("(BTS Grade 1C)"), with no field names; summary-table cells are short and never truncated.

## [2.3.0] - 2026-09-23

A leaner pipeline to cut both run time and token use. A 2.2.0 protocol review took about 30 minutes; with more capable models it should get faster, not slower. The main causes were one long sequential search, blanket full-text reading, a second agent re-reading every record, and maximum effort on every step.

### Changed

- **Parallel search on Sonnet.**
  - The lead skill splits the questions into 2–4 clusters and dispatches one `evidence-search` agent per cluster at the same time. `merge_ledgers.py` then combines their results.
  - Retrieval and tagging run on Claude Sonnet; judgement and writing stay on Opus.
  - Shorter agent runs also cost fewer tokens, because each tool call re-sends the conversation so far.
- **Economical search.** Each agent stays within its assigned questions. It decides from abstracts first and fetches full text only when a dose, threshold or method can't be judged otherwise (at most two or three papers). It aims for about 6–12 references per cluster.
- **Reference check without an extra agent.** The lead makes one batched PubMed `convert_article_ids` call. `verify_references.py` then checks each PMID ↔ DOI pairing, which catches a real identifier attached to the wrong paper at a fraction of the cost. The `reference-checker` agent has been removed. The fuller title/author comparison is still available for audits.
- **Targeted second review.** `second-reviewer` now checks only practice-changing judgements (major updates, new additions, removals) and safety-flagged items; it is skipped when there are none. `review_tables.py` warns only when such an item goes unreviewed.
- **Skills run at `effort: high`**, not `max`.
- **Word output without token cost.** The new `shared/scripts/md_to_docx.py` converts the Markdown with pandoc, installing `pypandoc_binary` if needed. The environment's built-in Word capability is now only the fallback.

### Compatibility

- Outputs, ledger schema (1.2), timing log and register are unchanged. Compare runs with `run_log.py summary` against the 2.2.1 baseline.

## [2.2.1] - 2026-09-23

### Added

- **Timing log.** Both skills now record each stage's start and end with `shared/scripts/run_log.py`, in `<workspace>/.clinical-evidence/run_log.csv`.
  - Stages logged: map, checkpoint, search, verify, judge, second review, tables, document.
  - Each agent stage also records the token usage the agent reports on completion, where available.
  - The hand-over message ends with a summary of minutes and tokens per stage.
  - The purpose is to find where time and tokens go, and to benchmark plugin versions against each other. The CSV reads straight into R.
  - The script never fails a clinical run: on any error it only warns.

## [2.2.0] - 2026-09-23

### Added

- **Question-driven protocol review.** `protocol-reviewer` now:
  1. maps the protocol into actionable statements (drug, dose, threshold, timing, procedure, monitoring);
  2. derives PICO-style review questions from them;
  3. confirms scope and questions with the clinician at a single checkpoint before searching.
  Each statement then gets a structured judgement: verdict, recommendation, cited evidence, grade, confidence, and safety/commissioning flags.
- **`second-reviewer` agent.** An independent reviewer that works in a fresh context. It challenges every judgement against the evidence it cites, and checks doses against the BNF/SmPC. Each disagreement must be resolved in writing and is shown in the review.
- **Evidence table and traceability matrix.** `shared/scripts/review_tables.py` checks the working files for consistency, then writes:
  - `*_Evidence_Table.csv` + `.xlsx`: one row per cited source, with design, population, size, certainty, key finding and the judgements that cite it;
  - `*_Traceability.csv`: statement → question → evidence → verdict → second review;
  - a Markdown matrix for the review's new Appendix A;
  - the evaluation register row, with counts computed rather than typed.
- **Parallel searches.** `shared/scripts/merge_ledgers.py` combines partial ledgers from several `evidence-search` agents. It de-duplicates on PMID/DOI, unions each entry's questions and renumbers ref_ids.
- **Ledger schema 1.2**, additive and optional:
  - `metadata.questions`;
  - on references: `questions`, `study_design`, `population`, `sample_size` and `certainty`;
  - on guideline recommendations: `source_quote`, `section` and `accessed`. The verbatim source quote lets a reviewer check a dose where it was published.
- Register column `second_review_disagreements`. Existing registers are migrated in place, with new columns appended.

### Fixed

- `verify_references.py --apply` no longer lowers a newer 1.x `ledger_schema_version` to "1.1".

### Compatibility

- 1.0 and 1.1 ledgers remain valid. `research-summary` is unchanged in behaviour; it moves onto the same question-driven pipeline in a later release.
- `openpyxl` is optional. Without it, the CSVs are still written.

## [2.1.1] - 2026-09-23

### Fixed

- **`research-summary` did not load in Claude Cowork.** Its frontmatter `description` was 1,353 characters, over the 1,024-character limit for skill descriptions. The loader dropped the skill silently, so only `protocol-reviewer` appeared (the plugin page showed "1 skill"). The description is now 764 characters and keeps the main trigger phrases. The bug dates from 2.0.0, when the skill absorbed `literature-search`'s triggers.

### Added

- `tests/test_plugin_structure.py` checks each skill's name (format, length, matches its folder) and description (≤ 1,024 characters, no XML tags), each agent's frontmatter, and that the marketplace entry points at the plugin, so a silently dropped skill fails CI instead.

## [2.1.0] - 2026-09-23

### Added

- **Independent, tolerant reference verification.** A new `reference-checker` agent is given only the PMIDs/DOIs from a search and re-reads each record from PubMed in a fresh context. `shared/scripts/verify_references.py` then cross-checks the two readings with `shared/scripts/refmatch.py`:
  - Harmless differences pass: capitalisation, accents (Müller/Muller/Mueller), HTML markup, punctuation, a DOI written as a URL, epub vs print year.
  - A different PMID or DOI, a title belonging to another paper, or a retraction fails, and the reference moves to `excluded_references` so it can never be cited.
  - Consortium-author mismatches are flagged for a quick human glance.
  - This replaces the search agent's own character-by-character self-check.
- **`shared/scripts/format_references.py`** builds the numbered Vancouver reference list (Markdown, or JSON for code that writes the `.docx`) from the verified ledger, refusing unknown or excluded ids. Reference text is no longer retyped.
- **Test suite and CI.** `tests/` (pytest, planted fixtures) covers matching, verification, formatting, validation and exports. A GitHub Actions workflow runs it on Python 3.10 and 3.12.
- Evaluation register gains a `references_excluded` column, appended at the end so existing registers stay readable.

### Changed

- **Prompts rewritten for current models.** SKILL.md files and the search agent now state the outcome, the hard constraints with their reasons, and the checks the output must pass, rather than step-by-step procedure. Line counts: protocol-reviewer 402 → 137, research-summary 383 → 105, evidence-search 556 → 154. The shared evidence procedure lives once, in `shared/references/consumer_integration.md`.
- **pandoc is optional.** Claude Desktop / Cowork create `.docx` natively in the house style; pandoc with `assets/reference.docx` remains an alternative route.
- Templates are now structure specs (sections, callout, disclaimer). The disclaimer records the verification status.
- Evidence summaries are labelled "Structured Literature Review" rather than "Systematic Literature Search", since there is no PRISMA-level search log yet.

### Fixed

- **The ledger schema's worked example cited the wrong paper.** It gave PMID 31107464 and doi:10.1111/ajt.15493 for Kotton et al. 2018 (Third International CMV Consensus Guidelines). PubMed shows that PMID is an organoid methods paper, and the DOI belongs to another article. Corrected to PMID 29596116, doi:10.1097/TP.0000000000002191. This is the failure mode the new verification catches, and it does: the old example is excluded when run through the pipeline.
- Duplicate-DOI detection is case-insensitive. `ref_id` uniqueness now also covers preprints.

### Compatibility

- **Ledger schema 1.1**, additive: optional `integrity` per reference, `excluded_references`, `metadata.verification`. 1.0 ledgers still validate; consumers verify them on first use.

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
