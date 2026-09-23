# CLAUDE.md

Maintainer notes for this skill. The runtime instructions live in `SKILL.md`; this file
records design decisions for anyone editing the skill.

## What it is

Reviews an uploaded clinical protocol (PDF/Word) against current guidelines and recent
evidence and produces a draft, section-by-section review (`.md` + `.docx`) with graded
recommendations, plus Zotero exports and a row in the workspace evaluation register.

## Files

- `SKILL.md` — outcome, workflow, non-negotiables. Kept deliberately short: current
  models need goals, constraints and reasons, not step-by-step procedure.
- `references/document_template.md` — document structure, draft callout and disclaimer
  text.
- `assets/reference.docx` — house style (A4, Arial, navy headings, header/footer); used
  directly if pandoc is the conversion route, otherwise a style reference.
- `evals/evals.json` — test scenarios.

## Design decisions

- **Shared evidence procedure.** Discovery, independent verification, validation,
  reference formatting and exports are defined once in
  `../../shared/references/consumer_integration.md`; this skill follows it.
- **Question-driven, traceable review (2.2.0).** The protocol is mapped to atomic
  statements and PICO-style review questions (`protocol_map.yaml`), confirmed with the
  clinician at a single checkpoint before searching. Searches can run in parallel per
  question cluster (`merge_ledgers.py`). Each statement gets a structured judgement
  (`judgements.yaml`), so every recommendation traces statement → question → evidence →
  verdict.
- **Second reviewer.** The `second-reviewer` agent, in a fresh context, challenges each
  judgement against its cited evidence and checks doses against BNF/SmPC — the dual-review
  step of a systematic review. Disagreements must be resolved in writing.
- **Scripted tables.** `review_tables.py` refuses to build if the working files are
  inconsistent (uncovered statement, excluded/unknown citation, unresolved disagreement),
  then writes the evidence table, traceability matrix and register row — counts are
  computed, not typed.
- **Verification before citation.** `reference-checker` re-reads every PMID from PubMed
  given identifiers only; `verify_references.py` cross-checks tolerantly and moves
  failures to `excluded_references`. `format_references.py` builds the list, so
  reference text is never retyped.
- **Native .docx.** Claude Desktop / Cowork create Word files directly; pandoc is an
  optional route, not a dependency.
- **Evaluation register** at `<workspace>/clinical-evidence-register.csv` — never in the
  skill directory (the plugin cache is replaced on update), appended by
  `review_tables.py`. New columns are added at the end and older registers are migrated
  in place (2.1.0 `references_excluded`, 2.2.0 `second_review_disagreements`).

## AI use policy (ISO 42001)

- **System:** the latest Claude Opus at maximum effort (version named in the plugin
  README), via Claude Cowork or Claude Code.
- **Intended use:** evidence synthesis to support protocol review; it does not make
  clinical decisions.
- **Oversight:** every output is a draft for appraisal by a consultant-level clinician
  and the approving MDT.
- **Transparency:** DRAFT callout; disclaimer with plugin version, model, sources,
  search/review dates and verification status; "Reviewed and approved by" field.
- **Traceability:** the evaluation register records each review's counts and outcome.
